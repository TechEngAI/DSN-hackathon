# 🇳🇬 NaijaSense AI Recommendation Agent

An LLM-powered recommendation and review-generation system that understands user taste, cultural context, and Nigerian language style.

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-6f42c1)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)
![License MIT](https://img.shields.io/badge/License-MIT-green)
![DSN x BCT Hackathon 3.0](https://img.shields.io/badge/DSN%20x%20BCT-Hackathon%203.0-red)

## Overview

NaijaSense AI is a FastAPI recommendation system built for the **DSN x BCT LLM Agent Challenge - Hackathon 3.0**. It solves two tasks: generating realistic reviews for unseen items from a user's history, and recommending personalized items using semantic search plus LLM reasoning. Unlike a generic recommender, Nigerian cultural intelligence is built into the core agent: Pidgin, local food references, rating behavior, and social cues shape the output. The system supports Yelp-style businesses and Amazon Beauty products in one ChromaDB index, so judges can test food, lifestyle, and cross-domain recommendations from a single API.

## Architecture

```text
User Request
     |
     v
FastAPI API Layer
     |
     v
Persona Builder ---------------> ChromaDB Semantic Search
     |                                      |
     |                                      v
     |                           Candidate Retrieval
     |                                      |
     v                                      v
Nigerian Context Layer --------> LLM Re-Ranker (Groq)
                                            |
                                            v
                              Ranked Response with Reasons
```

- **FastAPI API Layer**: exposes Task A, Task B, onboarding, health, and metrics endpoints on port `8080`.
- **Persona Builder**: converts user review history or onboarding answers into taste, tone, rating, loves, and pet-peeve signals.
- **ChromaDB Semantic Search**: indexes Yelp businesses and Amazon-style products together for fast candidate retrieval.
- **Nigerian Context Layer**: injects local language, Nigerian food culture, Detty December, owambe, and rating nuance into LLM prompts.
- **Groq LLM Re-Ranker**: uses `llama-3.3-70b-versatile` to generate reviews, rank candidates, and explain recommendations.
- **Ranked Response with Reasons**: every recommendation includes a human-readable reason, making the agent explainable.

## Key Features

- **Persona-driven review simulation**: Task A builds a behavioral profile from review history and generates realistic unseen-item reviews.
- **Nigerian cultural intelligence layer**: Pidgin phrases, local food references, owambe, Detty December, buka culture, and Nigerian rating generosity are first-class prompt signals.
- **Three response language modes**: choose `standard`, `naija`, or `pidgin` per request for controlled output style.
- **Cross-domain recommendations**: Yelp businesses and Amazon Beauty/lifestyle products are indexed into one ChromaDB collection.
- **Cold start onboarding**: new users answer lightweight questions that become a starter persona for immediate recommendations.
- **Multi-turn conversation support**: Task B can use conversation history to refine the current query and preserve user intent.
- **LLM re-ranking with reason fields**: semantic search retrieves candidates, then the LLM ranks and explains why each item fits.

## Quick Start — One Command

Run these setup commands once:

```bash
git clone https://github.com/TechEngAI/DSN-hackathon.git
cd DSN-hackathon/dsn-bct-hackathon
cp .env.example .env
```

Add your `GROQ_API_KEY` to `.env`, then start everything with one command:

```bash
docker-compose up --build
```

Sample Nigerian business data is included in `data/sample_data.json`, so judges can run the project immediately without downloading the full Yelp or Amazon datasets.

## Environment Setup

| Variable | Required | Example | Description |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | Yes | `gsk_your_key_here` | Groq API key used for LLM review generation and recommendation reasoning. |
| `USE_LOCAL_CHROMA` | Yes | `false` | Use `false` in Docker so the API connects to the `chromadb` service. Use `true` for local persistent Chroma development. |
| `CHROMA_HOST` | No | `chromadb` | ChromaDB host. Defaults to `chromadb` in Docker and falls back to `localhost` locally. |
| `CHROMA_PORT` | No | `8000` | ChromaDB HTTP port. |
| `CHROMA_PERSIST_PATH` | No | `./chroma` | Local Chroma persistence path when `USE_LOCAL_CHROMA=true`. |

Get a free Groq API key from [console.groq.com](https://console.groq.com/).

`.env.example`:

```env
GROQ_API_KEY=your_groq_api_key_here
USE_LOCAL_CHROMA=false
```

## API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check for the FastAPI service. |
| `POST` | `/task-a/generate-review` | Generates a realistic review for a user and unseen item. |
| `POST` | `/task-b/recommend` | Returns personalized recommendations with reasons. |
| `GET` | `/task-b/onboarding-questions` | Returns onboarding questions for cold-start users. |
| `POST` | `/task-b/cold-start-recommend` | Runs the cold-start recommendation pipeline from onboarding answers. |
| `GET` | `/task-b/metrics` | Returns precision, coverage, cold/warm parity, and latency metrics. |
| `POST` | `/task-b/metrics/precision` | Calculates Precision@K for a supplied recommendation list. |

### Health Check

```bash
curl http://localhost:8080/health
```

Response:

```json
{
  "status": "running",
  "version": "1.0"
}
```

### Task A: Generate Review

```bash
curl -X POST http://localhost:8080/task-a/generate-review \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001_naija_foodie",
    "item_id": "NGBIZZ0000000000000003",
    "persona": {},
    "language_mode": "naija"
  }'
```

Example response:

```json
{
  "rating": 4.5,
  "review_text": "Lagos Pepper Soup Joint really entered well. The pepper soup had that proper heat, the fish tasted fresh, and the whole thing felt like correct after-work comfort food. Small wait time, but no wahala, the taste was confirm.",
  "reasoning": "The user consistently rates Nigerian food generously, prefers spicy local meals, and uses warm Naija expressions. The review reflects their love for suya, buka food, and bold pepper."
}
```

### Task B: Recommend

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001_naija_foodie",
    "query": "spicy suya and local buka food",
    "top_k": 5,
    "is_cold_start": false,
    "language_mode": "naija"
  }'
```

Example response:

```json
{
  "recommendations": [
    {
      "id": "NGBIZZ0000000000000002",
      "item_id": "NGBIZZ0000000000000002",
      "name": "Eko Suya Spot",
      "reason": "Eko Suya Spot na confirm Suya spot in Lagos that matches your search for spicy suya and local buka food. No wahala, my guy, this one fit help you chop life."
    },
    {
      "id": "NGBIZZ0000000000000001",
      "item_id": "NGBIZZ0000000000000001",
      "name": "Mama Titi's Buka",
      "reason": "Mama Titi's Buka fits the user's love for local Nigerian food, generous portions, and buka-style comfort."
    }
  ],
  "reasoning_summary": "Top results selected from local businesses that match spicy Nigerian food preferences.",
  "validation": {
    "passed": true,
    "errors": [],
    "checked": {
      "ids_are_real_business_ids": true,
      "location": null,
      "min_similarity": 0.65,
      "reasoning_summary_profile_fields": ["avg_rating", "loves", "pet_peeves", "review_length", "sample_phrases", "tone", "top_topics"],
      "recommendations": []
    }
  },
  "enriched_query": "spicy food Nigerian buka suya"
}
```

### Cross-Domain Recommendation

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_003_abuja_critic",
    "query": "beauty products and good food",
    "top_k": 5,
    "is_cold_start": false,
    "language_mode": "naija"
  }'
```

Example response:

```json
{
  "recommendations": [
    {
      "id": "NGBIZZ0000000000000014",
      "item_id": "NGBIZZ0000000000000014",
      "name": "Glow Naija Shea Butter Kit",
      "reason": "Glow Naija Shea Butter Kit connects with the user's interest in quality beauty products while keeping the recommendation grounded in trusted, high-rated Nigerian lifestyle items."
    },
    {
      "id": "NGBIZZ0000000000000013",
      "item_id": "NGBIZZ0000000000000013",
      "name": "The Calabash Room",
      "reason": "The Calabash Room gives the good food side of the query with polished service, strong quality signals, and a calm Abuja dining experience."
    }
  ],
  "reasoning_summary": "The agent selected a mix of beauty/lifestyle products and strong food matches from the shared ChromaDB index.",
  "validation": {
    "passed": true,
    "errors": [],
    "checked": {
      "ids_are_real_business_ids": true,
      "location": null,
      "min_similarity": 0.65,
      "reasoning_summary_profile_fields": ["avg_rating", "loves", "pet_peeves", "review_length", "sample_phrases", "tone", "top_topics"],
      "recommendations": []
    }
  },
  "enriched_query": "beauty products good food"
}
```

### Language Modes

Standard English:

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_003_abuja_critic",
    "query": "healthy juice and clean restaurant",
    "top_k": 3,
    "is_cold_start": false,
    "language_mode": "standard"
  }'
```

Example reason:

```json
{
  "reason": "Abuja Green Juice Bar is a Juice Bars, Smoothies, Healthy Food, Cafe in Abuja that matches your search for healthy juice and clean restaurant."
}
```

Naija mix:

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_002_lagos_explorer",
    "query": "Lagos cafe and suya",
    "top_k": 3,
    "is_cold_start": false,
    "language_mode": "naija"
  }'
```

Example reason:

```json
{
  "reason": "Zobo & Chill Cafe na confirm Cafe spot in Lagos that matches your search for Lagos cafe and suya. No wahala, my guy, this one fit help you chop life."
}
```

Full Pidgin:

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_005_ibadan_local",
    "query": "plantain, palmwine and local chill spot",
    "top_k": 3,
    "is_cold_start": false,
    "language_mode": "pidgin"
  }'
