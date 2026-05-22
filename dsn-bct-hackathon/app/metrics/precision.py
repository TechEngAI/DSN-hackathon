from typing import Any

MIN_RELEVANCE_SIMILARITY = 0.65

# Lightweight query intent map used for Precision@K.
QUERY_TO_CATEGORY = {
    "tacos": ["Mexican", "Tex-Mex"],
    "pizza": ["Pizza", "Italian"],
    "burgers": ["Burgers", "American", "Fast Food"],
    "spicy food": ["Mexican", "Thai", "Indian", "Tex-Mex"],
    "wings": ["Chicken Wings", "Sports Bars", "American"],
}


def expected_categories_for_query(query: str) -> list[str]:
    """Return categories whose query keys appear in the user query."""
    normalized_query = str(query or "").casefold()
    expected: list[str] = []
    for query_key, categories in QUERY_TO_CATEGORY.items():
        if query_key in normalized_query:
            expected.extend(categories)

    # Treat generic spicy queries as spicy-food intent when the exact phrase is absent.
    if "spicy" in normalized_query and not expected:
        expected.extend(QUERY_TO_CATEGORY["spicy food"])

    return list(dict.fromkeys(expected))


def _recommendation_category(recommendation: dict[str, Any]) -> str:
    """Extract the category field regardless of the caller's naming convention."""
    return str(
        recommendation.get("primary_category")
        or recommendation.get("category")
        or recommendation.get("categories")
        or ""
    ).strip()


def _recommendation_similarity(recommendation: dict[str, Any]) -> float:
    """Extract similarity from either public or internal metric fields."""
    try:
        return float(recommendation.get("similarity_score", recommendation.get("score", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def calculate_precision_at_k(
    recommendations: list[dict[str, Any]], original_query: str, k: int | None = None
) -> dict:
    """Compute Precision@K using category intent and the 0.65 similarity threshold.

    NOTE: This function uses `original_query` for intent/category extraction and
    MUST NOT use any enriched or LLM-modified query for category matching.
    """
    limit = k if k is not None else len(recommendations)
    selected = recommendations[: max(0, limit)]

    expected_categories = expected_categories_for_query(original_query)
    expected_normalized = {category.casefold() for category in expected_categories}

    relevant_count = 0
    for recommendation in selected:
        category = _recommendation_category(recommendation)
        similarity = _recommendation_similarity(recommendation)
        category_matches = not expected_normalized or category.casefold() in expected_normalized
        if similarity >= MIN_RELEVANCE_SIMILARITY and category_matches:
            relevant_count += 1

    denominator = len(selected)
    precision = round(relevant_count / denominator, 4) if denominator else 0.0
    return {
        "precision_at_k": precision,
        "k": denominator,
        "relevant_count": relevant_count,
        "query": original_query,
        "expected_categories": expected_categories,
    }

