import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found. Add it to your .env file.")


class MenuChatbot:
    def __init__(self, embeddings_path, model_name='sentence-transformers/all-mpnet-base-v2'):
        """
        Initialize the menu chatbot with embeddings and models.
        
        Args:
            embeddings_path: Path to the pickle file containing embeddings
            model_name: Sentence transformer model for encoding queries
        """
        print("Loading menu embeddings...")
        with open(embeddings_path, 'rb') as f:
            data = pickle.load(f)
            self.embeddings = data['embeddings']
            self.metadata = data['metadata']
        
        print(f"Loaded {len(self.embeddings)} menu items")
        
        print(f"Loading embedding model on CPU: {model_name}")
        self.encoder = SentenceTransformer(model_name, device="cpu")
        
        print("Initializing Groq client...")
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        
        # Conversation history
        self.conversation_history = []
        
        # State management for interactions
        self.awaiting_selection = False
        self.current_search_results = []
        self.interaction_context = {}
        
        print("Chatbot ready!\n")
    
    def cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def search_menu(self, query, top_k=5):
        """
        Search for relevant menu items based on query.
        
        Args:
            query: User's search query
            top_k: Number of top results to return
        
        Returns:
            List of relevant menu items with metadata
        """
        # Encode the query
        query_embedding = self.encoder.encode(query)
        
        # Calculate similarities
        similarities = []
        for idx, embedding in enumerate(self.embeddings):
            sim = self.cosine_similarity(query_embedding, embedding)
            similarities.append((idx, sim))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top k results
        results = []
        for idx, sim in similarities[:top_k]:
            results.append({
                'metadata': self.metadata[idx],
                'similarity': float(sim)
            })
        
        return results
    
    def estimate_calories(self, item_name, category=None, description=None):
        """
        Estimate calories for a menu item using AI.
        
        Args:
            item_name: Name of the item
            category: Category of the item
            description: Description/ingredients
        
        Returns:
            Estimated calorie information as string
        """
        try:
            prompt = f"""Estimate the approximate calories for this menu item. Be brief and realistic.

Item: {item_name}
{f"Category: {category}" if category else ""}
{f"Details: {description}" if description else ""}

Provide ONLY a brief calorie estimate in this format: "~X-Y kcal" or "~X kcal" (where X and Y are numbers).
Be concise - just the calorie range, nothing else."""

            completion = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=50
            )
            
            calorie_info = completion.choices[0].message.content.strip()
            # Clean up the response to ensure it's just the calorie info
            calorie_info = re.sub(r'^[^0-9~]*', '', calorie_info)
            calorie_info = calorie_info.split('\n')[0].strip()
            return calorie_info if calorie_info else "~N/A"
        
        except Exception as e:
            return "~N/A"
    
    def format_menu_list(self, search_results, include_calories=True):
        """
        Format search results as a numbered list with calorie information.
        
        Args:
            search_results: List of search results
            include_calories: Whether to estimate and include calories
        
        Returns:
            Formatted string list
        """
        menu_list = ["\n📋 MENU OPTIONS:"]
        menu_list.append("=" * 70)
        
        for idx, result in enumerate(search_results, 1):
            meta = result['metadata']
            name = meta.get('name', 'Unknown Item')
            category = meta.get('category', '')
            price = meta.get('price', 'N/A')
            
            # Get description for calorie estimation
            description = ""
            if meta.get('original_data'):
                orig = meta['original_data']
                if orig.get('description'):
                    description = orig['description']
                elif orig.get('ingredients'):
                    ing = orig['ingredients'] if isinstance(orig['ingredients'], str) else ', '.join(orig['ingredients'])
                    description = ing
            
            # Estimate calories
            calories = ""
            if include_calories:
                calories = self.estimate_calories(name, category, description)
                calories = f" | {calories}"
            
            # Format the line
            line = f"{idx}. {name}"
            if category:
                line += f" ({category})"
            line += f" - ₹{price}{calories}"
            
            menu_list.append(line)
        
        menu_list.append("=" * 70)
        return '\n'.join(menu_list)
    
    def format_item_details(self, result, item_number=None):
        """Format detailed information about a specific menu item."""
        meta = result['metadata']
        details = []
        
        header = f"📌 {meta.get('name', 'Unknown Item')}"
        if item_number:
            header = f"📌 ITEM #{item_number}: {meta.get('name', 'Unknown Item')}"
        
        details.append("\n" + "=" * 70)
        details.append(header)
        details.append("=" * 70)
        
        if meta.get('category'):
            details.append(f"Category: {meta['category']}")
        
        if meta.get('price'):
            details.append(f"Price: ₹{meta['price']}")
        
        # Estimate calories
        description = ""
        if meta.get('original_data'):
            orig = meta['original_data']
            if orig.get('description'):
                description = orig['description']
                details.append(f"Description: {description}")
            
            if orig.get('ingredients'):
                ing = orig['ingredients'] if isinstance(orig['ingredients'], str) else ', '.join(orig['ingredients'])
                details.append(f"Ingredients: {ing}")
            
            if orig.get('allergens'):
                allergens = orig['allergens'] if isinstance(orig['allergens'], str) else ', '.join(orig['allergens'])
                details.append(f"⚠️  Allergens: {allergens}")
            
            if orig.get('dietary_info'):
                dietary = orig['dietary_info'] if isinstance(orig['dietary_info'], str) else ', '.join(orig['dietary_info'])
                details.append(f"🥗 Dietary Info: {dietary}")
        
        # Add calorie estimate
        calories = self.estimate_calories(meta.get('name', ''), meta.get('category', ''), description)
        details.append(f"🔥 Estimated Calories: {calories}")
        
        details.append("=" * 70)
        
        return '\n'.join(details)
    
    def format_context(self, search_results):
        """Format search results into context for the LLM."""
        context_parts = []
        
        for idx, result in enumerate(search_results, 1):
            meta = result['metadata']
            item_info = []
            
            if meta.get('name'):
                item_info.append(f"Item {idx}: {meta['name']}")
            if meta.get('category'):
                item_info.append(f"Category: {meta['category']}")
            if meta.get('price'):
                item_info.append(f"Price: {meta['price']}")
            
            # Include original data if available
            if meta.get('original_data'):
                orig = meta['original_data']
                if orig.get('description'):
                    item_info.append(f"Description: {orig['description']}")
                if orig.get('ingredients'):
                    ing = orig['ingredients'] if isinstance(orig['ingredients'], str) else ', '.join(orig['ingredients'])
                    item_info.append(f"Ingredients: {ing}")
                if orig.get('allergens'):
                    allergens = orig['allergens'] if isinstance(orig['allergens'], str) else ', '.join(orig['allergens'])
                    item_info.append(f"Allergens: {allergens}")
                if orig.get('dietary_info'):
                    dietary = orig['dietary_info'] if isinstance(orig['dietary_info'], str) else ', '.join(orig['dietary_info'])
                    item_info.append(f"Dietary: {dietary}")
            
            context_parts.append('\n'.join(item_info))
        
        return '\n\n'.join(context_parts)
    
    def check_needs_clarification(self, user_query, search_results):
        """
        Check if the query needs clarification (e.g., multiple options available).
        
        Returns:
            (needs_clarification: bool, clarification_type: str)
        """
        query_lower = user_query.lower()
        
        # Check if user is asking for a broad category with multiple results
        category_keywords = ['pizza', 'burger', 'drink', 'dessert', 'pasta', 'salad', 'coffee', 'tea']
        
        for keyword in category_keywords:
            if keyword in query_lower and len(search_results) > 1:
                return True, "selection"
        
        return False, None
    
    def generate_response(self, user_query, context, show_menu_list=False):
        """
        Generate conversational response using Groq API.
        
        Args:
            user_query: User's question
            context: Retrieved menu items context
            show_menu_list: Whether to show menu as a list first
        
        Returns:
            AI response string
        """
        # Build conversation with history
        messages = [
            {
                "role": "system",
                "content": """You are a friendly and helpful restaurant menu assistant. Your role is to help customers find items from the menu and answer their questions.

IMPORTANT RULES:
1. ONLY recommend items that are in the provided menu context below
2. DO NOT make up or suggest items that are not in the menu
3. If asked about something not in the menu, politely say it's not available
4. Be conversational, warm, and helpful
5. If asked about prices, ingredients, or details, provide accurate information from the menu
6. ALL PRICES ARE IN INR (Indian Rupees). Always mention prices as "₹X" or "Rs. X" or "INR X"
7. When there are multiple options, ask the customer to choose by saying "Please reply with the number (1, 2, 3, etc.) of the item you'd like to know more about"
8. Keep responses concise but friendly
9. When customer shows interest in an item or category with multiple options, guide them to make a selection"""
            }
        ]
        
        # Add conversation history (last 6 messages for context)
        for msg in self.conversation_history[-6:]:
            messages.append(msg)
        
        # Add current query with context
        user_content = f"""Customer question: {user_query}

Available menu items:
{context}

Please answer the customer's question. If there are multiple options and the customer hasn't specified which one, encourage them to select by number."""
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        try:
            completion = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            
            response = completion.choices[0].message.content.strip()
            
            return response
        
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}"
    
    def chat(self, user_query):
        """
        Main chat function - handles user query and returns response.
        
        Args:
            user_query: User's question/message
        
        Returns:
            AI response
        """
        # Check if user is responding with a number (selection)
        if self.awaiting_selection and user_query.strip().isdigit():
            selection = int(user_query.strip())
            
            if 1 <= selection <= len(self.current_search_results):
                selected_item = self.current_search_results[selection - 1]
                
                # Show detailed information
                details = self.format_item_details(selected_item, selection)
                
                # Update conversation history
                self.conversation_history.append({
                    "role": "user",
                    "content": f"Tell me more about item #{selection}"
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": details
                })
                
                # Reset selection state
                self.awaiting_selection = False
                self.current_search_results = []
                
                return details + "\n\nWould you like to know anything else about this item or explore other options?"
            else:
                return f"Please enter a number between 1 and {len(self.current_search_results)}."
        
        # Search for relevant menu items
        search_results = self.search_menu(user_query, top_k=5)
        
        # Check if we need clarification
        needs_clarification, clarification_type = self.check_needs_clarification(user_query, search_results)
        
        # Format context for LLM
        context = self.format_context(search_results)
        
        # Generate conversational response
        response = self.generate_response(user_query, context, needs_clarification)
        
        # If multiple relevant items, show menu list
        if len(search_results) > 1 and needs_clarification:
            menu_list = self.format_menu_list(search_results)
            full_response = f"{response}\n{menu_list}\n\n💬 Reply with a number (1-{len(search_results)}) to learn more about that item!"
            
            # Set state to await selection
            self.awaiting_selection = True
            self.current_search_results = search_results
        else:
            full_response = response
        
        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_query
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })
        
        return full_response
    
    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.awaiting_selection = False
        self.current_search_results = []
        self.interaction_context = {}
        print("Conversation history cleared.")


