import json
from pathlib import Path
from threading import Lock

STORE_PATH = Path(__file__).resolve().parents[1] / "coverage_store.json"
_LOCK = Lock()


def _ensure_store() -> None:
    """Create the coverage store on first use."""
    if not STORE_PATH.exists():
        STORE_PATH.write_text(json.dumps({"recommended_ids": []}, indent=2), encoding="utf-8")


def _load_ids() -> set[str]:
    _ensure_store()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {"recommended_ids": []}
    return {str(item_id) for item_id in data.get("recommended_ids", []) if item_id}


def _save_ids(recommended_ids: set[str]) -> None:
    STORE_PATH.write_text(
        json.dumps({"recommended_ids": sorted(recommended_ids)}, indent=2),
        encoding="utf-8",
    )


def track_coverage(recommendation_ids: list[str]) -> None:
    """Persist every recommended business id for coverage calculations."""
    clean_ids = {str(item_id).strip() for item_id in recommendation_ids if str(item_id or "").strip()}
    if not clean_ids:
        return

    with _LOCK:
        recommended_ids = _load_ids()
        recommended_ids.update(clean_ids)
        _save_ids(recommended_ids)


def get_coverage(total_businesses_in_dataset: int) -> dict:
    """Return the fraction of indexed businesses recommended at least once."""
    with _LOCK:
        recommended_ids = _load_ids()

    total = max(0, int(total_businesses_in_dataset or 0))
    coverage = round(len(recommended_ids) / total, 4) if total else 0.0
    return {
        "coverage": coverage,
        "unique_businesses_recommended": len(recommended_ids),
        "total_businesses_in_dataset": total,
    }

