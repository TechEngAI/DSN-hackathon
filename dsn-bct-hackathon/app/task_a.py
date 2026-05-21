import json
import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.startup import app_state

router = APIRouter(tags=["Task A"])

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


# Request model for Task A review generation endpoint
class GenerateReviewRequest(BaseModel):
    user_id: str  # Unique identifier for the user
    item_id: str  # ID of the business/item to generate review for
    persona: dict[str, Any] = Field(default_factory=dict)  # Optional pre-built persona (if not provided, will be built from history)


# Response model for Task A review generation endpoint
class GenerateReviewResponse(BaseModel):
    rating: float = Field(ge=1.0, le=5.0)  # Generated star rating (1-5)
    review_text: str  # Generated review text matching user persona
    reasoning: str  # Explanation of why this rating and review were chosen


# Helper function to extract JSON from LLM response, handling markdown code fences
def _extract_json(text: str) -> dict[str, Any]:
    try:
        # First, try to clean potential markdown fences
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


# Persona Builder: Extracts user behavioral profile from historical reviews
# Returns JSON with avg_rating, tone, top_topics, pet_peeves, loves, review_length, naija_cues, sample_phrases
def build_persona(user_history: dict) -> dict:
    """
    Builds a detailed profile/persona of the user from their historical reviews,
    identifying their preference patterns, tone, loves, and pet peeves.
    """
    # Handle cold start users (no review history)
    if user_history.get("is_cold_start", False) or not user_history.get("reviews"):
        return {
            "avg_rating": 3.0,
            "tone": "casual",
            "top_topics": [],
            "pet_peeves": [],
            "loves": [],
            "review_length": "medium",
            "naija_cues": False,
            "sample_phrases": []
        }

    # Format historical reviews into a readable format for LLM analysis
    reviews_block = ""
    for idx, review in enumerate(user_history.get("reviews", []), 1):
        stars = review.get("stars", "N/A")
        text = review.get("text", "").strip()
        reviews_block += f"Review {idx} (Rating: {stars}/5 stars):\n\"{text}\"\n\n"

    prompt = (
        "Analyze the following user review history to understand their personality, rating patterns, likes/dislikes, "
        "and preferred writing style. Create a structured behavioral persona JSON.\n\n"
        f"USER REVIEW HISTORY:\n{reviews_block}\n"
        "Return ONLY a valid JSON object with the following fields and no other text or explanation:\n"
        "{\n"
        '  "avg_rating": 4.2,\n'
        '  "tone": "casual",\n'
        '  "top_topics": ["food", "service", "ambience"],\n'
        '  "pet_peeves": ["slow service", "high prices"],\n'
        '  "loves": ["spicy food", "friendly staff"],\n'
        '  "review_length": "medium",\n'
        '  "naija_cues": true,\n'
        '  "sample_phrases": ["e sweet die", "abeg no dulling"]\n'
        "}\n\n"
        "Rules for the output values:\n"
        "- tone: must be one of: 'formal', 'casual', 'pidgin', or 'mixed'\n"
        "- review_length: must be one of: 'short', 'medium', or 'long'\n"
        "- naija_cues: boolean indicating if this user uses Nigerian Pidgin, slangs, or local cultural references in their style.\n"
        "- sample_phrases: a list of short phrases or words matching the user's specific vocabulary style.\n"
    )

    system_prompt = (
        "You are a professional behavioral analyst specializing in Nigerian consumer patterns. "
        "Analyze user reviews and extract a precise, high-fidelity profile.\n"
        f"{NIGERIAN_CONTEXT_BLOCK}\n"
        "Strictly output only the raw JSON. Do not include markdown code fences or conversational text."
    )

    # Call LLM to extract persona from review history
    raw_response = app_state["llm"].generate(prompt=prompt, system_prompt=system_prompt)
    try:
        return _extract_json(raw_response)
    except Exception:
        # Fallback: Return basic persona from user history if LLM fails
        return {
            "avg_rating": float(user_history.get("avg_rating", 3.0)),
            "tone": "casual",
            "top_topics": user_history.get("top_categories", []),
            "pet_peeves": [],
            "loves": [],
            "review_length": "medium",
            "naija_cues": False,
            "sample_phrases": []
        }


