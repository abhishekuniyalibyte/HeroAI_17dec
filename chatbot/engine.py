# engine.py  (FULL AI ENGINE — RAG + LLM — trimmed to ChatbotResult requirements)
 
import os
import json
import numpy as np
import re
from dataclasses import dataclass
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer, util
import pickle
 
load_dotenv()
 
# ============================================================
# CONFIG
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
 
EMBEDDINGS_PATH = Path("media/embeddings/restaurant_1_menu_embeddings.pkl")
CHUNKS_PATH = Path("text_chunks.json")
 
# ============================================================
# GLOBAL RAG STATE
# ============================================================
_embed_model = None
_embeddings = None
_text_chunks = None
_groq_client = None
_emb_last_mtime = None
_chunks_last_mtime = None
 
# Common typo corrections
COMMON_TYPO_MAP = {
    "desert": "dessert",
    "deserts": "desserts",
}
 
# ============================================================
# ChatbotResult (FINAL REQUIRED FORMAT)
# ============================================================
@dataclass
class ChatbotResult:
    intent: str
    reply: str
    item_id: Optional[int] = None
    quantity: int = 1
    item_name: Optional[str] = None
 
 
# ============================================================
# RAG SYSTEM LOADER
# ============================================================
def load_rag_system():
    global _embed_model, _embeddings, _text_chunks, _groq_client
    global _emb_last_mtime, _chunks_last_mtime

    # Agar sab pehle se loaded hai to dobara mat load karo
    if _embed_model and _embeddings is not None and _text_chunks is not None:
        return

    print("[RAG] Loading embedding model...")

    # 1) SentenceTransformer model
    if _embed_model is None:
        _embed_model = SentenceTransformer(MODEL_NAME)

    # 2) Embeddings file load karo
    if not EMBEDDINGS_PATH.exists():
        raise FileNotFoundError(f"Embeddings not found: {EMBEDDINGS_PATH}")

    # Raw data read (pkl ya npy / npz)
    if EMBEDDINGS_PATH.suffix == ".pkl":
        with open(EMBEDDINGS_PATH, "rb") as f:
            data = pickle.load(f)
    else:
        data = np.load(EMBEDDINGS_PATH, allow_pickle=True)

    # Agar dict hai, to usme se embeddings (aur texts) nikalo
    if isinstance(data, dict):
        if "embeddings" not in data:
            raise ValueError(
                f"Embeddings dict me 'embeddings' key nahi mili. "
                f"Available keys: {list(data.keys())}"
            )

        emb_array = data["embeddings"]

        # Agar texts/chunks bhi isi file me stored hain:
        if _text_chunks is None:
            if "texts" in data:
                _text_chunks = data["texts"]
            elif "chunks" in data:
                _text_chunks = data["chunks"]
    else:
        # Direct array case
        emb_array = data

    # Final numpy array
    _embeddings = np.asarray(emb_array, dtype="float32")
    _emb_last_mtime = EMBEDDINGS_PATH.stat().st_mtime
    print(f"[RAG] Embeddings loaded. Shape = {_embeddings.shape}")

    # 3) Agar abhi tak _text_chunks nahi aaye to JSON se loado
    if _text_chunks is None:
        if not CHUNKS_PATH.exists():
            raise FileNotFoundError(f"Text chunks not found: {CHUNKS_PATH}")
        with open(CHUNKS_PATH, "r") as f:
            _text_chunks = json.load(f)
        _chunks_last_mtime = CHUNKS_PATH.stat().st_mtime
    else:
        # Agar chunks embeddings ke saath hi aaye the to file optional ho sakti hai
        if CHUNKS_PATH.exists():
            _chunks_last_mtime = CHUNKS_PATH.stat().st_mtime
        else:
            _chunks_last_mtime = None

    # 4) Groq client
    if _groq_client is None and GROQ_API_KEY:
        _groq_client = Groq(api_key=GROQ_API_KEY)
        print("[RAG] Groq client initialized")

 
def ensure_latest_embeddings():
    global _embeddings, _text_chunks, _emb_last_mtime, _chunks_last_mtime

    if not EMBEDDINGS_PATH.exists() or not CHUNKS_PATH.exists():
        return

    current_emb = EMBEDDINGS_PATH.stat().st_mtime
    current_chunks = CHUNKS_PATH.stat().st_mtime

    if _emb_last_mtime is None or _chunks_last_mtime is None:
        _emb_last_mtime = current_emb
        _chunks_last_mtime = current_chunks
        return

    # ---------- Embeddings reload ----------
    if current_emb != _emb_last_mtime:
        print("[RAG] Reloading NEW embeddings...")

        if EMBEDDINGS_PATH.suffix == ".pkl":
            with open(EMBEDDINGS_PATH, "rb") as f:
                data = pickle.load(f)
        else:
            data = np.load(EMBEDDINGS_PATH, allow_pickle=True)

        if isinstance(data, dict):
            if "embeddings" not in data:
                raise ValueError(
                    f"Embeddings dict me 'embeddings' key nahi mili. "
                    f"Available keys: {list(data.keys())}"
                )
            emb_array = data["embeddings"]

            # Optional: texts bhi saath update karna ho to
            if "texts" in data:
                _text_chunks = data["texts"]
            elif "chunks" in data:
                _text_chunks = data["chunks"]
        else:
            emb_array = data

        _embeddings = np.asarray(emb_array, dtype="float32")
        _emb_last_mtime = current_emb

    # ---------- Chunks reload ----------
    if current_chunks != _chunks_last_mtime:
        print("[RAG] Reloading NEW text chunks...")
        with open(CHUNKS_PATH, "r") as f:
            _text_chunks = json.load(f)
        _chunks_last_mtime = current_chunks

 
