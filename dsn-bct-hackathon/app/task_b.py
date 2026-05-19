from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.chromadb_client import VectorStore


router = APIRouter(tags=["Task B"])
vector_store = VectorStore()


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


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    if request.is_cold_start:
        return RecommendResponse(
            user_id=request.user_id,
            recommendations=[
                Recommendation(
                    item_id="onboarding",
                    name="Complete onboarding preferences",
                    reason="We need a few preference signals before making personalized recommendations.",
                    score=1.0,
                )
            ],
        )

    matches = vector_store.search(query=request.query, n_results=request.top_k)
    recommendations: list[Recommendation] = []

    for match in matches:
        metadata: dict[str, Any] = match.get("metadata") or {}
        item_id = str(metadata.get("item_id") or match.get("id") or "unknown-item")
        name = str(metadata.get("name") or metadata.get("title") or item_id)
        error = metadata.get("error")
        reason = (
            str(error)
            if error
            else f"Matched because it is semantically related to: {request.query}"
        )

        recommendations.append(
            Recommendation(
                item_id=item_id,
                name=name,
                reason=reason,
                score=float(match.get("score", 0.0)),
            )
        )

    return RecommendResponse(user_id=request.user_id, recommendations=recommendations)
