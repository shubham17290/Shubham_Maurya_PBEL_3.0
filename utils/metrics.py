"""Tiny in-process metrics store (single worker)."""

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters = defaultdict(int)
_latencies = defaultdict(list)


def inc(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] += amount


def observe(name: str, value: float) -> None:
    with _lock:
        _latencies[name].append(value)
        # keep last 1000
        if len(_latencies[name]) > 1000:
            del _latencies[name][: len(_latencies[name]) - 1000]


def snapshot() -> dict:
    with _lock:
        out = {"counters": dict(_counters)}
        out["latencies"] = {
            k: {
                "count": len(v),
                "avg": (sum(v) / len(v)) if v else 0.0,
                "max": max(v) if v else 0.0,
            }
            for k, v in _latencies.items()
        }
        return out