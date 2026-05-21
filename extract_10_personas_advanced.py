import json
import os
import re
import shutil
from collections import defaultdict

# Setup directories
workspace_dir = r"C:\Users\ADMIN\Documents\my-bct"
analytics_dir = os.path.join(workspace_dir, "analytics")
os.makedirs(analytics_dir, exist_ok=True)

# 1. Copy cultural_proxy_map.json to analytics/ folder
src_map = os.path.join(workspace_dir, "cultural_proxy_map.json")
dst_map = os.path.join(analytics_dir, "cultural_proxy_map.json")
if os.path.exists(src_map):
    shutil.copy(src_map, dst_map)
    print(f"Copied {src_map} to {dst_map}")

# 2. Create analytics/behavioral_templates.json
templates_path = os.path.join(analytics_dir, "behavioral_templates.json")
templates_data = {
  "rating_bias_baseline_stars": 3.85,
  "target_average_review_length_words": 100,
  "style_anchors": {
    "Emotional Intensity": {
      "description": "Exhibits high emotional expression via ALL-CAPS words, multiple exclamation marks, or direct blunt terminology.",
      "trait_mapping": "Zero Chills / Direct"
    },
    "Staff & Respect Focus": {
      "description": "Mentions greetings, server attentiveness, or manager attitude, indicating focus on interpersonal respect.",
      "trait_mapping": "Strict Protocol / Elder Respect"
    },
    "Price/Portion Inspection": {
      "description": "Breaks down billing, costs, pricing tiers, discounts, or quantity value.",
      "trait_mapping": "Value-for-Money Hawk"
    }
  }
}

with open(templates_path, "w", encoding="utf-8") as f:
    json.dump(templates_data, f, indent=2)
print(f"Created behavioral templates at {templates_path}")


# 3. Analyze yelp_reviews_15mb.json for the next 10 users
review_file = os.path.join(workspace_dir, "docs", "raw_samples", "yelp_reviews_15mb.json")
exclude_user = "_BcWyKQL16ndpBdggh2kNA"

# Group reviews by user_id
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

# Get top 10 users by review count (richest histories for analysis)
sorted_users = sorted(user_reviews.items(), key=lambda x: len(x[1]), reverse=True)
top_10 = sorted_users[:10]

topic_keywords = {
    "Casual Dining": ["food", "eat", "restaurant", "menu", "wings", "ribs", "shrimp", "pizza", "burger", "taste", "delicious", "dinner", "lunch", "breakfast", "cafe", "bistro", "omelet", "ham", "eggs", "steak"],
    "Nightlife & Drinks": ["bar", "pub", "beer", "drink", "cocktail", "happy hour", "wine", "winery", "brewery", "flanagan"],
    "Retail & Shopping": ["shop", "store", "sale", "mall", "buy", "purchase", "target", "walmart", "winners", "shopping", "merchandise"],
    "Home Services": ["plumber", "pipe", "leak", "fix", "repair", "hardware", "ace", "appliance", "estimate", "service", "yard", "lawn", "shrubs", "plants"],
    "Beauty & Personal Care": ["nails", "salon", "hair", "spa", "polish", "massage", "waxing", "body wash", "lotion", "soap", "candle"],
    "Crafts & Hobbies": ["craft", "fabric", "joann", "michaels", "hobby", "sewing", "book", "read", "library", "books"],
    "Travel & Outdoor": ["hotel", "travel", "tourist", "preserve", "park", "trail", "factory", "creek", "nature", "scenery"]
}

