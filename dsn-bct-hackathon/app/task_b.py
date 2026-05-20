from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.startup import app_state


router = APIRouter(tags=["Task B"])


class RecommendRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    is_cold_start: bool = False


class Recommendation(BaseModel):
    item_id: str
    name: str
    reason: str
    score: float


class RecommendResponse(BaseModel):
    user_id: str
    recommendations: list[Recommendation]


def _build_reason(metadata: dict[str, Any], query: str) -> str:
    error = metadata.get("error")
    if error:
        return str(error)

    name = str(metadata.get("name") or "This business")
    primary_category = str(metadata.get("primary_category") or "a relevant category")
    city = str(metadata.get("city") or "").strip()
    state = str(metadata.get("state") or "").strip()
    stars = metadata.get("stars")
    review_count = metadata.get("review_count")

    location = ", ".join(part for part in [city, state] if part)
    location_text = f" in {location}" if location else ""
    rating_text = ""
    if stars is not None and review_count is not None:
        rating_text = f" It has a {stars} star rating across {review_count} reviews."

    return f"{name} matches '{query}' because it is indexed under {primary_category}{location_text}.{rating_text}".strip()


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    if request.is_cold_start:
        return RecommendResponse(
            user_id=request.user_id,
            recommendations=[
                Recommendation(
                    item_id="onboarding",
                    name="Complete onboarding preferences",
                    reason="Tell us a few cuisines, locations, or service types you like so we can personalize your recommendations.",
                    score=1.0,
                )
            ],
        )

    vector_store = app_state.get("vector_store")
    if vector_store is None:
        return RecommendResponse(
            user_id=request.user_id,
            recommendations=[
                Recommendation(
                    item_id="vector-store-unavailable",
                    name="Recommendation index unavailable",
                    reason="The vector store has not finished startup initialization yet.",
                    score=0.0,
                )
            ],
        )

    matches = vector_store.search(query=request.query, n_results=request.top_k)
    recommendations: list[Recommendation] = []

    for match in matches:
        metadata: dict[str, Any] = match.get("metadata") or {}
        item_id = str(metadata.get("business_id") or metadata.get("item_id") or match.get("id") or "unknown-item")
        name = str(metadata.get("name") or metadata.get("title") or item_id)
        reason = _build_reason(metadata=metadata, query=request.query)

        recommendations.append(
            Recommendation(
                item_id=item_id,
                name=name,
                reason=reason,
                score=float(match.get("score", 0.0)),
            )
        )

    return RecommendResponse(user_id=request.user_id, recommendations=recommendations)