def main():
    """Interactive chatbot interface."""
    import sys
    
    # Check if embeddings file path is provided
    if len(sys.argv) < 2:
        embeddings_path = "menu_embeddings.pkl"
        print(f"Using default embeddings file: {embeddings_path}")
    else:
        embeddings_path = sys.argv[1]
    
    if not os.path.exists(embeddings_path):
        print(f"Embeddings file not found: {embeddings_path}")
        print("Please provide the correct path to your menu_embeddings.pkl file")
        exit(1)
    
    # Initialize chatbot
    chatbot = MenuChatbot(embeddings_path)
    
    print("=" * 70)
    print("🍽️  RESTAURANT MENU CHATBOT")
    print("=" * 70)
    print("Ask me anything about our menu!")
    print("\nCommands:")
    print("  - 'quit' or 'exit': Exit the chatbot")
    print("  - 'reset': Clear conversation history")
    print("\nTip: When I show you menu options, reply with a number to get details!")
    print("=" * 70)
    print()
    
    # Interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Thanks for chatting! Have a great day!")
                break
            
            if user_input.lower() == 'reset':
                chatbot.reset_conversation()
                continue
            
            # Get response
            print("\n🤖 Assistant:")
            response = chatbot.chat(user_input)
            print(response)
            print()
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print()


if __name__ == "__main__":
    main()