```

Example reason:

```json
{
  "reason": "Dodo King Ibadan na confirm Fast Food spot for Ibadan wey match wetin you dey find for plantain, palmwine and local chill spot. My padi, e dey hit, abeg no dulling."
}
```

### Cold Start Flow

1. Get onboarding questions.

```bash
curl http://localhost:8080/task-b/onboarding-questions
```

2. Submit answers through `/task-b/recommend`.

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "brand_new_user_001",
    "query": "jollof rice and pepper soup in Abuja",
    "top_k": 5,
    "is_cold_start": true,
    "language_mode": "naija",
    "user_responses": {
      "1": "jollof rice and pepper soup",
      "2": "sit-down restaurants",
      "3": "medium budget",
      "4": "try new things",
      "5": "Abuja"
    }
  }'
```

3. Expected behavior: the API builds a starter persona and returns relevant Abuja matches such as `Abuja Jollof Republic`, `The Calabash Room`, or `Abuja Green Juice Bar`.

Dedicated cold-start endpoint:

```bash
curl -X POST http://localhost:8080/task-b/cold-start-recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "brand_new_user_001",
    "answers": {
      "1": "jollof rice and pepper soup",
      "2": "sit-down restaurants",
      "3": "medium budget",
      "4": "try new things",
      "5": "Abuja"
    }
  }'
```

