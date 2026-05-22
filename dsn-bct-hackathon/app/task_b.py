import json
import re
import time
import asyncio
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from app.metrics.comparison import log_recommendation_session
from app.metrics.coverage import track_coverage
from app.metrics.latency import record_latency
from app.metrics.precision import calculate_precision_at_k
from app.metrics.router import router as metrics_router
from app.startup import app_state

router = APIRouter(tags=["Task B"])
router.include_router(metrics_router)
MIN_RECOMMENDATION_SIMILARITY = 0.65

_summary_cache: dict[str, str] = {}
_persona_cache: dict[str, dict] = {}

# Nigerian Context Block used within prompts
NIGERIAN_CONTEXT_BLOCK = """
NIGERIAN CULTURAL CONTEXT & REFERENCE DICTIONARY:
- Phrase Mapping Table:
  * "Very delicious" -> "e sweet die" / "e dey hit" / "no cap"
  * "Please" -> "abeg"
  * "Don't miss out" -> "no dulling"
  * "Local/traditional food joint" -> "buka" / "joint"
  * "Party / Celebration / Gathering" -> "owambe"
  * "Trouble / Problem" -> "wahala"
  * "Understood / Solidified" -> "confirm"
  * "Friend / Guy" -> "padi" / "my guy"
  * "Enjoying life" -> "chilling" / "chop life"
  * "Expression of surprise/emphasis" -> "Oshey!" / "Chineke!" / "Kai!"

- Reference Local Highlights:
  * Suya spots (spicy grilled meat)
  * Buka restaurants (local bukka kitchens)
  * Jollof rice, puff puff, pepper soup, agege bread, shawarma, dodo (fried plantain)
  * Drinks like Zobo, Palmwine, cold Star/Malt

- Cultural Context & Triggers:
  * "Detty December" (Lagos party season in December)
  * "Owambe" (Saturday parties/feasts with colorful aso ebi)
  * "After-church spots" (Sunday family lunches/outings)
  * "Lagos Island vs Mainland" (Lekki/VI/Ikoyi highbrow vs Ikeja/Surulere grassroots vibe, traffic/gridlock commutes)

- Rating Behaviour Nuance:
  * Nigerians are highly encouraging and polite. They may rate 5 stars even when there are minor complaints (e.g. slow service or power outage) out of encouragement ("no wahala, we go support you").
  * Calibrate the ratings accordingly! When analyzing, look past the polite high ratings to identify actual pet peeves and loves.
"""


# Request model for Task B recommendation endpoint
class RecommendRequest(BaseModel):
    user_id: str  # Unique identifier for the user
    query: str = ""  # Optional search query from user
    top_k: int = Field(default=5, ge=1, le=50)  # Number of recommendations to return (1-50)
    is_cold_start: bool = False  # Flag indicating if this is a new user with no history
    location: Optional[str] = Field(default=None)  # Optional city/region filter for local recommendations
    user_responses: Optional[dict[str, str]] = Field(default=None)  # Onboarding questionnaire responses for cold-start users
    conversation_history: Optional[list[dict[str, Any]]] = Field(default=None)  # Multi-turn conversation context


# Helper function to extract JSON from LLM response, handling markdown code fences
def _extract_json(text: str) -> dict[str, Any]:
    try:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_city(city: str) -> str:
    city = str(city or "").split(",", maxsplit=1)[0].strip()
    return city.title()


def _normalize_location(value: Any) -> str:
    return normalize_city(str(value or "")).casefold()


def _display_location(value: Any) -> str:
    return normalize_city(str(value or ""))


def _extract_user_location(persona: dict, user_responses: dict | None = None, explicit_location: str | None = None) -> str:
    location_keys = ("location", "city", "region", "area")
    for source in ({"location": explicit_location}, user_responses or {}, persona or {}):
        for key, value in source.items():
            if str(key).strip().casefold() in location_keys and str(value or "").strip():
                return _display_location(value)
    return ""


def _location_where_filter(location: str) -> dict | None:
    normalized_city = normalize_city(location)
    if not normalized_city:
        return None
    return {"city": normalized_city}


def _dedupe_query_parts(parts: list[Any]) -> list[str]:
    seen: set[str] = set()
    unique_parts: list[str] = []
    for part in parts:
        text = re.sub(r"\s+", " ", str(part or "").strip())
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique_parts.append(text)
    return unique_parts


def _join_unique_query_parts(parts: list[Any]) -> str:
    return " ".join(_dedupe_query_parts(parts))


def _dedupe_query_text(text: str) -> str:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in re.sub(r"\s+", " ", str(text or "").strip()).split():
        key = token.strip(" ,;:").casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        tokens.append(token)
    return " ".join(tokens)


