import json
import csv
import os

# Paths to input files
YELP_PATH = "docs/raw_samples/yelp_academic_dataset_business.json"
AMAZON_PATH = "dsn-bct-hackathon/data/sample_data.json" 
OUTPUT_CSV = "analytics/clean_item_metadata.csv"

# Ensure output directory exists
os.makedirs("analytics", exist_ok=True)

print("Extracting data arrays and building metadata staging CSV...")

with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as csv_file:
    fieldnames = ["item_id", "name", "domain", "categories", "location", "stars"]
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    
    count_yelp = 0
    count_amazon = 0

    # 1. Parse Yelp Businesses
    if os.path.exists(YELP_PATH):
        with open(YELP_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    biz = json.loads(line)
                    writer.writerow({
                        "item_id": f"yelp_{biz['business_id']}",
                        "name": biz["name"],
                        "domain": "yelp",
                        "categories": biz.get("categories", "General"),
                        "location": f"{biz['city']}, {biz['state']}",
                        "stars": float(biz["stars"])
                    })
                    count_yelp += 1
                except Exception:
                    continue
    else:
        print(f"Warning: Yelp file not found at: {YELP_PATH}")

    # 2. Parse Amazon Products (For 25-pt Cross-Domain Requirements)
    if os.path.exists(AMAZON_PATH):
        try:
            # Try parsing as a full JSON array first
            with open(AMAZON_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("["):
                    products = json.loads(content)
                else:
                    # Fallback to JSON Lines
                    products = []
                    f.seek(0)
                    for line in f:
                        if line.strip():
                            products.append(json.loads(line))
            
            for prod in products:
                try:
                    # Safely handle potential field variances in Amazon schema
                    item_id = prod.get("asin") or prod.get("item_id") or prod.get("id")
                    title = prod.get("title") or prod.get("name") or "Amazon Product"
                    category = prod.get("category") or "E-Commerce"
                    rating = prod.get("overall") or prod.get("stars") or 4.0
                    
                    if item_id:
                        writer.writerow({
                            "item_id": f"amazon_{item_id}",
                            "name": title,
                            "domain": "amazon",
                            "categories": category,
                            "location": "Online / E-Commerce",
                            "stars": float(rating)
                        })
                        count_amazon += 1
                except Exception:
                    continue
        except Exception as exc:
            print(f"Warning: Error parsing Amazon file: {exc}")
    else:
        print(f"Warning: Amazon file not found at: {AMAZON_PATH}")

    # 3. Add Nigerian Cultural Items Dataset (Day 4 Requirement)
    cultural_items = [
        {"item_id": "yelp_naija_1", "name": "Yellow Chilli Bar & Restaurant", "domain": "yelp", "categories": "Restaurants, Nigerian, African, Casual Dining", "location": "Lagos, LA", "stars": 4.5},
        {"item_id": "yelp_naija_2", "name": "Bungalow Restaurant", "domain": "yelp", "categories": "Restaurants, Fusion, Seafood, Bars, Nightlife", "location": "Lagos, LA", "stars": 4.2},
        {"item_id": "yelp_naija_3", "name": "White House Buka", "domain": "yelp", "categories": "Restaurants, Food, African, Buka, Mama Put", "location": "Lagos, LA", "stars": 4.3},
        {"item_id": "yelp_naija_4", "name": "Mega Plaza Shopping Mall", "domain": "yelp", "categories": "Shopping, Department Stores, Retail & Shopping", "location": "Lagos, LA", "stars": 4.0},
        {"item_id": "yelp_naija_5", "name": "Deano's Beer Parlour", "domain": "yelp", "categories": "Pubs, Bars, Restaurants, Beer Parlour, Nightlife", "location": "Lagos, LA", "stars": 4.4},
        {"item_id": "yelp_naija_6", "name": "Glover Court Suya", "domain": "yelp", "categories": "Food, Restaurants, Suya Joint, Specialty Food, Grill", "location": "Lagos, LA", "stars": 4.7},
        {"item_id": "yelp_naija_7", "name": "Perfect Touch Salon & Spa", "domain": "yelp", "categories": "Beauty & Spas, Hair Salons, Nail Salons, Slay Queen", "location": "Abuja, FC", "stars": 4.6},
        {"item_id": "yelp_naija_8", "name": "Jazzhole Cafe & Bookstore", "domain": "yelp", "categories": "Food, Coffee & Tea, Cafes, Books, Nightlife", "location": "Lagos, LA", "stars": 4.8},
        {"item_id": "amazon_naija_9", "name": "Pack of Active Pepper Suya Spice", "domain": "amazon", "categories": "E-Commerce, Groceries, Spices, Suya", "location": "Online / E-Commerce", "stars": 4.5},
        {"item_id": "amazon_naija_10", "name": "Premium Hand-Woven Ankara Fabric", "domain": "amazon", "categories": "E-Commerce, Fashion, Clothing, Ankara", "location": "Online / E-Commerce", "stars": 4.7}
    ]
    for item in cultural_items:
        writer.writerow(item)
    print(f"Added {len(cultural_items)} Nigerian cultural items to metadata.")

print("Metadata compilation successful!")
print(f"Total Yelp items staged: {count_yelp}")
print(f"Total Amazon items staged: {count_amazon}")
print(f"Staging database file saved to: {OUTPUT_CSV}")
