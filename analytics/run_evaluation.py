import os
import sys
import json
import csv
import math
import re

# Add dsn-bct-hackathon to sys.path so we can import app modules
sys.path.append(os.path.abspath("dsn-bct-hackathon"))
os.environ["USE_LOCAL_CHROMA"] = "true"

from app.chromadb_client import VectorStore
from app.task_a import generate_review, GenerateReviewRequest
from chromadb.utils import embedding_functions

# ----------------------------------------------------------------------
# 1. Metric Computation Utilities
# ----------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, removing punctuation."""
    text = text.lower()
    return re.findall(r"\b\w+\b", text)

def lcs(x: list[str], y: list[str]) -> int:
    """Computes the length of the Longest Common Subsequence of x and y using DP."""
    m, n = len(x), len(y)
    if m == 0 or n == 0:
        return 0
    # Keep only two rows for memory optimization
    dp = [0] * (n + 1)
    for i in range(1, m + 1):
        prev = 0
        for j in range(1, n + 1):
            temp = dp[j]
            if x[i - 1] == y[j - 1]:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev = temp
    return dp[n]

def compute_rouge_l(ref: str, cand: str) -> float:
    """Computes ROUGE-L F1 score based on word-level LCS."""
    x = tokenize(ref)
    y = tokenize(cand)
    m, n = len(x), len(y)
    if m == 0 or n == 0:
        return 0.0
    lcs_len = lcs(x, y)
    r = lcs_len / m
    p = lcs_len / n
    if r + p == 0:
        return 0.0
    return (2 * r * p) / (r + p)

def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Computes cosine similarity between two vectors. Since Chroma embeddings are normalized, dot product suffices."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    return max(0.0, min(1.0, dot_product))

# ----------------------------------------------------------------------
# 2. Main Evaluation Pipeline
# ----------------------------------------------------------------------