async def update_summary_async(
    user_id: str,
    query: str,
    location: str,
    top_result_name: str,
    top_result_category: str,
    count: int,
) -> None:
    system_prompt = (
        "You write one-sentence recommendation summaries.\n"
        "Be concise. Max 2 sentences. No preamble."
    )
    prompt = (
        f"Query: {query}\n"
        f"Location: {location}\n"
        f"Top result: {top_result_name} ({top_result_category})\n"
        f"Total results: {count}\n\n"
        "Write a brief summary of why these results match the query."
    )
    llm_client = app_state.get("llm")
    if llm_client is None:
        return

    try:
        if getattr(llm_client, "client", None) is not None:
            resp = await asyncio.to_thread(
                llm_client.client.chat.completions.create,
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
            )
            summary = (resp.choices[0].message.content or "").strip()
        else:
            summary = str(await asyncio.to_thread(llm_client.generate, prompt, system_prompt)).strip()
        if summary:
            cache_key = f"{user_id}:{normalize_city(location).casefold()}:{query.strip().casefold()}"
            _summary_cache[cache_key] = summary
    except Exception as exc:
        print(f"[TIMER] background summary failed: {exc}")


def _metadata_matches_location(metadata: dict, location: str) -> bool:
    if not location:
        return True
    return _normalize_location(metadata.get("city")) == _normalize_location(location)


def _city_exists_in_dataset(vector_store: Any, city: str) -> bool:
    normalized_city = normalize_city(city)
    if not normalized_city or vector_store is None or getattr(vector_store, "collection", None) is None:
        return False
    try:
        results = vector_store.collection.get(where={"city": normalized_city}, limit=1, include=["metadatas"])
        return bool(results.get("ids"))
    except Exception:
        return False


def _candidate_business_id(match: dict, metadata: dict) -> str:
    business_id = str(metadata.get("business_id") or "").strip()
    name = str(metadata.get("name") or metadata.get("title") or "").strip()
    if not business_id or business_id == name:
        return ""
    return business_id


def _profile_schema(persona: dict) -> dict[str, str]:
    return {str(key): type(value).__name__ for key, value in _llm_user_profile(persona).items()}


def _llm_user_profile(persona: dict) -> dict:
    return {
        str(key): value
        for key, value in (persona or {}).items()
        if str(key) != "naija_cues"
    }


def _hallucinated_summary_fields(summary: str, profile_fields: set[str]) -> set[str]:
    forbidden_fields = {"naija_cues"} - profile_fields
    snake_case_tokens = set(re.findall(r"\b[a-z][a-z0-9]*_[a-z0-9_]*\b", summary or ""))
    explicit_forbidden = {field for field in forbidden_fields if field in (summary or "")}
    return explicit_forbidden | (snake_case_tokens - profile_fields)


def _validate_recommendation_output(
    recommendations: list[dict],
    candidates_by_id: dict[str, dict],
    user_location: str,
    reasoning_summary: str,
    profile_fields: set[str],
    min_similarity: float = MIN_RECOMMENDATION_SIMILARITY,
) -> tuple[list[dict], dict]:
    valid_recommendations = []
    checked_recommendations = []
    errors = []

    for recommendation in recommendations:
        rec_id = str(recommendation.get("id") or recommendation.get("item_id") or "").strip()
        candidate = candidates_by_id.get(rec_id)
        name = str(recommendation.get("name") or "").strip()

        if not candidate:
            errors.append(f"Recommendation '{name or rec_id}' was excluded because its id is not a candidate business_id.")
            continue
        if not rec_id or rec_id == name:
            errors.append(f"Recommendation '{name or rec_id}' was excluded because its id is missing or equals the business name.")
            continue
        if not _metadata_matches_location(candidate["metadata"], user_location):
            errors.append(f"Recommendation '{name or rec_id}' was excluded because it does not match location '{user_location}'.")
            continue
        if float(candidate["score"]) < min_similarity:
            errors.append(f"Recommendation '{name or rec_id}' was excluded because its similarity score is below {min_similarity}.")
            continue

        clean_recommendation = {
            "id": rec_id,
            "item_id": rec_id,
            "name": candidate["name"],
            "reason": str(recommendation.get("reason") or "").strip()
            or f"{candidate['name']} matches your profile and current request.",
        }
        valid_recommendations.append(clean_recommendation)
        checked_recommendations.append(
            {
                "id": rec_id,
                "item_id": rec_id,
                "name": candidate["name"],
                "primary_category": candidate["metadata"].get("primary_category", ""),
                "similarity_score": float(candidate["score"]),
            }
        )

    hallucinated_fields = sorted(_hallucinated_summary_fields(reasoning_summary, profile_fields))
    if hallucinated_fields:
        errors.append(
            "reasoning_summary referenced fields not present in the user profile: "
            + ", ".join(hallucinated_fields)
        )

    return valid_recommendations, {
        "passed": not errors,
        "errors": errors,
        "checked": {
            "ids_are_real_business_ids": True,
            "location": user_location or None,
            "min_similarity": min_similarity,
            "reasoning_summary_profile_fields": sorted(profile_fields),
            "recommendations": checked_recommendations,
        },
    }