# Review Generator: Simulates a user review for an unseen item based on persona
# Returns JSON with rating, review_text, and reasoning
def generate_review_logic(persona: dict, item: dict) -> dict:
    """
    Generates a review for an item that perfectly aligns with the given persona.
    """
    item_id = item.get("item_id")

    # Step 1: Try to find business details in app_state memory
    businesses = app_state.get("businesses", [])
    matched_business = None
    for b in businesses:
        if b.get("business_id") == item_id:
            matched_business = b
            break

    item_name = ""
    item_category = ""
    item_description = ""

    if matched_business:
        item_name = matched_business.get("name", "")
        item_category = matched_business.get("categories", "")

    # Step 2: Query ChromaDB vector store to enrich business information
    vector_store = app_state.get("vector_store")
    if vector_store:
        search_results = vector_store.search(item_id, n_results=1)
        if search_results and search_results[0].get("id") != "vector-store-unavailable" and search_results[0].get("id") != "search-error":
            meta = search_results[0].get("metadata", {})
            doc = search_results[0].get("document", "")
            if not item_name:
                item_name = meta.get("name") or meta.get("title") or ""
            if not item_category:
                item_category = meta.get("primary_category") or ""
            item_description = doc

    # Step 3: Fallback if no business details found
    if not item_name:
        item_name = item.get("name") or f"Business {item_id}"
    if not item_category:
        item_category = item.get("category") or "General"
    if not item_description:
        item_description = f"A popular business categorized under: {item_category}."

    prompt = (
        "Generate an authentic and realistic customer review for the specified business that perfectly matches the user persona profile.\n\n"
        f"USER PERSONA:\n{json.dumps(persona, indent=2)}\n\n"
        f"BUSINESS DETAILS:\n"
        f"- ID: {item_id}\n"
        f"- Name: {item_name}\n"
        f"- Category: {item_category}\n"
        f"- Profile / Context: {item_description}\n\n"
        "Instructions for review generation:\n"
        "1. Write the review from the perspective of this persona. Match the requested tone and review_length exactly.\n"
        "2. If persona['naija_cues'] is true, you MUST write the review in natural Nigerian Pidgin, "
        "referencing Nigerian local context elements (e.g. suya, jollof, owambe, Detty December, Lagos traffic) and "
        "using phrases like 'e sweet die', 'abeg', 'no dulling', 'e dey hit'.\n"
        "3. Emphasize items listed in the persona's 'loves' if they are relevant, or react negatively to items listed in 'pet_peeves' if relevant.\n"
        "4. Calibrate the star rating (between 1.0 and 5.0) to match persona['avg_rating'] and how the business details align with their loves/peeves.\n"
        "5. Include a reasoning field explaining the rating, tone, and why it perfectly reflects the persona's behaviors.\n\n"
        "Return ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "rating": 4.5,\n'
        '  "review_text": "text of the review here",\n'
        '  "reasoning": "rationale for rating and tone choice based on persona and business qualities"\n'
        "}"
    )

    system_prompt = (
        "You are an expert review generator who writes highly authentic, realistic customer reviews. "
        "You strictly adopt the provided user persona in terms of tone, style, cultural background, and rating behavior.\n"
        f"{NIGERIAN_CONTEXT_BLOCK}\n"
        "Strictly output only the raw JSON. Do not include markdown code fences or conversational text."
    )

    # Step 4: Call LLM to generate review matching persona
    raw_response = app_state["llm"].generate(prompt=prompt, system_prompt=system_prompt)
    try:
        return _extract_json(raw_response)
    except Exception:
        # Fallback: Return generic review if LLM fails
        return {
            "rating": persona.get("avg_rating") or 3.5,
            "review_text": f"This place {item_name} is okay. The experience was solid and fits my expectations.",
            "reasoning": "Fallback review generated due to model parsing exception."
        }


# FastAPI endpoint for Task A: Generate a review for an unseen item based on user persona
# POST /task-a/generate-review
@router.post("/generate-review", response_model=GenerateReviewResponse)
def generate_review(request: GenerateReviewRequest) -> GenerateReviewResponse:
    # Step 1: Retrieve user history from app_state
    user_history = app_state["user_history"].get_history(request.user_id)

    # Step 2: Use provided persona or build from user history
    persona = request.persona
    if not persona:
        persona = build_persona(user_history)

    # Step 3: Generate review based on persona and item details
    item = {"item_id": request.item_id}
    result = generate_review_logic(persona, item)

    # Step 4: Validate rating is within 1-5 range
    rating = float(result.get("rating", 3.0))
    rating = min(5.0, max(1.0, rating))

    # Step 5: Return structured response
    return GenerateReviewResponse(
        rating=rating,
        review_text=str(result.get("review_text", "")),
        reasoning=str(result.get("reasoning", ""))
    )
