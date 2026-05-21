import os
import sys
import json
import random

# Add dsn-bct-hackathon to sys.path so we can import app modules
sys.path.append(os.path.abspath("dsn-bct-hackathon"))
os.environ["USE_LOCAL_CHROMA"] = "true"

from app.chromadb_client import VectorStore
from app.task_a import generate_review, GenerateReviewRequest

def generate_samples():
    print("Loading validated personas...")
    personas_path = "analytics/validation_10_personas.json"
    if not os.path.exists(personas_path):
        print(f"Error: {personas_path} does not exist.")
        return
        
    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)
        
    print("Initializing VectorStore and fetching item IDs...")
    db = VectorStore()
    if db.connection_error or not db.collection:
        print(f"Error connecting to vector store: {db.connection_error}")
        return
        
    # Get all items in ChromaDB collection
    all_items = db.collection.get()
    item_ids = all_items.get("ids", [])
    if not item_ids:
        print("Error: No items found in ChromaDB collection.")
        return
    
    print(f"Found {len(item_ids)} items in ChromaDB.")
    
    sample_outputs = []
    
    # Generate 2 reviews per persona (total of 20 reviews)
    for idx, persona in enumerate(personas):
        user_id = persona["user_id"]
        # Choose 2 random unique items
        selected_items = random.sample(item_ids, 2)
        
        for item_id in selected_items:
            req = GenerateReviewRequest(
                user_id=user_id,
                item_id=item_id,
                persona=persona
            )
            
            print(f"Generating review for user {user_id} and item {item_id}...")
            res = generate_review(req)
            
            sample_outputs.append({
                "user_id": res.user_id,
                "item_id": res.item_id,
                "rating": res.rating,
                "review_text": res.review_text,
                "naija_cues_applied": res.naija_cues_applied,
                "lifestyle_profile": persona.get("lifestyle_profile"),
                "rating_bias": persona.get("rating_bias")
            })
            
    output_path = "analytics/sample_20_naija_reviews.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sample_outputs, f, indent=2)
        
    print(f"\nSuccessfully generated 20 sample reviews and saved to {output_path}")
    print("\n--- FIRST 3 SAMPLE REVIEWS ---")
    for r in sample_outputs[:3]:
        print(f"\nUser: {r['user_id']} ({r['lifestyle_profile']}, {r['rating_bias']})")
        print(f"Item: {r['item_id']}")
        print(f"Rating: {r['rating']}")
        print(f"Review: {r['review_text']}")
        print(f"Naija Cues Applied: {r['naija_cues_applied']}")

if __name__ == "__main__":
    generate_samples()