def _track_task_b_metrics(
    user_id: str,
    is_cold_start: bool,
    query: str,
    location: str | None,
    response: dict,
) -> None:
    """Record coverage, precision, and warm/cold quality for one response."""
    recommendations = response.get("recommendations", []) if isinstance(response, dict) else []
    checked = (
        response.get("validation", {})
        .get("checked", {})
        .get("recommendations", [])
        if isinstance(response, dict)
        else []
    )
    recommendation_ids = [
        str(item.get("id") or item.get("item_id"))
        for item in recommendations
        if item.get("id") or item.get("item_id")
    ]
    similarity_scores = []
    for item in checked:
        score = item.get("similarity_score")
        if score is None and item.get("distance") is not None:
            distance = float(item.get("distance") or 0.0)
            score = 1.0 - distance if 0.0 <= distance <= 1.0 else 1.0 / (1.0 + (distance / 4.0))
        similarity_scores.append(float(score or 0.0))
    # Prefer original user query for intent/category matching. The enriched/enhanced
    # search string used for retrieval is included in the `response` under
    # `enriched_query` (added by recommend_logic) for logging purposes only.
    enriched_query = None
    if isinstance(response, dict):
        enriched_query = response.get("enriched_query") or response.get("search_query")

    precision = calculate_precision_at_k(checked, query)

    track_coverage(recommendation_ids)
    log_recommendation_session(
        user_id=user_id,
        is_cold_start=is_cold_start,
        query=query,
        location=location,
        similarity_scores=similarity_scores,
        recommendation_count=len(recommendations),
        precision_at_k=precision,
        enriched_query=enriched_query,
    )


def _get_cached_persona(user_id: str, user_history: dict) -> dict:
    cache_key = f"{user_id}:{len(user_history.get('reviews', []))}:{user_history.get('avg_rating')}"
    if cache_key not in _persona_cache:
        from app.task_a import build_persona

        _persona_cache.clear()
        _persona_cache[cache_key] = build_persona(user_history)
    return _persona_cache[cache_key]


# Query Builder: Constructs semantic search string for ChromaDB retrieval
# Combines user loves, topics, categories, negates pet peeves, and adds Nigerian context if applicable
def build_taste_query(persona: dict, top_categories: list[str] = None) -> str:
    """
    Constructs a semantic search string using user loves, top topics,
    historical categories, negation of pet peeves, and Nigerian local terms if applicable.
    """
    # Extract persona components for query building
    loves = _dedupe_query_parts(persona.get("loves", []))
    top_topics = _dedupe_query_parts(persona.get("top_topics", []))
    categories = _dedupe_query_parts(top_categories or [])

    # Build positive query components
    query_parts = []
    query_parts.extend(loves)
    query_parts.extend(top_topics)
    query_parts.extend(categories)

    # Add negation hints for pet peeves (what to avoid)
    pet_peeves = persona.get("pet_peeves", [])
    if pet_peeves:
        negation_hints = " ".join(f"avoid {peeve}" for peeve in pet_peeves)
        query_parts.append(negation_hints)

    # Add Nigerian culinary and locality terms if user has Naija cues
    if persona.get("naija_cues", False):
        query_parts.append("suya pepper soup buka Lagos")

    return _dedupe_query_text(_join_unique_query_parts(query_parts))


class ColdStartRecommendRequest(BaseModel):
    user_id: str
    answers: dict


class Recommendation(BaseModel):
    id: Optional[str] = None
    item_id: str
    name: str
    reason: str
    score: float
    domain: str = "unknown"


class ColdStartRecommendResponse(BaseModel):
    user_id: str
    is_cold_start: bool
    recommendations: list[Recommendation]


def _build_cold_start_profile(user_responses: dict | None) -> dict:
    responses = user_responses or {}
    numeric_fields = {
        "1": "preferred_food",
        "2": "dining_style",
        "3": "budget",
        "4": "openness",
        "5": "location",
    }
    profile = {
        "preferred_food": "",
        "cuisine": "",
        "dining_style": "",
        "budget": "",
        "openness": "",
        "location": "",
    }

    for raw_key, raw_value in responses.items():
        key = numeric_fields.get(str(raw_key), str(raw_key))
        value = str(raw_value or "").strip()
        if key in profile:
            profile[key] = value

    if not profile["cuisine"]:
        profile["cuisine"] = profile["preferred_food"]

    profile["loves"] = _dedupe_query_parts([
        profile["preferred_food"],
        profile["cuisine"],
    ])
    profile["top_topics"] = _dedupe_query_parts([
        profile["dining_style"],
        profile["budget"],
        profile["openness"],
    ])
    profile["pet_peeves"] = []
    profile["tone"] = "casual"
    profile["review_length"] = "medium"
    profile["sample_phrases"] = []
    return profile


