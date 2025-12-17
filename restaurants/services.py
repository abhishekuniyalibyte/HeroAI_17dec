# restaurants/services.py
import json
import os
import tempfile
from typing import Tuple, Dict, Any

from django.core.files import File
from django.utils import timezone

from restaurants import menu_extractor
from restaurants.menu_utils import extract_menu_from_path

from menu.services import rebuild_menu_from_json
from menu.embedding_context import suspend_embedding_signals
from menu.tasks import regenerate_menu_embeddings_for_restaurant


def _flatten_categories_to_items(categories: list[dict]) -> list[dict]:
    items_from_json = []

    for cat in categories or []:
        cat_name = (
            cat.get("name")
            or cat.get("category")
            or cat.get("category_name")
            or ""
        )
        cat_name = (cat_name or "").strip()

        for item in cat.get("items") or []:
            items_from_json.append(
                {
                    "name": (item.get("name") or "").strip(),
                    "description": item.get("description") or "",
                    # IMPORTANT: menu.services will create Category rows from this string
                    "category": cat_name,
                    "price": item.get("price"),
                    "currency": item.get("currency") or "INR",
                    "ingredients": item.get("ingredients") or [],
                    "image_url": item.get("image_url") or "",
                    # you can pass raw too (optional)
                    "raw": item,
                }
            )

    # remove invalid (no name)
    items_from_json = [x for x in items_from_json if x.get("name")]
    return items_from_json


def run_menu_extraction_pipeline(restaurant) -> Tuple[bool, Dict[str, Any]]:
    """
    Returns: (success: bool, info: dict)
    """

    sources = restaurant.get_menu_sources_for_ai()
    image_paths = sources.get("images") or []
    pdf_paths = sources.get("pdfs") or []

    assets = [("image", p) for p in image_paths] + [("pdf", p) for p in pdf_paths]
    assets = [(k, p) for (k, p) in assets if p and os.path.exists(p)]

    if not assets:
        return False, {"error": "No menu images or PDFs found for this restaurant."}

    # set processing state
    restaurant.menu_extract_status = "processing"
    restaurant.menu_extract_error = ""
    restaurant.save(update_fields=["menu_extract_status", "menu_extract_error"])

    all_categories = []
    restaurant_name = None
    phone = None

    for idx, (kind, file_path) in enumerate(assets, start=1):
        print(f"[menu-extract] {restaurant.id} → {kind} {idx}/{len(assets)} → {file_path}")

        try:
            data = extract_menu_from_path(file_path, menu_extractor.GROQ_API_KEY)
        except Exception as e:
            print(f"[menu-extract] ERROR on {file_path}: {e}")
            continue

        if not data:
            print(f"[menu-extract] No data returned for {file_path}")
            continue

        restaurant_name = restaurant_name or data.get("restaurant_name")
        phone = phone or data.get("phone")

        cats = data.get("categories") or []
        all_categories.extend(cats)
        print(f"[menu-extract] extracted {len(cats)} categories from this {kind}")

    if not all_categories:
        restaurant.menu_extract_status = "failed"
        restaurant.menu_extract_error = "Extraction produced 0 categories from all assets."
        restaurant.save(update_fields=["menu_extract_status", "menu_extract_error"])
        return False, {"error": restaurant.menu_extract_error}

    final_data = {
        "restaurant_name": restaurant_name,
        "phone": phone,
        "categories": all_categories,
    }

    # Save JSON to Restaurant.menu_json
    try:
        json_bytes = json.dumps(final_data, indent=2, ensure_ascii=False).encode("utf-8")
        fd, tmp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(tmp_path, "wb") as f:
            f.write(json_bytes)

        filename = f"restaurant_{restaurant.id}_menu.json"
        with open(tmp_path, "rb") as f:
            restaurant.menu_json.save(filename, File(f), save=False)

        os.remove(tmp_path)
    except Exception as e:
        print(f"[menu-extract] JSON save error: {e}")
        # continue anyway (DB rebuild still works)

    # Build DB items
    items_from_json = _flatten_categories_to_items(final_data.get("categories") or [])
    if not items_from_json:
        restaurant.menu_extract_status = "failed"
        restaurant.menu_extract_error = "Items list empty after flattening categories."
        restaurant.save(update_fields=["menu_extract_status", "menu_extract_error"])
        return False, {"error": restaurant.menu_extract_error}

    # Bulk rebuild menu (mute embedding signals)
    with suspend_embedding_signals():
        rebuild_menu_from_json(restaurant, items_from_json)

    # Trigger embeddings ONCE
    regenerate_menu_embeddings_for_restaurant.delay(restaurant.id)

    restaurant.menu_extract_status = "succeeded"
    restaurant.menu_extract_error = ""
    restaurant.menu_last_extracted_at = timezone.now()
    restaurant.save(update_fields=["menu_extract_status", "menu_extract_error", "menu_last_extracted_at", "menu_json"])

    return True, {
        "items_count": len(items_from_json),
        "categories_count": len(all_categories),
    }