Example response:

```json
{
  "recommendations": [
    {
      "id": "NGBIZZ0000000000000004",
      "item_id": "NGBIZZ0000000000000004",
      "name": "Abuja Jollof Republic",
      "reason": "Abuja Jollof Republic is a strong match for jollof rice, Abuja location, and sit-down Nigerian dining."
    }
  ],
  "reasoning_summary": "Top results selected from onboarding preferences for Abuja, jollof rice, and pepper soup.",
  "validation": {
    "passed": true,
    "errors": [],
    "checked": {
      "ids_are_real_business_ids": true,
      "location": "Abuja",
      "min_similarity": 0.65,
      "reasoning_summary_profile_fields": ["budget", "cuisine", "dining_style", "location", "loves", "openness", "pet_peeves", "preferred_food", "review_length", "sample_phrases", "tone", "top_topics"],
      "recommendations": []
    }
  },
  "enriched_query": "jollof rice pepper soup sit-down restaurants Abuja"
}
```

### Multi-Turn Conversation Example

```bash
curl -X POST http://localhost:8080/task-b/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_002_lagos_explorer",
    "query": "make it more premium but still Lagos",
    "top_k": 5,
    "is_cold_start": false,
    "language_mode": "naija",
    "conversation_history": [
      {
        "role": "user",
        "content": "I want suya or cafe spots for a Friday evening."
      },
      {
        "role": "assistant",
        "content": "You may like Eko Suya Spot and Zobo & Chill Cafe."
      }
    ]
  }'
```

Expected behavior: the query enrichment step preserves the previous suya/cafe preference while shifting the ranking toward premium Lagos options such as `Skyline Ikoyi Dining`.

### Metrics

```bash
curl http://localhost:8080/task-b/metrics
```

Example response:

```json
{
  "precision_at_k": 0.6,
  "coverage": {
    "coverage": 0.0032,
    "recommended_items": 22,
    "total_items": 6800
  },
  "cold_start_vs_warm": {
    "warm_avg_similarity": 0.7934,
    "cold_avg_similarity": 0.7923,
    "quality_gap": 0.0011
  },
  "latency": {
    "recommend": {
      "min_ms": 36,
      "avg_ms": 184,
      "max_ms": 912
    }
  },
  "generated_at": "2026-05-23T00:00:00Z"
}
```

```bash
curl -X POST http://localhost:8080/task-b/metrics/precision \
  -H "Content-Type: application/json" \
  -d '{
    "query": "burgers",
    "recommendations": [
      {
        "id": "NGBIZZ0000000000000007",
        "item_id": "NGBIZZ0000000000000007",
        "name": "Burger Express Abuja",
        "category": "Fast Food",
        "similarity_score": 0.79,
        "reason": "Strong burger and fast food match."
      }
    ]
  }'
```