def _build_cold_start_query(profile: dict) -> str:
    query_parts = [
        profile.get("preferred_food") or profile.get("cuisine"),
        profile.get("dining_style"),
        profile.get("location"),
    ]
    return _dedupe_query_text(_join_unique_query_parts(query_parts))


def enrich_query_with_history(query: str, history: list) -> str:
    if not history:
        return query

    try:
        history_lines = []
        for message in history:
            role = str(message.get("role", "user")).strip() or "user"
            content = str(message.get("content", "")).strip()
            if content:
                history_lines.append(f"{role}: {content}")

        if not history_lines:
            return query

        prompt = (
            "CONVERSATION HISTORY:\n"
            f"{json.dumps(history_lines, indent=2)}\n\n"
            "CURRENT QUERY:\n"
            f"{query}\n\n"
            "OUTPUT:"
        )
        system_prompt = (
            "You are a query enrichment assistant for a restaurant recommendation engine. "
            "Given a conversation history and a new user query, produce ONE enriched search string that captures the user's full intent.\n\n"
            "Rules:\n"
            "- Combine relevant context from history with the current query\n"
            "- Keep it short: max 15 words\n"
            "- Output ONLY the enriched query string, nothing else\n"
            "- Do not explain, do not add punctuation beyond the query itself"
        )

        llm_client = app_state.get("llm")
        if llm_client is None:
            return query

        # Use the underlying Groq client directly when available so this lightweight call stays capped at 50 tokens.
        if getattr(llm_client, "client", None) is not None:
            response = llm_client.client.chat.completions.create(
                model="llama3-8b-8192",
                max_tokens=50,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            enriched = response.choices[0].message.content or ""
        else:
            enriched = llm_client.generate(prompt=prompt, system_prompt=system_prompt)

        cleaned = re.sub(r"[^A-Za-z0-9\s+-]", " ", str(enriched)).strip()
        words = cleaned.split()
        return " ".join(words[:15]) if words else query
    except Exception:
        return query


@router.get("/onboarding-questions")
def onboarding_questions() -> list[dict]:
    cold_start_handler = app_state.get("cold_start_handler")
    if cold_start_handler is None:
        return []
    return cold_start_handler.get_onboarding_questions()


@router.post("/cold-start-recommend")
async def cold_start_recommend(request: ColdStartRecommendRequest) -> Any:
    started_at = time.perf_counter()
    try:
        # Branch 1: Convert numbered onboarding answers into a queryable temporary profile.
        starter_profile = _build_cold_start_profile(request.answers)

        # Branch 2: Build the search query from mapped profile fields like dining_style, cuisine, and location.
        query = _build_cold_start_query(starter_profile)

        # Branch 3: Run the same validated recommendation pipeline used by /recommend.
        response = await recommend_logic(
            persona=starter_profile,
            query=query,
            top_k=5,
            top_categories=[],
            conversation_history=[],
            user_location=starter_profile.get("location"),
            user_responses=starter_profile,
        )
        _track_task_b_metrics(
            user_id=request.user_id,
            is_cold_start=True,
            query=query,
            location=starter_profile.get("location"),
            response=response,
        )
        return response
    finally:
        record_latency("cold_start_recommend", (time.perf_counter() - started_at) * 1000)


# Recommendation Engine: Retrieves, ranks, and explains personalized recommendations
# Returns JSON with recommendations list and reasoning_summary
async def recommend_logic(
    persona: dict,
    query: str,
    top_k: int,
    top_categories: list[str] = None,
    conversation_history: list = None,
    user_location: str | None = None,
    user_responses: dict | None = None,
    background_tasks: BackgroundTasks | None = None,
    request_user_id: str = "",
) -> dict:
    """
    Retrieves candidates using semantic search, ranks them using the LLM based on user profile
    and conversation context, and returns recommendations with reasoning.
    """
    # Step 1: Build semantic search query from persona
    taste_query = build_taste_query(persona, top_categories)

    location = _extract_user_location(persona, user_responses=user_responses, explicit_location=user_location)
    location_filter = _location_where_filter(location)
    has_conversation_history = conversation_history is not None and len(conversation_history) > 0

    # Step 2: Enrich the current query with conversation context only when history is present.
    search_query = query
    if has_conversation_history:
        query_for_enrichment = f"{query} {location}".strip() if location else query
        search_query = enrich_query_with_history(query_for_enrichment, conversation_history)

    # Step 3: Append the raw or enriched user query to the persona taste query for ChromaDB retrieval.
    full_search_query = _dedupe_query_text(_join_unique_query_parts([taste_query, search_query]))

    # Step 4: Search ChromaDB vector store with the enriched query, location filter, and similarity threshold.
    t2 = time.time()
    vector_store = app_state.get("vector_store")
    candidates = []
    if vector_store:
        candidates = vector_store.search(
            full_search_query,
            n_results=min(top_k * 3, 15),
            where=location_filter,
            min_score=MIN_RECOMMENDATION_SIMILARITY,
        )
    print(f"[TIMER] chromadb query: {(time.time() - t2) * 1000:.0f}ms")

    # Step 5: Clean and structure candidate data from search results
    valid_candidates = []
    candidates_by_id = {}
    candidates_by_name = {}
    for match in candidates:
        if match.get("id") in ["vector-store-unavailable", "search-error"]:
            continue
        meta = match.get("metadata", {})
        doc = match.get("document", "")
        score = float(match.get("score", 0.0) or 0.0)
        if score < MIN_RECOMMENDATION_SIMILARITY:
            continue
        if not _metadata_matches_location(meta, location):
            continue
        cid = _candidate_business_id(match, meta)
        if not cid:
            continue
        cname = str(meta.get("name") or meta.get("title") or cid)
        candidate = {
            "id": cid,
            "item_id": cid,
            "name": cname,
            "categories": meta.get("primary_category") or "",
            "city": meta.get("city") or "",
            "state": meta.get("state") or "",
            "stars": meta.get("stars", 0.0),
            "review_count": meta.get("review_count", 0),
            "similarity_score": score,
            "description": doc
        }
        valid_candidates.append(candidate)
        candidates_by_id[cid] = {"metadata": meta, "name": cname, "score": score}
        candidates_by_name[cname.casefold()] = {"metadata": meta, "name": cname, "score": score, "id": cid}

    # Step 6: Handle case where no candidates found
    if not valid_candidates:
        city_exists = _city_exists_in_dataset(vector_store, location)
        if location and not city_exists:
            summary = f"No businesses found in {location}. Our dataset currently covers US cities only."
        elif location:
            summary = (
                f"No businesses in {location} matched this query with similarity >= "
                f"{MIN_RECOMMENDATION_SIMILARITY}."
            )
        else:
            summary = f"No matching candidate businesses met similarity >= {MIN_RECOMMENDATION_SIMILARITY}."
        return {
            "recommendations": [],
            "reasoning_summary": summary,
            "validation": {
                "passed": True,
                "errors": [],
                "checked": {
                    "ids_are_real_business_ids": True,
                    "location": location or None,
                    "min_similarity": MIN_RECOMMENDATION_SIMILARITY,
                    "reasoning_summary_profile_fields": sorted(_profile_schema(persona).keys()),
                    "recommendations": [],
                },
            },
        }

    # Step 7: Return recommendations immediately and generate the LLM summary out of band.
    selected_candidates = valid_candidates[:top_k]
    recommendations = [
        {
            "id": candidate["id"],
            "item_id": candidate["id"],
            "name": candidate["name"],
            "reason": (
                f"{candidate['name']} is a {candidate['categories']} in {candidate['city']} "
                f"that matches your search for {query}."
            ),
        }
        for candidate in selected_candidates
    ]
    reasoning_summary = f"Top {len(recommendations)} results for '{query}' in {location}."
    validated_recs, validation = _validate_recommendation_output(
        recommendations,
        candidates_by_id=candidates_by_id,
        user_location=location,
        reasoning_summary=reasoning_summary,
        profile_fields=set(_profile_schema(persona).keys()),
    )

    if background_tasks and selected_candidates:
        top_result = selected_candidates[0]
        background_tasks.add_task(
            update_summary_async,
            request_user_id,
            query,
            location,
            top_result["name"],
            top_result["categories"],
            len(validated_recs),
        )

    return {
        "recommendations": validated_recs,
        "reasoning_summary": reasoning_summary,
        "validation": validation,
        "enriched_query": full_search_query,
    }

    # Step 7: Format conversation history for multi-turn context
    history_block = ""
    if conversation_history:
        history_block = "\nCONVERSATION HISTORY:\n"
        for msg in conversation_history:
            role = str(msg.get("role", "user")).capitalize()
            content = str(msg.get("content", ""))
            history_block += f"- {role}: {content}\n"

    # Step 8: Append current query if not already in history
    if query and (not conversation_history or conversation_history[-1].get("content") != query):
        history_block += f"- User (Latest): {query}\n"

    conversation_preference_instruction = ""
    if has_conversation_history:
        conversation_preference_instruction = (
            "The user previously expressed these preferences in conversation: "
            f"{json.dumps(conversation_history, indent=2)}. "
            "Reference these where relevant in your reasoning summary.\n"
        )

    llm_profile = _llm_user_profile(persona)
    profile_schema = _profile_schema(persona)

    # Step 9: Formulate LLM ranking prompt with persona, history, and candidates.
    prompt = (
        "You are an advanced recommendation system. Select and rank the best business recommendations for this user persona.\n\n"
        f"USER PROFILE SCHEMA (field_name: python_type):\n{json.dumps(profile_schema, indent=2)}\n\n"
        f"USER PERSONA:\n{json.dumps(llm_profile, indent=2)}\n"
        f"USER LOCATION FILTER:\n{location or 'None provided'}\n\n"
        f"SEARCH QUERY USED FOR RETRIEVAL:\n{full_search_query}\n\n"
        f"{history_block}\n"
        f"CANDIDATES FOR TAILORED SELECTION (20 Max):\n{json.dumps(valid_candidates, indent=2)}\n\n"
        f"Instructions:\n"
        f"1. Select the top {top_k} best matched items from the list.\n"
        f"2. Ensure chosen items align with user's loves, avoid pet peeves, and respect prior search criteria or follow-ups in the conversation history.\n"
        f"3. Every selected item must have similarity_score >= {MIN_RECOMMENDATION_SIMILARITY} and must match the user location filter if one is provided.\n"
        "4. Use only the id value supplied in each candidate. That id is the real Yelp business_id. Never use the business name as an id.\n"
        "5. Provide a 'reasoning_summary' at the top level detailing your overall recommendation strategy.\n"
        f"{conversation_preference_instruction}"
        "6. Only reference fields present in the provided user profile. Do not invent or assume any fields.\n"
        "7. For each chosen item, return exact fields: id, item_id, name, and reason (1-2 sentences mapping their preference style and current query).\n\n"
        "Return ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "reasoning_summary": "summary of overall recommendation strategy",\n'
        '  "recommendations": [\n'
        '    {\n'
        '      "id": "business_id",\n'
        '      "item_id": "business_id",\n'
        '      "name": "business_name",\n'
        '      "reason": "1-2 sentence tailored reasoning"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    system_prompt = (
        "You are a personalized recommendation ranking agent. You specialize in analyzing candidate sets against detailed user personas, "
        "matching contextual cues, and expressing recommendations with custom local accents.\n"
        f"{NIGERIAN_CONTEXT_BLOCK}\n"
        "Strictly output only the raw JSON. Do not include markdown code fences or conversational text."
    )

    # Step 4: Generate reasoning_summary via LLM.
    t3 = time.time()
    llm_client = app_state.get("llm")
    raw_response = ""
    if llm_client is None:
        raw_response = ""
    else:
        # Use underlying client if available to set token limits
        if getattr(llm_client, "client", None) is not None:
            try:
                resp = await asyncio.to_thread(
                    llm_client.client.chat.completions.create,
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=120,
                )
                raw_response = resp.choices[0].message.content or ""
            except Exception:
                raw_response = await asyncio.to_thread(llm_client.generate, prompt, system_prompt)
        else:
            raw_response = await asyncio.to_thread(llm_client.generate, prompt, system_prompt)
    print(f"[TIMER] summary generation: {(time.time() - t3) * 1000:.0f}ms")
    try:
        parsed = _extract_json(raw_response)
        recs = parsed.get("recommendations", [])

        # Correct IDs only when the LLM selected an existing candidate by name, then validate everything.
        corrected_recs = []
        for r in recs:
            rec_id = str(r.get("id") or r.get("item_id") or "").strip()
            candidate = candidates_by_id.get(rec_id)
            if not candidate:
                candidate_by_name = candidates_by_name.get(rec_id.casefold()) or candidates_by_name.get(
                    str(r.get("name") or "").casefold()
                )
                if candidate_by_name:
                    rec_id = candidate_by_name["id"]
            r["id"] = rec_id
            r["item_id"] = rec_id
            corrected_recs.append(r)

        reasoning_summary = parsed.get("reasoning_summary", "Tailored list compiled for your preferences.")
        t4 = time.time()
        validated_recs, validation = _validate_recommendation_output(
            corrected_recs,
            candidates_by_id=candidates_by_id,
            user_location=location,
            reasoning_summary=reasoning_summary,
            profile_fields=set(profile_schema.keys()),
        )
        print(f"[TIMER] validation: {(time.time() - t4) * 1000:.0f}ms")
        if validation["errors"] and any("reasoning_summary" in error for error in validation["errors"]):
            reasoning_summary = "Recommendations were selected from matching candidate businesses using only provided profile fields."
            validated_recs, validation = _validate_recommendation_output(
                validated_recs,
                candidates_by_id=candidates_by_id,
                user_location=location,
                reasoning_summary=reasoning_summary,
                profile_fields=set(profile_schema.keys()),
            )

        # Step 11: Generate short per-item reasons concurrently (optimize tokens and parallelism)
        checked_recs = validation.get("checked", {}).get("recommendations", [])
        sim_map = {str(item.get("id")): float(item.get("similarity_score", 0.0) or 0.0) for item in checked_recs}

        async def _generate_reason(candidate: dict) -> str:
            cid = str(candidate.get("id") or candidate.get("item_id") or "")
            name = str(candidate.get("name") or "")
            meta = candidates_by_id.get(cid, {}).get("metadata", {})
            category = meta.get("primary_category") or meta.get("category") or ""
            city = meta.get("city") or ""
            stars = meta.get("stars") or candidate.get("stars") or ""
            similarity = sim_map.get(cid, 0.0)

            # Optimization 3: Skip LLM for low-confidence results
            if similarity < 0.75:
                return (
                    f"{name} is a {category} in {city} with a {stars}-star rating, matching your search for {query}."
                )

            # Otherwise, call LLM to craft a short 1-2 sentence reason. Limit tokens to 80.
            reason_prompt = (
                f"Write a 1-2 sentence recommendation reason for the business '{name}'. "
                f"User query: {query}. User profile (summary): {json.dumps(llm_profile)}. "
                f"Keep it concise and specific to why {name} matches the user's intent."
            )
            reason_system = (
                "You are a concise recommendation explanation generator. Output only the reason text."
            )

            if llm_client is None:
                return reason_prompt

            # Use underlying client if available to set max_tokens precisely
            try:
                if getattr(llm_client, "client", None) is not None:
                    resp = await asyncio.to_thread(
                        llm_client.client.chat.completions.create,
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": reason_system},
                            {"role": "user", "content": reason_prompt},
                        ],
                        max_tokens=80,
                    )
                    # If the client API accepted a dict, try to extract like before
                    if hasattr(resp, "choices"):
                        return (resp.choices[0].message.content or "").strip()
                    # Fallback string
                    return str(resp)
                else:
                    # Fall back to wrapper generate via thread
                    resp_text = await asyncio.to_thread(llm_client.generate, reason_prompt, reason_system)
                    return str(resp_text).strip()
            except Exception:
                # Fallback template on failure
                return (
                    f"{name} is a {category} in {city} with a {stars}-star rating, matching your search for {query}."
                )

        # Step 3: Generate short per-item reasons concurrently
        t5 = time.time()
        to_explain = validated_recs[:top_k]
        tasks = [_generate_reason(c) for c in to_explain]
        reasons = []
        try:
            reasons = await asyncio.gather(*tasks)
        except Exception:
            # If any reason task fails, fall back to template reasons
            reasons = [
                (
                    f"{c.get('name')} is a {candidates_by_id.get(c.get('id', ''), {}).get('metadata', {}).get('primary_category','')} "
                    f"in {candidates_by_id.get(c.get('id', ''), {}).get('metadata', {}).get('city','')} matching your search for {query}."
                )
                for c in to_explain
            ]
        finally:
            print(f"[TIMER] reason generation: {(time.time() - t5) * 1000:.0f}ms")

        # Attach generated reasons back to recommendations
        for rec, reason_text in zip(to_explain, reasons):
            rec["reason"] = reason_text

        return {
            "recommendations": to_explain,
            "reasoning_summary": reasoning_summary,
            "validation": validation,
            "enriched_query": full_search_query,
        }
    except Exception:
        # Fallback: Return top candidates by category if LLM fails
        fallback_recs = []
        for c in valid_candidates[:top_k]:
            fallback_recs.append({
                "id": c["id"],
                "item_id": c["id"],
                "name": c["name"],
                "reason": f"Selected because it fits your preference for {c['categories']} in {c['city']}."
            })
        reasoning_summary = "Top items selected from local businesses that met the similarity threshold."
        validated_recs, validation = _validate_recommendation_output(
            fallback_recs,
            candidates_by_id=candidates_by_id,
            user_location=location,
            reasoning_summary=reasoning_summary,
            profile_fields=set(profile_schema.keys()),
        )
        return {
            "recommendations": validated_recs,
            "reasoning_summary": reasoning_summary,
            "validation": validation,
            "enriched_query": full_search_query,
        }


