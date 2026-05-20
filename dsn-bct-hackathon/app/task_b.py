from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.startup import app_state


router = APIRouter(tags=["Task B"])


class RecommendRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    is_cold_start: bool = False
    domain: Literal["yelp", "amazon"] | None = None


class ColdStartRecommendRequest(BaseModel):
    user_id: str
    answers: dict


class Recommendation(BaseModel):
    item_id: str
    name: str
    reason: str
    score: float
    domain: str = "unknown"


class RecommendResponse(BaseModel):
    user_id: str
    recommendations: list[Recommendation]


class ColdStartRecommendResponse(BaseModel):
    user_id: str
    is_cold_start: bool
    recommendations: list[Recommendation]


def _build_reason(metadata: dict[str, Any], query: str) -> str:
    error = metadata.get("error")
    if error:
        return str(error)

    domain = str(metadata.get("domain") or "unknown")
    name = str(metadata.get("name") or "This item")
    category = str(metadata.get("primary_category") or metadata.get("category") or "a relevant category")
    city = str(metadata.get("city") or "").strip()
    state = str(metadata.get("state") or "").strip()
    stars = metadata.get("stars")
    review_count = metadata.get("review_count")
    price = metadata.get("price")

    if domain == "amazon":
        price_text = f" and costs about {price}" if price not in [None, "", 0, 0.0] else ""
        rating_text = ""
        if stars is not None and review_count is not None:
            rating_text = f" It has a {stars} star rating across {review_count} ratings."
        return f"{name} matches '{query}' because it is an Amazon {category} product{price_text}.{rating_text}".strip()

    location = ", ".join(part for part in [city, state] if part)
    location_text = f" in {location}" if location else ""
    rating_text = ""
    if stars is not None and review_count is not None:
        rating_text = f" It has a {stars} star rating across {review_count} reviews."

    return f"{name} matches '{query}' because it is indexed under {category}{location_text}.{rating_text}".strip()


def _format_match(match: dict, query: str) -> Recommendation:
    metadata: dict[str, Any] = match.get("metadata") or {}
    item_id = str(
        metadata.get("business_id")
        or metadata.get("product_id")
        or metadata.get("item_id")
        or match.get("id")
        or "unknown-item"
    )
    name = str(metadata.get("name") or metadata.get("title") or item_id)
    domain = str(metadata.get("domain") or "unknown")
    reason = _build_reason(metadata=metadata, query=query)

    return Recommendation(
        item_id=item_id,
        name=name,
        reason=reason or f"{name} was retrieved as a relevant match for '{query}'.",
        score=float(match.get("score", 0.0)),
        domain=domain,
    )


def _filter_by_domain(matches: list[dict], domain: str | None) -> list[dict]:
    if domain is None:
        return matches
    return [match for match in matches if (match.get("metadata") or {}).get("domain") == domain]


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


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
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
                    domain="system",
                )
            ],
        )

    cold_start_handler = app_state.get("cold_start_handler")
    user_history_service = app_state.get("user_history")
    user_history = (
        user_history_service.get_history(request.user_id)
        if user_history_service is not None
        else {"review_count": 0, "is_cold_start": True}
    )

    if request.is_cold_start or (
        cold_start_handler is not None and cold_start_handler.is_cold_start(user_history)
    ):
        answers = {1: request.query}
        raw_recommendations = (
            cold_start_handler.get_cold_start_recommendations(answers, top_k=request.top_k)
            if cold_start_handler is not None
            else []
        )
        filtered = [
            item
            for item in raw_recommendations
            if request.domain is None or item.get("domain") == request.domain
        ]
        return RecommendResponse(
            user_id=request.user_id,
            recommendations=[Recommendation(**item) for item in filtered[: request.top_k]],
        )

    search_size = request.top_k if request.domain is None else min(50, request.top_k * 5)
    matches = vector_store.search(query=request.query, n_results=search_size)
    filtered_matches = _filter_by_domain(matches, request.domain)
    recommendations = [_format_match(match, request.query) for match in filtered_matches[: request.top_k]]

    return RecommendResponse(user_id=request.user_id, recommendations=recommendations)
