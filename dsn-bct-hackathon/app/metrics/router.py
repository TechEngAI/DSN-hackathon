from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.metrics.comparison import get_cold_start_vs_warm, get_latest_precision
from app.metrics.coverage import get_coverage
from app.metrics.latency import get_latency_metrics
from app.metrics.precision import calculate_precision_at_k
from app.startup import app_state

router = APIRouter(tags=["Task B Metrics"])


class PrecisionRequest(BaseModel):
    query: str
    recommendations: list[dict[str, Any]]


def _total_businesses() -> int:
    """Read the ChromaDB collection count, returning zero if unavailable."""
    vector_store = app_state.get("vector_store")
    if vector_store is None:
        return 0
    try:
        return int(vector_store.get_collection_count())
    except Exception:
        return 0


@router.get("/metrics")
def metrics() -> dict:
    """Expose all Task B evaluation metrics in one response."""
    return {
        "precision_at_k": get_latest_precision(),
        "coverage": get_coverage(_total_businesses()),
        "cold_start_vs_warm": get_cold_start_vs_warm(),
        "latency": get_latency_metrics(),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.post("/metrics/precision")
def precision(request: PrecisionRequest) -> dict:
    """Compute Precision@K for a supplied recommendation list."""
    return calculate_precision_at_k(
        request.recommendations,
        request.query,
    )
