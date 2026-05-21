import json
import re
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.startup import app_state

router = APIRouter(tags=["Task B"])

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


# Query Builder: Constructs semantic search string for ChromaDB retrieval
# Combines user loves, topics, categories, negates pet peeves, and adds Nigerian context if applicable
def build_taste_query(persona: dict, top_categories: list[str] = None) -> str:
    """
    Constructs a semantic search string using user loves, top topics,
    historical categories, negation of pet peeves, and Nigerian local terms if applicable.
    """
    # Extract persona components for query building
    loves = persona.get("loves", [])
    top_topics = persona.get("top_topics", [])
    categories = top_categories or []

    # Build positive query components
    query_parts = []
    if loves:
        query_parts.append(" ".join(loves))
    if top_topics:
        query_parts.append(" ".join(top_topics))
    if categories:
        query_parts.append(" ".join(categories))

    # Add negation hints for pet peeves (what to avoid)
    pet_peeves = persona.get("pet_peeves", [])
    if pet_peeves:
        negation_hints = " ".join(f"avoid {peeve}" for peeve in pet_peeves)
        query_parts.append(negation_hints)

    # Add Nigerian culinary and locality terms if user has Naija cues
    if persona.get("naija_cues", False):
        query_parts.append("suya pepper soup buka Lagos")

    return " ".join(query_parts).strip()


class ColdStartRecommendRequest(BaseModel):
    user_id: str
    answers: dict


class Recommendation(BaseModel):
    item_id: str
    name: str
    reason: str
    score: float
    domain: str = "unknown"


class ColdStartRecommendResponse(BaseModel):
    user_id: str
    is_cold_start: bool
    recommendations: list[Recommendation]


@router.get("/onboarding-questions")
def onboarding_questions() -> list[dict]:
    cold_start_handler = app_state.get("cold_start_handler")
    if cold_start_handler is None:
        return []
    return cold_start_handler.get_onboarding_questions()


@router.post("/cold-start-recommend", response_model=ColdStartRecommendResponse)
def cold_start_recommend(request: ColdStartRecommendRequest) -> ColdStartRecommendResponse:
    cold_start_handler = app_state.get("cold_start_handler")
    if cold_start_handler is None:
        return ColdStartRecommendResponse(
            user_id=request.user_id,
            is_cold_start=True,
            recommendations=[
                Recommendation(
                    item_id="cold-start-unavailable",
                    name="Cold start handler unavailable",
                    reason="The onboarding recommender has not finished startup initialization yet.",
                    score=0.0,
                    domain="system",
                )
            ],
        )

    raw_recommendations = cold_start_handler.get_cold_start_recommendations(request.answers, top_k=5)
    recommendations = [Recommendation(**item) for item in raw_recommendations]
    return ColdStartRecommendResponse(
        user_id=request.user_id,
        is_cold_start=True,
        recommendations=recommendations,
    )


