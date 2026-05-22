from statistics import mean
from threading import Lock

import numpy as np

from app.metrics.comparison import load_log, save_log

_LOCK = Lock()


def record_latency(endpoint: str, response_time_ms: float) -> None:
    """Record one endpoint latency sample in milliseconds."""
    clean_endpoint = str(endpoint or "unknown")
    with _LOCK:
        data = load_log()
        data.setdefault("latencies", {})
        data["latencies"].setdefault(clean_endpoint, [])
        data["latencies"][clean_endpoint].append(round(float(response_time_ms), 4))
        save_log(data)


def _stats(latencies: list[float]) -> dict:
    if not latencies:
        return {
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "total_requests": 0,
        }

    return {
        "avg_latency_ms": round(mean(latencies), 4),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 4),
        "min_latency_ms": round(min(latencies), 4),
        "max_latency_ms": round(max(latencies), 4),
        "total_requests": len(latencies),
    }


def get_latency_metrics() -> dict:
    """Return latency summaries for both Task B recommendation endpoints."""
    with _LOCK:
        latencies = load_log().get("latencies", {})

    return {
        "recommend": _stats([float(item) for item in latencies.get("recommend", [])]),
        "cold_start_recommend": _stats([float(item) for item in latencies.get("cold_start_recommend", [])]),
    }

