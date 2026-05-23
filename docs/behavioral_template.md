# Yelp Behavioral Analysis: Extreme Disappointment vs. Extreme Satisfaction
This report analyzes **2,000 unique Yelp users** (1,000 expressing extreme disappointment (1-star) and 1,000 expressing extreme satisfaction (5-star)) based on their reviews.

## 1. Quantitative Profile Comparison

| Metric | Extreme Disappointment (1-Star) | Extreme Satisfaction (5-Star) |
| :--- | :---: | :---: |
| **Average Characters** | 694.2 | 465.5 |
| **Average Words** | 133.2 | 86.9 |
| **Average Sentences** | 9.4 | 7.1 |
| **Exclamation Marks (`!`) per Review** | 1.15 | 1.76 |
| **Question Marks (`?`) per Review** | 0.37 | 0.08 |
| **All-Caps Word Ratio** | 0.685% | 0.449% |

### Key Observations:
1. **Length differences**: Extreme disappointment reviews tend to be **1.5x longer** than extreme satisfaction reviews. Angry users write detailed, chronological narratives explaining *why* they were let down, whereas happy users write shorter, high-emotion summaries.
2. **Punctuation**: 
   - Satisfied users use exclamation marks much more frequently (1.8 vs 1.2 per review) to convey enthusiasm.
   - Disappointed users use question marks much more frequently (0.4 vs 0.1 per review), indicating disbelief, rhetorical frustration ("Why is this place open?"), or questioning charges ("How is this $20?").
3. **Capitalization**: Disappointed users use ALL-CAPS words at a higher rate (0.685% vs 0.449%) to highlight extreme frustration (e.g. "NEVER", "RUDE", "WORST").

---

## 2. Qualitative Lexical Comparison

### Top Keywords (Stop Words Removed)
- **Disappointment**: **she** (570), **when** (515), **just** (444), **all** (426), **from** (405), **like** (390), **even** (361), **never** (349), **what** (339), **after** (336), **them** (329), **here** (326), **will** (320), **her** (320), **said** (314)
- **Satisfaction**: **great** (588), **very** (393), **all** (337), **here** (297), **can** (283), **just** (276), **best** (266), **from** (264), **their** (250), **will** (246), **like** (224), **also** (215), **love** (214), **amazing** (200), **delicious** (193)

### Top Bigrams
- **Disappointment**: **it was** (388), **of the** (375), **in the** (355), **i was** (352), **and i** (316), **don t** (293), **on the** (286), **to the** (279), **this place** (269), **didn t** (252), **and the** (247), **for a** (218), **for the** (214), **i had** (214), **we were** (210)
- **Satisfaction**: **and the** (278), **of the** (268), **this place** (248), **and i** (228), **in the** (223), **it was** (223), **it s** (218), **the best** (192), **on the** (172), **i was** (162), **for a** (159), **i ve** (151), **is a** (150), **if you** (150), **to the** (149)

### Top Trigrams
- **Disappointment**: **i don t** (86), **i had to** (66), **one of the** (58), **the food was** (57), **i didn t** (55), **this place is** (49), **didn t even** (48), **won t be** (46), **it was a** (43), **they don t** (43), **i will never** (39), **it would be** (39), **i was told** (38), **they didn t** (38), **and it was** (37)
- **Satisfaction**: **this place is** (56), **one of the** (48), **i can t** (47), **and it was** (41), **it s a** (40), **i don t** (39), **this is the** (39), **the food was** (37), **i had the** (35), **i ve been** (35), **i ve ever** (34), **i didn t** (34), **if you re** (33), **of the best** (33), **the food is** (32)

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
