import json
import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.llm_client import LLMClient


router = APIRouter(tags=["Task A"])
llm_client = LLMClient()


class GenerateReviewRequest(BaseModel):
    user_id: str
    item_id: str
    persona: dict[str, Any] = Field(default_factory=dict)


class GenerateReviewResponse(BaseModel):
    user_id: str
    item_id: str
    rating: float = Field(ge=1.0, le=5.0)
    review_text: str
    naija_cues_applied: bool


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


@router.post("/generate-review", response_model=GenerateReviewResponse)
def generate_review(request: GenerateReviewRequest) -> GenerateReviewResponse:
    persona_json = json.dumps(request.persona, ensure_ascii=True)
    prompt = (
        "Generate a realistic customer review for a recommendation-system evaluation.\n"
        f"User ID: {request.user_id}\n"
        f"Item ID: {request.item_id}\n"
        f"Persona JSON: {persona_json}\n\n"
        "Return only valid JSON with this exact schema: "
        '{"rating": 4.5, "review_text": "short natural review", "naija_cues_applied": true}. '
        "The rating must be a number from 1.0 to 5.0. Include light Nigerian/Naija phrasing only when it fits the persona."
    )
    system_prompt = "You are a helpful assistant that returns strict JSON and no markdown."

    raw_response = llm_client.generate(prompt=prompt, system_prompt=system_prompt)

    try:
        parsed = _extract_json(raw_response)
        rating = float(parsed.get("rating", 3.0))
        rating = min(5.0, max(1.0, rating))
        review_text = str(parsed.get("review_text", "")).strip()
        naija_cues_applied = bool(parsed.get("naija_cues_applied", False))

        if not review_text:
            review_text = "Review could not be generated from the model response."

        return GenerateReviewResponse(
            user_id=request.user_id,
            item_id=request.item_id,
            rating=rating,
            review_text=review_text,
            naija_cues_applied=naija_cues_applied,
        )
    except Exception:
        return GenerateReviewResponse(
            user_id=request.user_id,
            item_id=request.item_id,
            rating=3.0,
            review_text=f"Unable to parse LLM response as JSON. Raw response: {raw_response}",
            naija_cues_applied=False,
        )