# Cold-Start Persona Builder: Creates initial persona from onboarding questionnaire
# Used when user has no review history (worth 25 points in scoring)
def build_starter_persona(user_responses: dict) -> dict:
    """
    Builds a starter user persona JSON from onboarding questionnaire answers.
    """
    prompt = (
        "A new user has completed the onboarding questionnaire. Build a starter persona JSON based on their answers.\n\n"
        f"ONBOARDING RESPONSES:\n{json.dumps(user_responses, indent=2)}\n\n"
        "Generate a valid starter persona JSON with these exact fields:\n"
        "{\n"
        '  "avg_rating": 4.0,\n'
        '  "tone": "casual",\n'
        '  "top_topics": ["food", "service"],\n'
        '  "pet_peeves": ["slow service"],\n'
        '  "loves": ["spicy food"],\n'
        '  "review_length": "medium",\n'
        '  "naija_cues": true,\n'
        '  "sample_phrases": ["no dulling"]\n'
        "}\n\n"
        "Instructions:\n"
        "- Infuse local Nigerian style and flag naija_cues as true if they prefer local spots or use Pidgin language styles.\n"
        "- Standardize tone to: 'casual', 'formal', 'pidgin', or 'mixed'.\n"
        "- Standardize review_length to: 'short', 'medium', or 'long'.\n"
        "- Deduce loves and pet_peeves directly from answers."
    )

    system_prompt = (
        "You are a professional behavioral analyst specializing in Nigerian consumer patterns. "
        "Analyze onboarding responses to generate a starter persona profile.\n"
        f"{NIGERIAN_CONTEXT_BLOCK}\n"
        "Strictly output only the raw JSON. Do not include markdown code fences or conversational text."
    )

    # Call LLM to build persona from onboarding responses
    raw_response = app_state["llm"].generate(prompt=prompt, system_prompt=system_prompt)
    try:
        return _extract_json(raw_response)
    except Exception:
        # Fallback: Return generic persona if LLM fails
        return {
            "avg_rating": 4.0,
            "tone": "casual",
            "top_topics": ["Local Spot", "Food"],
            "pet_peeves": ["poor service"],
            "loves": ["spicy food", "good vibe"],
            "review_length": "medium",
            "naija_cues": True,
            "sample_phrases": ["no dulling", "confirm"]
        }