def determine_lifestyle_profile(topics, text):
    text_lower = text.lower()
    # Cross-reference with cultural_proxy_map categories
    if "Nightlife & Drinks" in topics or any(x in text_lower for x in ["beer", "wine", "cocktail", "bar", "pub"]):
        if any(x in text_lower for x in ["wine", "cocktail", "bistro"]):
            return "Detty_December_Vibe"
        return "Beer_Parlour_Regular"
    if "Casual Dining" in topics or any(x in text_lower for x in ["food", "wings", "pizza", "burger", "bistro"]):
        if any(x in text_lower for x in ["wings", "barbecue", "bbq", "ribs", "spicy"]):
            return "Suya_Enthusiast"
        return "Buka_Regular"
    if "Beauty & Personal Care" in topics or any(x in text_lower for x in ["nails", "salon", "spa", "lotion"]):
        return "Slay_Queen_Vibe"
    if "Retail & Shopping" in topics or any(x in text_lower for x in ["shop", "store", "purchase", "target"]):
        return "Ajebutter_Executive"
    if "Home Services" in topics or any(x in text_lower for x in ["plumber", "repair", "hardware", "yard"]):
        return "Landlord_Vibe"
    if "Crafts & Hobbies" in topics or any(x in text_lower for x in ["book", "read", "fabric", "craft"]):
        return "Book_and_Chill_Vibe"
    return "Soft_Life_Chaser"

personas = []

for idx, (uid, revs) in enumerate(top_10):
    # Calculate average rating
    avg_rating = sum(r["stars"] for r in revs) / len(revs)
    
    # Rating bias logic (threshold = 3.85)
    rating_bias = "appreciative_inclined" if avg_rating > 3.85 else "critically_inclined"
    
    # Detect topics
    text_blob = " ".join([r["text"] for r in revs])
    text_blob_lower = text_blob.lower()
    
    user_topics = []
    for topic, keywords in topic_keywords.items():
        if any(k in text_blob_lower for k in keywords):
            user_topics.append(topic)
    if not user_topics:
        user_topics = ["General"]
        
    lifestyle_profile = determine_lifestyle_profile(user_topics, text_blob)
    
    # Extract Naija Cues (anchored style patterns)
    style_traits = []
    
    # 1. Emotional Intensity -> 'Zero Chills / Direct'
    # Markers: caps lock, heavy exclamation points, blunt language
    caps_words = re.findall(r"\b[A-Z]{4,}\b", text_blob)
    has_heavy_excl = text_blob.count("!!") > 0 or text_blob.count("!") > 3
    blunt_words = ["disgusting", "horrible", "terrible", "waste", "yick", "ouch", "wronged", "bad", "worst", "hate"]
    has_blunt = any(w in text_blob_lower for w in blunt_words)
    
    if len(caps_words) > 0 or has_heavy_excl or has_blunt:
        style_traits.append("Zero Chills / Direct")
        
    # 2. Staff & Respect Focus -> 'Strict Protocol / Elder Respect'
    # Markers: employee attitudes, greetings, attentiveness
    staff_words = ["staff", "waiter", "steward", "manager", "owner", "service", "friendly", "helpful", "kind", "rude", "greeted", "attitude", "attentive"]
    if any(w in text_blob_lower for w in staff_words):
        style_traits.append("Strict Protocol / Elder Respect")
        
    # 3. Price/Portion Inspection -> 'Value-for-Money Hawk'
    # Markers: detailed breakdowns of value, pricing, billing
    price_words = ["price", "cost", "dollar", "bill", "$", "pricey", "expensive", "quote", "charge", "fee", "cheap", "value", "coupon", "off"]
    if any(w in text_blob_lower for w in price_words):
        style_traits.append("Value-for-Money Hawk")
        
    # Build style notes referencing targets and traits
    notes = "Writes reviews targeting an average length of 100 words. "
    if style_traits:
        notes += "Exhibits style traits: " + ", ".join([f"'{t}'" for t in style_traits]) + ". "
    notes += f"Tone is conversational and detail-focused based on an average rating history of {avg_rating:.2f} stars."
    
    persona = {
      "user_id": uid,
      "rating_bias": rating_bias,
      "preferred_topics": user_topics[:3],
      "lifestyle_profile": lifestyle_profile,
      "naija_cues": True,
      "review_style_notes": notes
    }
    personas.append(persona)

# Write output file
validation_file = os.path.join(analytics_dir, "validation_10_personas.json")
with open(validation_file, "w", encoding="utf-8") as f:
    json.dump(personas, f, indent=2)

print("SUCCESS")
