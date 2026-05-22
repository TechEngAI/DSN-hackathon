import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from threading import Lock

LOG_PATH = Path(__file__).resolve().parents[1] / "recommendation_log.json"
_LOCK = Lock()


def _empty_log() -> dict:
    return {"sessions": [], "latencies": {}}


def ensure_log() -> None:
    """Create the shared recommendation log on first use."""
    if not LOG_PATH.exists():
        LOG_PATH.write_text(json.dumps(_empty_log(), indent=2), encoding="utf-8")


def load_log() -> dict:
    ensure_log()
    try:
        data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = _empty_log()
    data.setdefault("sessions", [])
    data.setdefault("latencies", {})
    return data


def save_log(data: dict) -> None:
    data.setdefault("sessions", [])
    data.setdefault("latencies", {})
    LOG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def log_recommendation_session(
    user_id: str,
    is_cold_start: bool,
    query: str,
    location: str | None,
    similarity_scores: list[float],
    recommendation_count: int,
    precision_at_k: dict | None = None,
    enriched_query: str | None = None,
) -> None:
    """Append one recommendation session for warm-vs-cold comparison."""
    clean_scores = []
    for score in similarity_scores:
        if score is None:
            continue
        value = float(score)
        if value > 1.0:
            value = 1.0 / (1.0 + (value / 4.0))
        clean_scores.append(value)
    avg_similarity = round(mean(clean_scores), 4) if clean_scores else 0.0
    if clean_scores and avg_similarity < 0.5 and all(score < 0.5 for score in clean_scores):
        print(
            "[METRICS WARNING] avg_similarity suspiciously low: "
            f"{avg_similarity:.4f}. Check if raw distances are being passed."
        )
    session = {
        "user_id": user_id,
        "is_cold_start": bool(is_cold_start),
        "query": query,
        "enriched_query": enriched_query,
        "location": location,
        "avg_similarity_score": avg_similarity,
        "recommendation_count": int(recommendation_count or 0),
        "precision_at_k": precision_at_k,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    with _LOCK:
        data = load_log()
        data["sessions"].append(session)
        save_log(data)


def _summary_for_sessions(sessions: list[dict]) -> dict:
    quality_sessions = [item for item in sessions if int(item.get("recommendation_count", 0) or 0) > 0]
    if not quality_sessions:
        return {"avg_similarity": 0.0, "avg_recommendation_count": 0.0, "total_sessions": 0}

    return {
        "avg_similarity": round(mean(float(item.get("avg_similarity_score", 0.0)) for item in quality_sessions), 4),
        "avg_recommendation_count": round(mean(int(item.get("recommendation_count", 0)) for item in quality_sessions), 4),
        "total_sessions": len(quality_sessions),
    }


def get_cold_start_vs_warm() -> dict:
    """Compare aggregate quality for warm and cold-start sessions."""
    with _LOCK:
        sessions = load_log().get("sessions", [])

    warm_sessions = [item for item in sessions if not item.get("is_cold_start")]
    cold_sessions = [item for item in sessions if item.get("is_cold_start")]
    warm = _summary_for_sessions(warm_sessions)
    cold = _summary_for_sessions(cold_sessions)
    return {
        "warm_users": warm,
        "cold_start_users": cold,
        "quality_gap": round(warm["avg_similarity"] - cold["avg_similarity"], 4),
    }


def get_latest_precision() -> dict:
    """Return the most recent logged Precision@K metric, or zeros."""
    with _LOCK:
        sessions = load_log().get("sessions", [])

    for session in reversed(sessions):
        precision = session.get("precision_at_k")
        if precision:
            return precision
    return {"precision_at_k": 0.0, "k": 0, "relevant_count": 0, "query": ""}
