#!/usr/bin/env python3
"""
Test script for AI-powered chatbot engine.
Run this to verify your setup before integrating with Django.

Usage:
    python test_ai_engine.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path if running standalone
sys.path.insert(0, str(Path(__file__).parent))

from engine import parse_message, load_rag_system


def print_result(query: str, result):
    """Pretty print test results."""
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    print(f"Intent: {result.intent}")
    print(f"Reply: {result.reply}")
    if result.item_name:
        print(f"Item: {result.item_name}")
    if result.quantity > 1:
        print(f"Quantity: {result.quantity}")
    print(f"Confidence: {result.confidence:.2f}")
    print()


def run_tests():
    """Run a series of test queries."""
    print("\n🤖 AI-Powered Chatbot Engine Test Suite")
    print("="*60)
    
    # Load the RAG system
    try:
        load_rag_system()
        print("✅ RAG system loaded successfully!")
    except Exception as e:
        print(f"❌ Failed to load RAG system: {e}")
        print("\nMake sure you have:")
        print("1. menu_embeddings.npy")
        print("2. text_chunks.json")
        print("3. GROQ_API_KEY in .env")
        return
    
    # Test cases
    test_queries = [
        # Basic commands
        "menu",
        "cart",
        "clear",
        "confirm",
        
        # Natural language - menu browsing
        "what do you have",
        "show me your dishes",
        "what can I order",
        
        # Natural language - adding items
        "I want butter naan",
        "add 2 paneer tikka",
        "get me some naan bread",
        "I'd like to order butter chicken",
        
        # Fuzzy/typo queries
        "add buter nan",
        "paner tika",
        
        # Descriptive queries (semantic search)
        "something spicy",
        "show me breads",
        "vegetarian options",
        
        # Quantity variations
        "add 3 naan",
        "I want 2 butter naan and 1 paneer",
        
        # Cart operations
        "what's in my cart",
        "remove butter naan",
        "clear everything",
        
        # Edge cases
        "",
        "hello",
        "help",
        "xyz123",
    ]
    
    print("\n📊 Running test queries...\n")
    
    success_count = 0
    for query in test_queries:
        try:
            result = parse_message(query)
            print_result(query, result)
            
            # Count as success if not HELP or has high confidence
            if result.intent != "HELP" or result.confidence > 0.7:
                success_count += 1
                
        except Exception as e:
            print(f"\n❌ Error processing '{query}': {e}\n")
    
    # Summary
    print("\n" + "="*60)
    print("📈 Test Summary")
    print("="*60)
    print(f"Total queries: {len(test_queries)}")
    print(f"Successful: {success_count}/{len(test_queries)}")
    print(f"Success rate: {success_count/len(test_queries)*100:.1f}%")
    
    # Check for common issues
    print("\n✅ System Check:")
    print(f"   Embeddings: {'✓' if Path('menu_embeddings.npy').exists() else '✗'}")
    print(f"   Text chunks: {'✓' if Path('text_chunks.json').exists() else '✗'}")
    print(f"   GROQ_API_KEY: {'✓' if os.getenv('GROQ_API_KEY') else '✗'}")


def interactive_mode():
    """Run interactive testing mode."""
    print("\n💬 Interactive Mode")
    print("="*60)
    print("Type your queries (or 'exit' to quit):\n")
    
    try:
        load_rag_system()
    except Exception as e:
        print(f"❌ Failed to load RAG system: {e}")
        return
    
    while True:
        try:
            query = input("You: ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("Goodbye! 👋")
                break
            
            if not query:
                continue
            
            result = parse_message(query)
            print(f"\nBot ({result.intent}, conf={result.confidence:.2f}): {result.reply}")
            
            if result.item_name:
                print(f"     → Item: {result.item_name} x {result.quantity}")
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AI-powered chatbot engine")
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        run_tests()
