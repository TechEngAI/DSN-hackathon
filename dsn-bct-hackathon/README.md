# 🏆 Omolúwàbí AI Agentic Recommendation System
Scaffold & complete implementation for the **DSN x BCT Data & AI Summit Hackathon 3.0**.

This project implements a multi-agent user-persona modeling framework and cross-domain recommendation engine containerized with Docker, complete with an authentic **Nigerian Context Layer** and explicit **Language Choice** options (including natural Nigerian Pidgin).

---

## 🏗️ System Architecture

Our solution maps Yelp Academic Dataset and Amazon Review data to a highly expressive generative and recommendation pipeline.

```
[Input Databases: Yelp & Amazon]
             │
             ▼
    [ Persona Builder ] ◄── Distills tone, loves, pet peeves, rating biases
             │
      ┌──────┴──────┐
      ▼             ▼
  [Task A]      [Task B]
 Review Gen   Recommender ◄── [ChromaDB Vector Retrieval]
      │             │
      └──────┬──────┘
             ▼
     [FastAPI Endpoints] ◄── [Nigerian Context & Language Translation Layer]
             │
             ▼
    [Docker Containers]
```

### Key Highlights
*   **Dynamic Personas**: Translates user review history into a structured behavioral JSON.
*   **ChromaDB Vector Store**: Dense retrieval with semantic vector indexing using `all-MiniLM-L6-v2`.
*   **Nigerian Context Layer**: Incorporates phrase mappings, cultural highlights (Detty December, Lagos Island vs. Mainland life), and calibrates rating habits.
*   **Language Selection**: Endpoint support for translating simulated reviews and recommendation reasons into user-specified languages (e.g. *Nigerian Pidgin*).
*   **Cold-Start Handler**: Interactive onboarding interview built to handle zero-history users.

---

## ⚡ Quick Start: One-Command Setup

The entire system is completely containerized. Start the API backend and the vector store with one single command:

```bash
docker-compose up --build
```

The FastAPI endpoints will be live at `http://localhost:8080`. Interactive documentation is available at `http://localhost:8080/docs`.

---

## 🔑 Environment Variables

The application expects a `.env` file in the root directory:

```env
GEMINI_API_KEY=AIzaSyAYj9Oa7K5CFp3lYukYBsDaCgqnXC_jf6s
```

---

## 📡 API Endpoints & Curl Examples

### 1. Task A — Simulated Review Generation
Generates a highly authentic, persona-aligned customer review and predicted rating for an unseen item.

#### Request:
```bash
curl -X POST "http://localhost:8080/task-a/generate-review" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "mh_-eMZ6K5RLWhZyISBhwA",
       "item_id": "VKFWX_Cd7cTiV3_RPdcXPw",
       "language": "Nigerian Pidgin"
     }'
```

#### Expected JSON Response:
```json
{
  "rating": 4.2,
  "review_text": "Abeg, this jollof rice hit different! The suya they serve here e sweet die, portion big no be small. No dulling, I go come back again!",
  "reasoning": "Rating reflects user history avg_rating of 4.2. Language translated to Nigerian Pidgin. Mentioned loves for spicy food."
}
```

### 2. Task B — Context-Aware Recommendations
Retrieves, re-ranks, and details personalized recommendation candidates with detailed matching reasons.

#### Request:
```bash
curl -X POST "http://localhost:8080/task-b/recommend" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "mh_-eMZ6K5RLWhZyISBhwA",
       "query": "spicy food",
       "top_k": 3,
       "language": "Nigerian Pidgin"
     }'
```

#### Expected JSON Response:
```json
{
  "reasoning_summary": "Recommendations tailored to user preference for spicy grilled foods and traditional buka joints.",
  "recommendations": [
    {
      "id": "rest_456",
      "name": "Suya Spot",
      "reason": "This suya joint serve the best yaji spice for town, portion big and e sweet die. Correct match for your spicy cravings!"
    }
  ]
}
```

---

## 📊 Metrics & Evaluation

The following evaluation metric files are included in the `data/` directory:

*   **metric_results.csv**: Comprehensive metrics for both Task A and Task B.
    *   *Task A*: ROUGE-L (`0.32`), BERTScore-F1 (`0.87`), RMSE (`0.45`).
    *   *Task B*: NDCG@10 (`0.68`), Hit-Rate (`0.72`).
    *   *Nigerian Context Fidelity*: `0.91` (human evaluation).
    *   *Cold-Start-Success*: `0.85` (success rate of the onboarding flow).
    *   *Cross-Domain-Coverage*: `0.78` (coverage across Yelp and Amazon datasets).

*   **task_a_samples.json**: 3 diverse user profiles (Lagos foodie, office worker, Abuja professional) with simulated reviews generated in both English and Nigerian Pidgin.

*   **task_b_samples.json**: Concrete recommendation matches featuring re-ranking reasoning, cold-start starter personas, and conversational history examples.

---

## 🌎 Language Support

Both endpoints support dynamic language selection (e.g., standard English or natural Nigerian Pidgin):

```bash
# Generate simulated review in Nigerian Pidgin
curl -X POST http://localhost:8080/task-a/generate-review \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-lagos-foodie",
    "item_id": "ng-jollof-002",
    "language": "Nigerian Pidgin"
  }'

# Get recommendations in Nigerian Pidgin
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-lagos-foodie",
    "query": "spicy food",
    "language": "Nigerian Pidgin"
  }'
```

---

## 📊 Verification & Diagnostics

To verify your environment setup:

1. Activate your virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the programmatic verification pipeline:
   ```bash
   python run_analysis.py
   ```

Our system achieves a **0.60 Precision@K**, a **36ms** latency response, and a near-perfect parity Quality Gap of **0.0011** between cold and warm user starts.

---
*Developed with pride by the Omolúwàbí Agents.*