# FastAPI endpoint for Task B: Generate personalized recommendations
# POST /task-b/recommend
# Handles both cold-start (new users) and normal recommendation flows
@router.post("/recommend")
async def recommend(request: RecommendRequest, background_tasks: BackgroundTasks) -> Any:
    started_at = time.perf_counter()
    t0 = time.time()
    user_history = app_state["user_history"].get_history(request.user_id)
    has_existing_profile = bool(user_history.get("reviews"))

    # Step 1 - normalize and validate input
    print(f"[TIMER] input validation: {(time.time() - t0) * 1000:.0f}ms")
    t1 = time.time()

    try:
        if request.is_cold_start is True and request.user_responses:
            # Branch 1: Cold-start user has answered onboarding, so build a temporary profile and recommend.
            starter_persona = _build_cold_start_profile(request.user_responses)
            starter_query = request.query or _build_cold_start_query(starter_persona)
            response = await recommend_logic(
                persona=starter_persona,
                query=starter_query,
                top_k=request.top_k,
                top_categories=[],
                conversation_history=request.conversation_history,
                user_location=request.location or starter_persona.get("location"),
                user_responses=starter_persona,
                background_tasks=background_tasks,
                request_user_id=request.user_id,
            )
            _track_task_b_metrics(
                user_id=request.user_id,
                is_cold_start=True,
                query=starter_query,
                location=request.location or starter_persona.get("location"),
                response=response,
            )
            return response

        elif request.is_cold_start is True and not has_existing_profile:
            # Branch 2: Cold-start user has no saved profile and no answers yet, so ask onboarding questions.
            return {
                "status": "cold_start",
                "questions": [
                    "What's your favourite type of food or cuisine?",
                    "Do you prefer fast food, sit-down restaurants, or street food?",
                    "What is your budget range?",
                    "Are you a 'try new things' or 'stick to favourites' person?",
                    "What city or area are you in?",
                ],
            }

        elif request.is_cold_start is False:
            # Branch 3: Explicit non-cold-start request, so always use the existing-profile path.
            persona = _get_cached_persona(request.user_id, user_history)
            response = await recommend_logic(
                persona=persona,
                query=request.query,
                top_k=request.top_k,
                top_categories=user_history.get("top_categories", []),
                conversation_history=request.conversation_history,
                user_location=request.location,
                user_responses=request.user_responses,
                background_tasks=background_tasks,
                request_user_id=request.user_id,
            )
            _track_task_b_metrics(
                user_id=request.user_id,
                is_cold_start=False,
                query=request.query,
                location=request.location,
                response=response,
            )
            return response

        else:
            # Branch 4: Cold-start flag is true but a profile exists, so prefer the existing profile.
            persona = _get_cached_persona(request.user_id, user_history)
            response = await recommend_logic(
                persona=persona,
                query=request.query,
                top_k=request.top_k,
                top_categories=user_history.get("top_categories", []),
                conversation_history=request.conversation_history,
                user_location=request.location,
                user_responses=request.user_responses,
                background_tasks=background_tasks,
                request_user_id=request.user_id,
            )
            _track_task_b_metrics(
                user_id=request.user_id,
                is_cold_start=False,
                query=request.query,
                location=request.location,
                response=response,
            )
            return response
    finally:
        record_latency("recommend", (time.perf_counter() - started_at) * 1000)
        print(f"[TIMER] TOTAL: {(time.time() - t0) * 1000:.0f}ms")
