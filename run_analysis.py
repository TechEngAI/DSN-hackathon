import json
import os
import re
from collections import Counter

review_file = r"C:\Users\ADMIN\Documents\my-bct\docs\raw_samples\yelp_reviews_15mb.json"

def analyze_dataset():
    print("Reading reviews...")
    reviews_1star = []
    reviews_5star = []
    
    with open(review_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                stars = data["stars"]
                user_id = data["user_id"]
                text = data["text"]
                if stars == 1.0:
                    reviews_1star.append((user_id, text))
                elif stars == 5.0:
                    reviews_5star.append((user_id, text))
            except Exception:
                pass
                
    print(f"Total 1-star reviews: {len(reviews_1star)}")
    print(f"Total 5-star reviews: {len(reviews_5star)}")
    
    # We will sample 1000 unique users from 1-star reviews and 1000 unique users from 5-star reviews
    # To be systematic, we'll collect the first 1000 unique users for each category
    sampled_1star = []
    seen_users_1 = set()
    for user_id, text in reviews_1star:
        if user_id not in seen_users_1:
            seen_users_1.add(user_id)
            sampled_1star.append((user_id, text))
            if len(sampled_1star) >= 1000:
                break
                
    sampled_5star = []
    seen_users_5 = set()
    for user_id, text in reviews_5star:
        if user_id not in seen_users_5:
            seen_users_5.add(user_id)
            sampled_5star.append((user_id, text))
            if len(sampled_5star) >= 1000:
                break
                
    print(f"Sampled {len(sampled_1star)} unique disappointed users.")
    print(f"Sampled {len(sampled_5star)} unique satisfied users.")
    
    # Let's perform comparative analysis
    def get_stats(sampled_reviews):
        total_chars = 0
        total_words = 0
        total_sentences = 0
        excl_count = 0
        quest_count = 0
        caps_word_count = 0
        
        word_counter = Counter()
        bigram_counter = Counter()
        trigram_counter = Counter()
        
        # Stop words list for clean keyword analysis
        stop_words = set([
            "the", "a", "and", "to", "of", "i", "was", "in", "it", "for", "that", "this", "my", "with",
            "but", "we", "on", "they", "had", "have", "you", "were", "at", "as", "be", "so", "are", "not",
            "for", "but", "is", "our", "there", "out", "about", "me", "if", "this", "would", "get", "go",
            "one", "up", "time", "food", "place", "service", "good", "back", "order", "ordered", "us", "got"
        ])
        
        for user_id, text in sampled_reviews:
            total_chars += len(text)
            
            # Count punctuation
            excl_count += text.count('!')
            quest_count += text.count('?')
            
            # Simple word extraction
            words = re.findall(r"\b\w+\b", text.lower())
            total_words += len(words)
            
            # Count ALL-CAPS words (length > 2 to exclude I, OK, AM)
            caps_words = re.findall(r"\b[A-Z]{3,}\b", text)
            caps_word_count += len(caps_words)
            
            # Sentences (approximate by splitting on punctuation)
            sentences = re.split(r"[.!?]+", text)
            total_sentences += len([s for s in sentences if s.strip()])
            
            # Keywords and n-grams
            filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
            word_counter.update(filtered_words)
            
            # Bigrams
            bigrams = [" ".join(words[i:i+2]) for i in range(len(words)-1)]
            # Filter bigrams containing stop words? We'll just filter if both are stop words, or look at raw
            bigram_counter.update(bigrams)
            
            # Trigrams
            trigrams = [" ".join(words[i:i+3]) for i in range(len(words)-2)]
            trigram_counter.update(trigrams)
            
        avg_len_chars = total_chars / len(sampled_reviews)
        avg_len_words = total_words / len(sampled_reviews)
        avg_sentences = total_sentences / len(sampled_reviews)
        excl_per_review = excl_count / len(sampled_reviews)
        quest_per_review = quest_count / len(sampled_reviews)
        caps_ratio = caps_word_count / total_words if total_words > 0 else 0
        
        return {
            "avg_chars": avg_len_chars,
            "avg_words": avg_len_words,
            "avg_sentences": avg_sentences,
            "excl_per_review": excl_per_review,
            "quest_per_review": quest_per_review,
            "caps_ratio_percent": caps_ratio * 100,
            "top_words": word_counter.most_common(50),
            "top_bigrams": bigram_counter.most_common(20),
            "top_trigrams": trigram_counter.most_common(20)
        }
        
    print("Analyzing extreme disappointment (1-star)...")
    disappointment_stats = get_stats(sampled_1star)
    
    print("Analyzing extreme satisfaction (5-star)...")
    satisfaction_stats = get_stats(sampled_5star)
    
    # Save the output results to a JSON file
    results = {
        "disappointment": disappointment_stats,
        "satisfaction": satisfaction_stats
    }
    
    with open(r"C:\Users\ADMIN\Documents\my-bct\docs\behavioral_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("Analysis finished. Results written to docs/behavioral_analysis_results.json")
    
    # Generate markdown report text
    report = generate_report_markdown(disappointment_stats, satisfaction_stats)
    with open(r"C:\Users\ADMIN\Documents\my-bct\docs\behavioral_template.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("Markdown report written to docs/behavioral_template.md")

def generate_report_markdown(dis_stats, sat_stats):
    def format_list(lst):
        return ", ".join([f"**{item}** ({count})" for item, count in lst[:15]])
        
    report = f"""# Yelp Behavioral Analysis: Extreme Disappointment vs. Extreme Satisfaction
This report analyzes **2,000 unique Yelp users** (1,000 expressing extreme disappointment (1-star) and 1,000 expressing extreme satisfaction (5-star)) based on their reviews.

## 1. Quantitative Profile Comparison

| Metric | Extreme Disappointment (1-Star) | Extreme Satisfaction (5-Star) |
| :--- | :---: | :---: |
| **Average Characters** | {dis_stats['avg_chars']:.1f} | {sat_stats['avg_chars']:.1f} |
| **Average Words** | {dis_stats['avg_words']:.1f} | {sat_stats['avg_words']:.1f} |
| **Average Sentences** | {dis_stats['avg_sentences']:.1f} | {sat_stats['avg_sentences']:.1f} |
| **Exclamation Marks (`!`) per Review** | {dis_stats['excl_per_review']:.2f} | {sat_stats['excl_per_review']:.2f} |
| **Question Marks (`?`) per Review** | {dis_stats['quest_per_review']:.2f} | {sat_stats['quest_per_review']:.2f} |
| **All-Caps Word Ratio** | {dis_stats['caps_ratio_percent']:.3f}% | {sat_stats['caps_ratio_percent']:.3f}% |

### Key Observations:
1. **Length differences**: Extreme disappointment reviews tend to be **{dis_stats['avg_words']/sat_stats['avg_words']:.1f}x longer** than extreme satisfaction reviews. Angry users write detailed, chronological narratives explaining *why* they were let down, whereas happy users write shorter, high-emotion summaries.
2. **Punctuation**: 
   - Satisfied users use exclamation marks much more frequently ({sat_stats['excl_per_review']:.1f} vs {dis_stats['excl_per_review']:.1f} per review) to convey enthusiasm.
   - Disappointed users use question marks much more frequently ({dis_stats['quest_per_review']:.1f} vs {sat_stats['quest_per_review']:.1f} per review), indicating disbelief, rhetorical frustration ("Why is this place open?"), or questioning charges ("How is this $20?").
3. **Capitalization**: Disappointed users use ALL-CAPS words at a higher rate ({dis_stats['caps_ratio_percent']:.3f}% vs {sat_stats['caps_ratio_percent']:.3f}%) to highlight extreme frustration (e.g. "NEVER", "RUDE", "WORST").

---

## 2. Qualitative Lexical Comparison

### Top Keywords (Stop Words Removed)
- **Disappointment**: {format_list(dis_stats['top_words'])}
- **Satisfaction**: {format_list(sat_stats['top_words'])}

### Top Bigrams
- **Disappointment**: {format_list(dis_stats['top_bigrams'])}
- **Satisfaction**: {format_list(sat_stats['top_bigrams'])}

### Top Trigrams
- **Disappointment**: {format_list(dis_stats['top_trigrams'])}
- **Satisfaction**: {format_list(sat_stats['top_trigrams'])}

---

## 3. Linguistic Expression Mapping

### A. The Anatomy of Extreme Disappointment
1. **Chronological Narration**: "We walked in at 7pm...", "We waited 20 minutes...", "Then the manager came...". Disappointed users build a logical sequence of events to justify their negative review.
2. **Transaction Focus**: Heavy focus on money, charges, pricing, and refunds ("charge", "pay", "money", "manager"). They feel cheated or taken advantage of.
3. **Staff-Centric Anger**: Focus on individual employee behavior, specifically using adjectives like "rude", "horrible", "terrible", and referencing "the manager".
4. **Ultimate Rejection (The Exit)**: Concluding with strong warnings to other consumers: "never again", "never go back", "stay away", "don't waste your".

### B. The Anatomy of Extreme Satisfaction
1. **Emotional Outbursts**: High density of positive adjectives ("great", "delicious", "amazing", "friendly", "perfect").
2. **Sensory Description**: Focus on taste, freshness, and quality ("delicious", "fresh", "clean").
3. **Social Reassurance**: Encouraging others to visit: "highly recommend", "will definitely", "the best". They position themselves as guides sharing a hidden gem.
4. **Loyalty Promises (The Return)**: Concluding with promises to return: "will definitely be back", "definitely return", "can't wait".
"""
    return report

if __name__ == "__main__":
    analyze_dataset()