# Recommendation Engine: Retrieves, ranks, and explains personalized recommendations
# Returns JSON with recommendations list and reasoning_summary
def recommend_logic(
    persona: dict,
    query: str,
    top_k: int,
    top_categories: list[str] = None,
    conversation_history: list = None
) -> dict:
    """
    Retrieves candidates using semantic search, ranks them using the LLM based on user profile
    and conversation context, and returns recommendations with reasoning.
    """
    # Step 1: Build semantic search query from persona
    taste_query = build_taste_query(persona, top_categories)

    # Step 2: Append user's explicit query if provided
    full_search_query = taste_query
    if query:
        full_search_query = f"{taste_query} {query}".strip()

    # Step 3: Search ChromaDB vector store for 20 candidate items
    vector_store = app_state.get("vector_store")
    candidates = []
    if vector_store:
        candidates = vector_store.search(full_search_query, n_results=20)

    # Step 4: Clean and structure candidate data from search results
    valid_candidates = []
    for idx, match in enumerate(candidates):
        if match.get("id") in ["vector-store-unavailable", "search-error"]:
            continue
        meta = match.get("metadata", {})
        doc = match.get("document", "")
        cid = str(meta.get("business_id") or meta.get("item_id") or match.get("id") or f"item-{idx}")
        cname = str(meta.get("name") or meta.get("title") or cid)
        valid_candidates.append({
            "id": cid,
            "name": cname,
            "categories": meta.get("primary_category") or "",
            "city": meta.get("city") or "",
            "stars": meta.get("stars", 0.0),
            "review_count": meta.get("review_count", 0),
            "description": doc
        })

    # Step 5: Handle case where no candidates found
    if not valid_candidates:
        return {
            "recommendations": [],
            "reasoning_summary": "No matching candidate businesses were found."
        }

    # Step 6: Format conversation history for multi-turn context
    history_block = ""
    if conversation_history:
        history_block = "\nCONVERSATION HISTORY:\n"
        for msg in conversation_history:
            role = str(msg.get("role", "user")).capitalize()
            content = str(msg.get("content", ""))
            history_block += f"- {role}: {content}\n"

    # Step 7: Append current query if not already in history
    if query and (not conversation_history or conversation_history[-1].get("content") != query):
        history_block += f"- User (Latest): {query}\n"

    # Step 8: Formulate LLM ranking prompt with persona, history, and candidates
    prompt = (
        "You are an advanced recommendation system. Select and rank the best business recommendations for this user persona.\n\n"
        f"USER PERSONA:\n{json.dumps(persona, indent=2)}\n"
        f"{history_block}\n"
        f"CANDIDATES FOR TAILORED SELECTION (20 Max):\n{json.dumps(valid_candidates, indent=2)}\n\n"
        f"Instructions:\n"
        f"1. Select the top {top_k} best matched items from the list.\n"
        f"2. Ensure chosen items align with user's loves, avoid pet peeves, and respect prior search criteria or follow-ups in the conversation history.\n"
        f"3. If persona['naija_cues'] is true, prioritize candidates that match local tastes (like suya spots, buka cafes, local spots) "
        "and write the 'reason' using subtle Pidgin expressions and local cultural references.\n"
        "4. Provide a 'reasoning_summary' at the top level detailing your overall recommendation strategy and why this batch is perfect for them.\n"
        "5. For each chosen item, return exact fields: id, name, and reason (1-2 sentences mapping their preference style and current query).\n\n"
        "Return ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "reasoning_summary": "summary of overall recommendation strategy",\n'
        '  "recommendations": [\n'
        '    {\n'
        '      "id": "business_id",\n'
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

    # Step 9: Call LLM to rank and select top recommendations
    raw_response = app_state["llm"].generate(prompt=prompt, system_prompt=system_prompt)
    try:
        parsed = _extract_json(raw_response)
        recs = parsed.get("recommendations", [])

        # Ensure both 'id' and 'item_id' fields exist for integration compatibility
        for r in recs:
            if "item_id" not in r and "id" in r:
                r["item_id"] = r["id"]
            elif "id" not in r and "item_id" in r:
                r["id"] = r["item_id"]

        # Step 10: Return ranked recommendations with reasoning
        return {
            "recommendations": recs,
            "reasoning_summary": parsed.get("reasoning_summary", "Tailored list compiled for your preferences.")
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
        return {
            "recommendations": fallback_recs,
            "reasoning_summary": "Top items selected based on category relevance."
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
def recommend(request: RecommendRequest) -> Any:
    # Step 1: Check if this is a cold-start user (no review history)
    user_history = app_state["user_history"].get_history(request.user_id)
    is_cold = request.is_cold_start or user_history.get("is_cold_start", False)

    # Step 2: Handle cold-start flow
    if is_cold:
        if not request.user_responses:
            # Cold-start stage 1: Return onboarding questions
            return {
                "status": "cold_start",
                "questions": [
                    "What's your favourite type of food or cuisine?",
                    "Rate your last great experience out of 5",
                    "Name one thing that ruins your experience anywhere",
                    "Are you a 'try new things' or 'stick to favourites' person?",
                    "Do you prefer local Nigerian spots or international chains?"
                ]
            }
        else:
            # Cold-start stage 2: Build persona from responses and recommend
            starter_persona = build_starter_persona(request.user_responses)
            return recommend_logic(
                persona=starter_persona,
                query=request.query,
                top_k=request.top_k,
                top_categories=[],
                conversation_history=request.conversation_history
            )

    # Step 3: Normal recommendation flow for existing users
    from app.task_a import build_persona
    persona = build_persona(user_history)

    return recommend_logic(
        persona=persona,
        query=request.query,
        top_k=request.top_k,
        top_categories=user_history.get("top_categories", []),
        conversation_history=request.conversation_history
    )
