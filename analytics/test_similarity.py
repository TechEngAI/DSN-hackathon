import os
import sys

# Add dsn-bct-hackathon to sys.path so we can import app modules
sys.path.append(os.path.abspath("dsn-bct-hackathon"))

# Force local ChromaDB mode
os.environ["USE_LOCAL_CHROMA"] = "true"

from app.chromadb_client import VectorStore

def test_queries():
    print("Initializing VectorStore...")
    db = VectorStore()
    if db.connection_error:
        print(f"Connection Error: {db.connection_error}")
        return
        
    count = db.get_collection_count()
    print(f"Total count in collection: {count}")
    
    # Test queries
    test_queries = [
        "spicy chicken wings and beer",
        "shopping for electronics",
        "home repair plumber leak",
        "beauty spa hair nails salon"
    ]
    
    for query in test_queries:
        print("\n" + "="*50)
        print(f"Query: '{query}'")
        print("="*50)
        results = db.search(query, n_results=3)
        for idx, match in enumerate(results):
            metadata = match.get("metadata", {})
            print(f"{idx+1}. ID: {match['id']} (Score: {match['score']:.4f})")
            print(f"   Name: {metadata.get('name')}")
            print(f"   Domain: {metadata.get('domain')}")
            print(f"   Categories: {metadata.get('categories')}")
            print(f"   Location: {metadata.get('location')}")
            print(f"   Rating: {metadata.get('stars')} stars")
            print(f"   Document Text: {match['text']}\n")

if __name__ == "__main__":
    test_queries()