def evaluate():
    print("="*60)
    print("   RUNNING DSN X BCT HACKATHON METRICS & EVALUATION (DAY 5)")
    print("="*60)

    # 2.1 Load Validation Personas
    personas_path = "analytics/validation_10_personas.json"
    if not os.path.exists(personas_path):
        print(f"Error: {personas_path} not found.")
        sys.exit(1)
    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)
    p_users = {p["user_id"]: p for p in personas}
    print(f"Loaded {len(personas)} validation personas.")

    # 2.2 Initialize Vector Store and Embedding Function
    db = VectorStore()
    if db.connection_error:
        print(f"Error: {db.connection_error}")
        sys.exit(1)
    
    ef = embedding_functions.DefaultEmbeddingFunction()
    
    # Get all items in database to count total count and check relevance labels
    db_items = db.collection.get()
    all_db_ids = db_items.get("ids", [])
    all_db_metadatas = db_items.get("metadatas", [])
    print(f"Database contains {len(all_db_ids)} items.")

    # ----------------------------------------------------------------------
    # Task A Evaluation (User Modeling: RMSE, ROUGE-L, BERTScore F1 equiv)
    # ----------------------------------------------------------------------
    print("\n--- Running Task A (User Modeling) Evaluation ---")
    reviews_path = "docs/raw_samples/yelp_reviews_15mb.json"
    if not os.path.exists(reviews_path):
        print(f"Error: {reviews_path} not found.")
        sys.exit(1)

    task_a_logs = []
    squared_errors = []
    rouge_l_scores = []
    bertscore_f1s = []

    count = 0
    with open(reviews_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                review_gt = json.loads(line)
            except Exception:
                continue

            u_id = review_gt.get("user_id")
            if u_id not in p_users:
                continue

            count += 1
            item_id = "yelp_" + review_gt.get("business_id")
            stars_gt = float(review_gt.get("stars", 3.0))
            text_gt = review_gt.get("text", "")

            # Generate review using the target persona
            persona = p_users[u_id]
            req = GenerateReviewRequest(
                user_id=u_id,
                item_id=item_id,
                persona=persona
            )
            res = generate_review(req)
            
            stars_pred = float(res.rating)
            text_pred = res.review_text

            # Compute Task A metrics
            se = (stars_pred - stars_gt) ** 2
            rouge_l = compute_rouge_l(text_gt, text_pred)
            
            # Embed reference and candidate for BERTScore equivalent
            emb_ref = ef([text_gt])[0]
            emb_cand = ef([text_pred])[0]
            bertscore_f1 = compute_cosine_similarity(emb_ref, emb_cand)

            squared_errors.append(se)
            rouge_l_scores.append(rouge_l)
            bertscore_f1s.append(bertscore_f1)

            task_a_logs.append({
                "user_id": u_id,
                "item_id": item_id,
                "rating_gt": stars_gt,
                "rating_pred": stars_pred,
                "error": stars_pred - stars_gt,
                "rouge_l": rouge_l,
                "bertscore_f1": bertscore_f1
            })

            if count % 10 == 0:
                print(f"Processed {count} reviews...")

    # Calculate Aggregate Task A Metrics
    num_reviews = len(squared_errors)
    if num_reviews > 0:
        rmse = math.sqrt(sum(squared_errors) / num_reviews)
        avg_rouge_l = sum(rouge_l_scores) / num_reviews
        avg_bertscore = sum(bertscore_f1s) / num_reviews
    else:
        rmse, avg_rouge_l, avg_bertscore = 0.0, 0.0, 0.0

    print(f"Task A Evaluation completed over {num_reviews} reviews:")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  ROUGE-L F1: {avg_rouge_l:.4f}")
    print(f"  BERTScore F1 Equiv: {avg_bertscore:.4f}")

    # ----------------------------------------------------------------------
    # Task B Evaluation (Recommendation: NDCG@10, Hit Rate)
    # ----------------------------------------------------------------------
    print("\n--- Running Task B (Recommendation) Evaluation ---")
    
    # Helper to check relevance of item to lifestyle profile
    def is_item_relevant(metadata: dict, profile: str) -> bool:
        name = str(metadata.get("name", "")).lower()
        cats = str(metadata.get("categories", "")).lower()
        
        if profile == "Beer_Parlour_Regular":
            # Matches pubs, bars, local joints, suya spots, beer parlours
            return any(k in cats or k in name for k in ["pub", "bar", "parlour", "nightlife", "suya", "chilli", "bungalow"])
        elif profile == "Detty_December_Vibe":
            # Matches nightlife, lounges, cocktail spots, restaurants, shopping malls
            return any(k in cats or k in name for k in ["nightlife", "cocktail", "lounge", "bar", "restaurant", "shopping", "mall", "jazzhole"])
        elif profile == "Suya_Enthusiast":
            return any(k in cats or k in name for k in ["suya", "grill", "spice", "specialty food", "african", "restaurant"])
        elif profile == "Buka_Regular":
            return any(k in cats or k in name for k in ["buka", "mama put", "african", "restaurant", "food"])
        elif profile == "Slay_Queen_Vibe":
            return any(k in cats or k in name for k in ["beauty", "salon", "spa", "hair", "nail", "mall", "shopping"])
        elif profile == "Ajebutter_Executive":
            return any(k in cats or k in name for k in ["brunch", "cafe", "fusion", "seafood", "bookstore", "restaurant"])
        elif profile == "Landlord_Vibe":
            return any(k in cats or k in name for k in ["home services", "real estate", "repair", "dentist"])
        elif profile == "Book_and_Chill_Vibe":
            return any(k in cats or k in name for k in ["book", "cafe", "coffee", "tea", "library"])
        elif profile == "Soft_Life_Chaser":
            return any(k in cats or k in name for k in ["spa", "salon", "cafe", "restaurant", "soft life", "mall"])
        return False

    task_b_logs = []
    hit_rates = []
    ndcgs = []

    # Map queries to lifestyle profiles for evaluation
    queries_map = {
        "Beer_Parlour_Regular": "cold beer, grilled suya, local joint hangout after work",
        "Detty_December_Vibe": "nightlife club, cocktails, lounge and party music",
        "Suya_Enthusiast": "hot spicy suya and grilled beef",
        "Buka_Regular": "local buka amala, pounded yam, local food",
        "Slay_Queen_Vibe": "beauty spa, hair extension styling and nails",
        "Ajebutter_Executive": "nice brunch, high-end cafe, seafood fusion dining",
        "Landlord_Vibe": "plumber repair work or home repair inspection",
        "Book_and_Chill_Vibe": "quiet cafe bookstore, book reading and coffee",
        "Soft_Life_Chaser": "luxury massage salon, relaxing spa session"
    }

    # Pre-calculate the total number of relevant items in database for each profile to compute IDCG
    profile_total_relevant = {}
    for profile in queries_map.keys():
        relevant_count = 0
        for meta in all_db_metadatas:
            if is_item_relevant(meta, profile):
                relevant_count += 1
        profile_total_relevant[profile] = relevant_count

    for u_id, persona in p_users.items():
        profile = persona.get("lifestyle_profile", "Soft_Life_Chaser")
        query = queries_map.get(profile, "nice food and drinks")
        
        # Get recommendations from vector store
        results = db.search(query, n_results=10)
        
        # Calculate relevance scores
        rel_list = []
        for match in results:
            meta = match.get("metadata", {})
            rel_list.append(1 if is_item_relevant(meta, profile) else 0)
        
        # Calculate DCG@10
        dcg = 0.0
        for idx, rel in enumerate(rel_list):
            dcg += rel / math.log2(idx + 2)
            
        # Calculate IDCG@10
        total_rel = profile_total_relevant.get(profile, 0)
        idcg = 0.0
        for idx in range(min(10, total_rel)):
            idcg += 1.0 / math.log2(idx + 2)
        if idcg == 0.0:
            idcg = 1.0  # Avoid division by zero
            
        ndcg = dcg / idcg
        hit = 1 if sum(rel_list) >= 1 else 0
        
        hit_rates.append(hit)
        ndcgs.append(ndcg)
        
        task_b_logs.append({
            "user_id": u_id,
            "profile": profile,
            "query": query,
            "recommendations": [r["id"] for r in results],
            "relevance": rel_list,
            "hit_rate_10": hit,
            "ndcg_10": ndcg
        })
        
    avg_hit_rate = sum(hit_rates) / len(hit_rates)
    avg_ndcg = sum(ndcgs) / len(ndcgs)
    
    print(f"Task B Evaluation completed over {len(p_users)} personas:")
    print(f"  Hit Rate@10: {avg_hit_rate:.4f}")
    print(f"  NDCG@10: {avg_ndcg:.4f}")

    # ----------------------------------------------------------------------
    # 3. Save All Results to CSV
    # ----------------------------------------------------------------------
    output_csv = "analytics/evaluation_results.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["=== DSN x BCT HACKATHON EVALUATION SUMMARY ==="])
        writer.writerow([])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Task A (User Modeling) - Evaluated Records", num_reviews])
        writer.writerow(["Task A (User Modeling) - Rating RMSE", rmse])
        writer.writerow(["Task A (User Modeling) - Review ROUGE-L F1", avg_rouge_l])
        writer.writerow(["Task A (User Modeling) - Review BERTScore F1 Equiv", avg_bertscore])
        writer.writerow(["Task B (Recommendation) - Evaluated Personas", len(p_users)])
        writer.writerow(["Task B (Recommendation) - Hit Rate@10", avg_hit_rate])
        writer.writerow(["Task B (Recommendation) - NDCG@10", avg_ndcg])
        writer.writerow([])
        writer.writerow(["=== INDIVIDUAL TASK A LOGS ==="])
        writer.writerow(["User ID", "Item ID", "Rating Ground-Truth", "Rating Predicted", "Error", "ROUGE-L F1", "BERTScore F1 Equiv"])
        for row in task_a_logs:
            writer.writerow([row["user_id"], row["item_id"], row["rating_gt"], row["rating_pred"], row["error"], row["rouge_l"], row["bertscore_f1"]])
        writer.writerow([])
        writer.writerow(["=== INDIVIDUAL TASK B LOGS ==="])
        writer.writerow(["User ID", "Profile", "Query", "Hit Rate@10", "NDCG@10", "Recommendations List"])
        for row in task_b_logs:
            writer.writerow([row["user_id"], row["profile"], row["query"], row["hit_rate_10"], row["ndcg_10"], ";".join(row["recommendations"])])
            
    print(f"\nEvaluation successfully compiled and logged to: {output_csv}")

if __name__ == "__main__":
    evaluate()
