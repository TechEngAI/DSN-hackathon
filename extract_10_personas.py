import json
import os
import re
from collections import defaultdict

review_file = r"C:\Users\ADMIN\Documents\my-bct\docs\raw_samples\yelp_reviews_15mb.json"
analytics_dir = r"C:\Users\ADMIN\Documents\my-bct\analytics"
os.makedirs(analytics_dir, exist_ok=True)

exclude_user = "_BcWyKQL16ndpBdggh2kNA"

# Step 1: Group reviews by user_id
user_reviews = defaultdict(list)

with open(review_file, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            uid = data["user_id"]
            if uid == exclude_user:
                continue
            user_reviews[uid].append(data)
        except Exception:
            pass

# Step 2: Sort users by review count to get 10 rich user histories
sorted_users = sorted(user_reviews.items(), key=lambda x: len(x[1]), reverse=True)
top_10 = sorted_users[:10]

# Topic keywords mapping
topic_keywords = {
    "Casual Dining": ["food", "eat", "restaurant", "menu", "wings", "ribs", "shrimp", "pizza", "burger", "taste", "delicious", "dinner", "lunch", "breakfast", "cafe", "bistro", "omelet", "ham", "eggs", "steak"],
    "Nightlife & Drinks": ["bar", "pub", "beer", "drink", "cocktail", "happy hour", "wine", "winery", "brewery", "flanagan"],
    "Retail & Shopping": ["shop", "store", "sale", "mall", "buy", "purchase", "target", "walmart", "winners", "shopping", "merchandise"],
    "Home Services": ["plumber", "pipe", "leak", "fix", "repair", "hardware", "ace", "appliance", "estimate", "service", "yard", "lawn", "shrubs", "plants"],
    "Beauty & Personal Care": ["nails", "salon", "hair", "spa", "polish", "massage", "waxing", "body wash", "lotion", "soap", "candle"],
    "Crafts & Hobbies": ["craft", "fabric", "joann", "michaels", "hobby", "sewing", "book", "read", "library", "books"],
    "Travel & Outdoor": ["hotel", "travel", "tourist", "preserve", "park", "trail", "factory", "creek", "nature", "scenery"]
}

# Nigerian Cultural Proxy mappings based on topics
def determine_lifestyle_profile(topics, reviews):
    text_blob = " ".join([r["text"].lower() for r in reviews]).lower()
    
    # Check for Nightlife / Alcohol
    if "Nightlife & Drinks" in topics or any(x in text_blob for x in ["beer", "wine", "cocktail", "bar", "pub"]):
        if any(x in text_blob for x in ["wine", "cocktail", "bistro"]):
            return "Detty_December_Vibe"  # upscale party/nightlife
        return "Beer_Parlour_Regular"
        
    # Check for Food / Casual Eating
    if "Casual Dining" in topics or any(x in text_blob for x in ["food", "wings", "pizza", "burger"]):
        if any(x in text_blob for x in ["wings", "barbecue", "bbq", "ribs"]):
            return "Suya_Enthusiast"
        return "Buka_Regular"
        
    # Check for High-end / Shopping / Personal Care
    if any(x in topics for x in ["Beauty & Personal Care", "Retail & Shopping"]):
        if any(x in text_blob for x in ["nails", "spa", "lotion", "salon"]):
            return "Slay_Queen_Vibe"
        return "Ajebutter_Executive"
        
    # Check for Home / Yard / DIY
    if "Home Services" in topics or any(x in text_blob for x in ["yard", "plants", "plumber", "repair", "hardware"]):
        return "Landlord_Vibe"
        
    # Check for Hobbies / Books / Crafts
    if "Crafts & Hobbies" in topics or any(x in text_blob for x in ["book", "read", "fabric", "craft"]):
        return "Book_and_Chill_Vibe"
        
    return "Soft_Life_Chaser"

# Build personas for each of the top 10 users
personas = []

for idx, (uid, revs) in enumerate(top_10):
    # Calculate average rating
    avg_rating = sum(r["stars"] for r in revs) / len(revs)
    
    # Rating bias logic (threshold = 3.85)
    rating_bias = "appreciative_inclined" if avg_rating > 3.85 else "critically_inclined"
    
    # Detect topics
    text_blob = " ".join([r["text"].lower() for r in revs])
    user_topics = []
    for topic, keywords in topic_keywords.items():
        if any(k in text_blob for k in keywords):
            user_topics.append(topic)
    if not user_topics:
        user_topics = ["General Lifestyle"]
        
    # Determine lifestyle profile
    lifestyle_profile = determine_lifestyle_profile(user_topics, revs)
    
    # Custom review style notes mapping to 100-word target
    # Generate notes describing their actual writing features
    has_excl = any("!" in r["text"] for r in revs)
    has_question = any("?" in r["text"] for r in revs)
    avg_len = sum(len(r["text"].split()) for r in revs) / len(revs)
    
    notes = f"Writes detailed, conversational reviews targeting an average length of 100 words. "
    if avg_len > 120:
        notes += "Tends to write longer, chronological stories detailing step-by-step experiences. "
    else:
        notes += "Focuses on providing brief, direct summaries of quality and convenience. "
        
    if has_excl:
        notes += "Frequently uses exclamation marks for emphasizing positive or negative feelings. "
    if has_question:
        notes += "Uses rhetorical questions to express mild disappointment or confusion. "
        
    notes += f"Maintains a rating average of {avg_rating:.2f} stars."
    
    persona = {
      "user_id": uid,
      "rating_bias": rating_bias,
      "preferred_topics": user_topics[:3], # Cap at 3 topics
      "lifestyle_profile": lifestyle_profile,
      "naija_cues": True,
      "review_style_notes": notes
    }
    personas.append(persona)

# Write to file
dest_file = os.path.join(analytics_dir, "validation_10_personas.json")
with open(dest_file, "w", encoding="utf-8") as f:
    json.dump(personas, f, indent=2)

print(f"Successfully generated 10 personas in {dest_file}")
print("Sample personas:")
print(json.dumps(personas[:2], indent=2))