# ============================================================
# SEMANTIC SEARCH
# ============================================================
def parse_chunk_text(chunk: str) -> Dict[str, str]:
    parts = {}
    for seg in chunk.split(". "):
        if ": " in seg:
            k, v = seg.split(": ", 1)
            parts[k.lower()] = v
 
    return {
        "category": parts.get("category", ""),
        "name": parts.get("item", ""),
        "price": parts.get("price", ""),
    }
 
 
def semantic_search(query: str, top_k: int = 5) -> List[Dict[str, any]]:
    ensure_latest_embeddings()
 
    q_emb = _embed_model.encode(query, convert_to_numpy=True)
    scores = util.cos_sim(q_emb, _embeddings)[0]
    top_indices = scores.argsort(descending=True)[:top_k].tolist()
 
    results = []
    for idx in top_indices:
        parsed = parse_chunk_text(_text_chunks[idx])
        results.append(
            {
                "text": _text_chunks[idx],
                "score": float(scores[idx]),
                "parsed": parsed
            }
        )
    return results
 
 
# ============================================================
# NORMALIZATION
# ============================================================
def normalize_term(term: str) -> str:
    if not term:
        return term
 
    t = term.strip().lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
 
    if "desert" in t and "dessert" not in t:
        t = "dessert"
 
    t = COMMON_TYPO_MAP.get(t, t)
    return t
 
 
# ============================================================
# LLM INTENT CLASSIFICATION
# ============================================================
def classify_intent_with_llm(message: str) -> Dict[str, any]:
    """
    This is a trimmed version of chatbot.py classification,
    but returns only fields we can use.
    """
    if not _groq_client:
        load_rag_system()
 
    prompt = f"""
You are a restaurant ordering assistant. Extract intent from the user's message.
 
INTENTS:
ADD_ITEM, REMOVE_ITEM, SHOW_CART, SHOW_MENU,
CLEAR_CART, CONFIRM_ORDER, SEARCH_ITEM, HELP
 
Extract:
- intent
- item_name (lowercase or null)
- quantity (default 1)
 
Return ONLY JSON:
"""
 
    try:
        resp = _groq_client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[{"role": "user", "content": prompt + message}],
            temperature=0.2,
            max_tokens=200
        )
        raw = resp.choices[0].message.content.strip()
 
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "").strip()
 
        data = json.loads(raw)
 
        if "intent" not in data:
            data["intent"] = "HELP"
        if "quantity" not in data:
            data["quantity"] = 1
 
        return data
 
    except Exception:
        return {"intent": "HELP", "quantity": 1, "item_name": None}
 
 
# ============================================================
# CONVERSATIONAL RESPONSE
# ============================================================
def generate_conversational_reply(user_query: str, items: List[Dict[str, any]]) -> str:
    if not _groq_client:
        return "Here are some items I found."
 
    context = "\n".join([f"- {it['text']}" for it in items])
 
    prompt = f"""
You are a friendly restaurant assistant.
 
User question: {user_query}
 
Relevant menu items:
{context}
 
Give a helpful natural-language answer (2–4 sentences). Mention prices.
"""
 
    try:
        resp = _groq_client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=250
        )
        return resp.choices[0].message.content.strip()
 
    except Exception:
        names = [it["parsed"]["name"] for it in items]
        return f"I found these items: {', '.join(names)}."
 
 
# ============================================================
# MAIN ENTRYPOINT: parse_message()
# ============================================================
def parse_message(message: str) -> ChatbotResult:
    text = (message or "").strip()
    if not text:
        return ChatbotResult(
            intent="HELP",
            reply="Try something like 'menu', 'add butter naan', or 'show cart'."
        )
 
    load_rag_system()
 
    llm = classify_intent_with_llm(text)
 
    intent = llm.get("intent", "HELP")
    item_name_raw = llm.get("item_name")
    quantity = llm.get("quantity", 1)
 
    # -------------------------------
    # SIMPLE INTENTS
    # -------------------------------
    if intent == "SHOW_CART":
        return ChatbotResult(intent="SHOW_CART", reply="Here is your cart:")
 
    if intent == "SHOW_MENU":
        return ChatbotResult(intent="SHOW_MENU", reply="Here are the menu items:")
 
    if intent == "CLEAR_CART":
        return ChatbotResult(intent="CLEAR_CART", reply="Okay, clearing your cart.")
 
    if intent == "CONFIRM_ORDER":
        return ChatbotResult(intent="CONFIRM_ORDER", reply="Confirming your order...")
 
    # -------------------------------
    # ADD / REMOVE
    # -------------------------------
    if intent in ["ADD_ITEM", "REMOVE_ITEM"]:
        return ChatbotResult(
            intent=intent,
            reply="Processing...",
            quantity=quantity,
            item_name=item_name_raw
        )
 
    # -------------------------------
    # SEARCH (RAG)
    # -------------------------------
    if intent == "SEARCH_ITEM" and item_name_raw:
        normalized = normalize_term(item_name_raw)
        results = semantic_search(normalized, top_k=5)
 
        if not results:
            return ChatbotResult(
                intent="SEARCH_ITEM",
                reply=f"Sorry, I couldn't find anything related to '{normalized}'."
            )
 
        best_score = results[0]["score"]
        if best_score < 0.35:
            return ChatbotResult(
                intent="SEARCH_ITEM",
                reply=f"Sorry, '{normalized}' is not on our menu."
            )
 
        conversational = generate_conversational_reply(text, results)
        return ChatbotResult(
            intent="SEARCH_ITEM",
            reply=conversational
        )
 
    # -------------------------------
    # HELP or fallback
    # -------------------------------
    return ChatbotResult(
        intent="HELP",
        reply="I can help you browse the menu or place an order. Try 'menu' or 'add butter naan'."
    )
    
    