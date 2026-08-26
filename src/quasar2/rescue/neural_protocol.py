"""Full-protocol hook for CrossEncoderReranker. Records NOT_RUN when extras are absent."""

from __future__ import annotations

from typing import Any

from quasar2.retrieval.base import SearchHit


def reranker_status() -> dict[str, Any]:
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
    except Exception as error:
        return {
            "status": "NOT_RUN",
            "reason": "sentence-transformers CrossEncoder not importable",
            "detail": str(error),
            "class_present": True,
            "full_protocol_executed": False,
        }
    return {
        "status": "AVAILABLE",
        "reason": "CrossEncoder importable; full N4 sanity cost still opt-in",
        "class_present": True,
        "full_protocol_executed": False,
    }


def maybe_rerank(query: str, hits: tuple[SearchHit, ...], k: int) -> tuple[SearchHit, ...] | None:
    status = reranker_status()
    if status["status"] != "AVAILABLE":
        return None
    from quasar2.retrieval.neural import CrossEncoderReranker

    reranker = CrossEncoderReranker()
    return reranker.rerank(query, hits, k)
