"""In-process load probe. Not a claim of production SLO."""

from __future__ import annotations

import json
import statistics
import threading
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def _timed(url: str, *, data: bytes | None = None, timeout: float = 2.0) -> dict[str, Any]:
    started = time.perf_counter()
    error = None
    status = 0
    try:
        req = Request(url, data=data, method="POST" if data else "GET")
        if data:
            req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=timeout) as response:
            status = int(response.status)
            response.read()
    except URLError as exc:
        error = str(exc)
        status = 0
    elapsed = (time.perf_counter() - started) * 1000.0
    return {"ms": elapsed, "status": status, "error": error}


def run_load_test(base: str, *, concurrency: int = 1, n: int = 10, path: str = "/health") -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    lock = threading.Lock()

    def worker() -> None:
        row = _timed(base.rstrip("/") + path)
        with lock:
            results.append(row)

    if concurrency <= 1:
        for _ in range(n):
            worker()
    else:
        remaining = n
        while remaining:
            batch = min(concurrency, remaining)
            threads = [threading.Thread(target=worker) for _ in range(batch)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            remaining -= batch
    times = [row["ms"] for row in results]
    errors = sum(1 for row in results if row["status"] >= 400 or row["error"])
    times_sorted = sorted(times)

    def pct(p: float) -> float:
        if not times_sorted:
            return 0.0
        index = min(len(times_sorted) - 1, max(0, int(round((p / 100.0) * (len(times_sorted) - 1)))))
        return times_sorted[index]

    return {
        "base": base,
        "path": path,
        "n": n,
        "concurrency": concurrency,
        "errors": errors,
        "error_rate": errors / n if n else 0.0,
        "p50_ms": pct(50),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "mean_ms": statistics.mean(times) if times else 0.0,
        "throughput_per_s": (n / (sum(times) / 1000.0)) if times and sum(times) else 0.0,
        "slo_predefined": {"p95_ms": 250.0, "error_rate": 0.05, "concurrency": concurrency},
        "gate_g_scale": "FAIL"
        if errors / n > 0.05 or (times and pct(95) > 250 and path == "/health")
        else "PASS_LOCAL_HEALTH"
        if path == "/health"
        else "TESTED",
        "note": "Local in-process probe. Not a cloud capacity claim.",
    }
