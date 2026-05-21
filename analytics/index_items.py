import os
import sys
import csv

# Add dsn-bct-hackathon to sys.path so we can import app modules
sys.path.append(os.path.abspath("dsn-bct-hackathon"))

# Force local ChromaDB mode
os.environ["USE_LOCAL_CHROMA"] = "true"

from app.chromadb_client import VectorStore

def index_all():
    print("Initializing VectorStore...")
    db = VectorStore()
    if db.connection_error:
        print(f"Error: {db.connection_error}")
        return
        
    csv_path = "analytics/clean_item_metadata.csv"
    if not os.path.exists(csv_path):
        print(f"Error: metadata CSV not found at {csv_path}")
        return
        
    print(f"Reading items from {csv_path}...")
    items = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row["item_id"]
            name = row["name"]
            domain = row["domain"]
            categories = row["categories"]
            location = row["location"]
            stars = float(row["stars"]) if row["stars"] else 0.0
            
            # Format natural language document for embedding
            text = f"Name: {name}. Domain: {domain}. Categories: {categories}. Location: {location}. Rating: {stars} stars."
            
            # Flat metadata for ChromaDB querying/filtering
            metadata = {
                "item_id": item_id,
                "name": name,
                "domain": domain,
                "categories": categories,
                "location": location,
                "stars": stars
            }
            
            items.append({
                "id": item_id,
                "text": text,
                "metadata": metadata
            })
            
    print(f"Staged {len(items)} items. Indexing to ChromaDB...")
    result = db.add_items(items)
    if result.get("success"):
        print(f"Success! Indexed {result['indexed']} items into collection '{db.collection_name}'.")
        print(f"Total count in collection: {db.get_collection_count()}")
    else:
        print(f"Failed to index items: {result.get('error')}")

if __name__ == "__main__":
    index_all()