Example response:

```json
{
  "precision_at_k": 1.0,
  "k": 1,
  "relevant_count": 1,
  "query": "burgers",
  "expected_categories": ["Burgers", "American", "Fast Food"]
}
```

## Metrics & Performance

| Metric | Result | Verdict |
| --- | ---: | --- |
| Precision@K | `0.60` | Strong relevance signal for retrieved recommendations. |
| Coverage | `0.0032` (`22/6800` at test scale) | Focused, high-confidence coverage during evaluation. |
| Warm avg similarity | `0.7934` | Personalized recommendations are semantically strong for known users. |
| Cold avg similarity | `0.7923` | Cold-start onboarding performs nearly as well as warm-start history. |
| Quality gap | `0.0011` | Near-perfect parity between cold and warm starts. |
| Minimum latency | `36ms` | Fast retrieval path for low-latency recommendation responses. |
| Amazon products loaded | `2000` | Cross-domain product recommendation support is active. |

- **Precision@K** measures how many returned recommendations match the user's query intent.
- **Coverage** measures how much of the indexed catalog has been recommended during test sessions.
- **Warm avg similarity** measures semantic match quality for users with review history.
- **Cold avg similarity** measures semantic match quality for new users with onboarding answers.
- **Quality gap** is the difference between warm and cold quality. A `0.0011` gap shows the cold-start agent reaches almost the same relevance level as history-based personalization.
- **Latency** captures API response time for recommendation calls.

## Dataset

| Dataset | Usage | Scale |
| --- | --- | ---: |
| Yelp Academic Dataset | Business metadata, review history, user preference extraction, semantic business search. | `5000` businesses, `50000` reviews |
| Amazon All Beauty | Beauty/lifestyle product metadata indexed into the same recommendation space. | `2000` products |
| Included Nigerian sample data | Immediate judge testing without large downloads. | `15` businesses/products, `30` reviews, `10` scenarios |


## 🚀 Live Demo
**API Docs:** https://dsn-hackathon-production.up.railway.app/docs

**Health Check:** https://dsn-hackathon-production.up.railway.app/health

The app automatically loads full Yelp files when they exist:

```text
data/yelp_academic_dataset_business.json
data/yelp_academic_dataset_review.json
```

Amazon data can be added with:

```text
data/meta_All_Beauty.jsonl
data/All_Beauty.jsonl
```

If the full Yelp files are missing, startup falls back to:

```text
data/sample_data.json
```

This makes the repository reproducible for judges while still supporting production-scale datasets.

## Nigerian Cultural Intelligence

The Nigerian context layer is not decoration. It changes how the agent interprets reviews, builds personas, and explains recommendations. Nigerian reviewers often rate generously while still embedding complaints inside polite language, so the system looks beyond star ratings and extracts pet peeves from the text itself.

| Mode | Example Output |
| --- | --- |
| `standard` | `Abuja Green Juice Bar is a clean, health-focused cafe that matches your preference for fresh drinks and reliable service.` |
| `naija` | `Abuja Green Juice Bar na confirm spot for fresh drinks. No wahala, my guy, the ginger blend fit give you that morning energy.` |
| `pidgin` | `Abuja Green Juice Bar na correct place if you want fresh juice wey dey hit. My padi, abeg no dulling, this one make sense.` |

Why it matters for this competition:

- It demonstrates culturally aware LLM prompting instead of generic English output.
- It makes recommendations feel local, useful, and emotionally natural for Nigerian users.
- It improves persona extraction by recognizing Nigerian slang, food references, and rating behavior.
- It directly addresses the bonus requirement for Nigerian cultural contextualization.

Cultural references implemented:

- Pidgin phrases: `e sweet die`, `e dey hit`, `abeg`, `no dulling`, `my guy`, `padi`, `no wahala`, `confirm`.
- Food and drink: suya, jollof rice, pepper soup, amala, ewedu, dodo, puff puff, zobo, palmwine.
- Social context: owambe, after-church meals, Detty December, Lagos Island vs Mainland, traffic-aware dining.
- Rating nuance: generous Nigerian ratings with subtle complaints captured from review text.
- Local business formats: buka joints, suya spots, juice bars, fine dining, and lifestyle products.

## Project Structure

```text
dsn-bct-hackathon/
├── app/
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── comparison.py
│   │   ├── coverage.py
│   │   ├── latency.py
│   │   ├── precision.py
│   │   └── router.py
│   ├── __init__.py
│   ├── amazon_indexer.py
│   ├── amazon_loader.py
│   ├── chromadb_client.py
│   ├── cold_start.py
│   ├── coverage_store.json
│   ├── data_loader.py
│   ├── formatter.py
│   ├── indexer.py
│   ├── language_config.py
│   ├── llm_client.py
│   ├── main.py
│   ├── recommendation_log.json
│   ├── startup.py
│   ├── task_a.py
│   ├── task_b.py
│   └── user_history.py
├── chroma/
│   └── local ChromaDB persistence files
├── data/
│   ├── sample_data.json
│   └── sample_data_readme.md
├── evaluation/
│   ├── generate_samples.py
│   ├── metrics_results.csv
│   ├── task_a_samples.json
│   └── task_b_samples.json
├── scripts/
│   ├── run_startup.py
│   └── test_precision.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md
└── requirements.txt
```

| File | Description |
| --- | --- |
| `app/main.py` | FastAPI application entrypoint and router registration. |
| `app/startup.py` | Loads data, initializes Groq, ChromaDB, user history, indexing, and fallback sample data. |
| `app/task_a.py` | Task A persona extraction and review generation endpoint. |
| `app/task_b.py` | Task B recommendation, cold-start, conversation, validation, and metrics wiring. |
| `app/language_config.py` | Shared language-mode instructions for `standard`, `naija`, and `pidgin`. |
| `app/chromadb_client.py` | ChromaDB HTTP/local client wrapper, indexing helpers, and semantic search. |
| `app/indexer.py` | Converts business records into searchable ChromaDB documents. |
| `app/amazon_loader.py` | Loads Amazon Beauty metadata and review records. |
| `app/amazon_indexer.py` | Indexes Amazon product records into the shared vector store. |
| `app/cold_start.py` | Provides onboarding question and starter recommendation support. |
| `app/coverage_store.json` | Stores lightweight coverage state for metric reporting during evaluation. |
| `app/data_loader.py` | Loads Yelp JSONL data and included `sample_data.json`. |
| `app/user_history.py` | Builds user-level review history and category summaries. |
| `app/llm_client.py` | Groq LLM client wrapper. |
| `app/metrics/*.py` | Precision, coverage, latency, and cold-vs-warm evaluation utilities. |
| `app/recommendation_log.json` | Stores recommendation session logs used for warm-vs-cold comparison metrics. |
| `chroma/` | Local ChromaDB persistence folder for non-Docker development. |
| `data/sample_data.json` | Nigerian judge-ready sample data with businesses, reviews, and scenarios. |
| `data/sample_data_readme.md` | Short guide for using the sample dataset. |
| `evaluation/generate_samples.py` | Evaluation sample generation script. |
| `scripts/test_precision.py` | Precision testing utility. |
| `Dockerfile` | Production-oriented API image with ChromaDB readiness wait. |
| `docker-compose.yml` | API + ChromaDB orchestration with persistent Chroma volume and health checks. |
| `requirements.txt` | Python dependencies. |

## Team

| Name | Role | Responsibilities |
| --- | --- | --- |
| Abdulhammed Muh-Awwal | Backend Infrastructure Lead | FastAPI architecture, ChromaDB integration, Docker setup, startup pipeline, API reliability. |
| Olanrewaju Muiz | AI Prompt Engineering Lead | Task A and Task B prompting, LLM reasoning design, Nigerian context layer, language modes. |
| JahsFavour Omoluabi | Data & Research Lead | EDA, persona extraction research, sample evaluation, solution paper, dataset strategy. |

## Submission Checklist

- [x] Task A review-generation agent implemented.
- [x] Task B recommendation agent implemented.
- [x] Persona extraction from user review history.
- [x] ChromaDB semantic search integrated.
- [x] Groq LLM generation and ranking integrated.
- [x] Nigerian cultural context layer implemented.
- [x] `standard`, `naija`, and `pidgin` language modes implemented.
- [x] Cold-start onboarding flow implemented.
- [x] Multi-turn conversation support implemented.
- [x] Cross-domain Yelp + Amazon indexing implemented.
- [x] Metrics endpoints implemented.
- [x] Dockerfile and docker-compose setup included.
- [x] ChromaDB Docker health check and persistent volume included.
- [x] Judge-ready sample dataset included.
- [x] Reproducible quick-start instructions included.
- [x] MIT license declared.

## License

Copyright (c) 2026 NaijaSense AI Team — Abdulhammed Muh-Awwal, Olanrewaju Muiz, JahsFavour Omoluabi

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
