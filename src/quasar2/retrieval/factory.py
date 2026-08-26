"""Build named retrieval backends without changing the inference loop."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from quasar2.retrieval.base import Document, Retriever
from quasar2.retrieval.bm25 import BM25Retriever
from quasar2.retrieval.dense import HashingDenseRetriever
from quasar2.retrieval.hybrid import HybridRetriever

DEBUG_BACKENDS = frozenset({"bm25", "dense", "dense_hash", "hybrid"})
SCIENTIFIC_BACKENDS = frozenset({"neural", "hybrid_neural", "e5", "bge-m3", "hybrid_bge"})
ALL_BACKENDS = DEBUG_BACKENDS | SCIENTIFIC_BACKENDS


def build_retriever(
    documents: Sequence[Document],
    backend: str = "hybrid",
    retrieval: Mapping[str, Any] | None = None,
) -> Retriever:
    """Return a retriever implementing the shared ``search`` protocol.

    ``dense`` / ``dense_hash`` are the hashing cosine proxy (CI / debug).
    ``neural`` is sentence-transformers and is optional.
    """

    settings = dict(retrieval or {})
    name = backend.strip().lower()
    if name not in ALL_BACKENDS:
        raise ValueError(f"Unknown retrieval backend {backend!r}; choose from {sorted(ALL_BACKENDS)}")
    sparse = BM25Retriever(documents)
    hashing = HashingDenseRetriever(
        documents, dimensions=int(settings.get("dense_dimensions", 384))
    )
    if name in {"bm25"}:
        return sparse
    if name in {"dense", "dense_hash"}:
        return hashing
    if name == "hybrid":
        return HybridRetriever(
            sparse,
            hashing,
            sparse_weight=float(settings.get("bm25_weight", 0.6)),
            dense_weight=float(settings.get("dense_weight", 0.4)),
            rrf_k=int(settings.get("rrf_k", 20)),
        )
    from quasar2.retrieval.neural import NeuralDenseRetriever

    profile = "minilm"
    if name == "e5":
        profile = "e5"
    elif name in {"bge-m3", "hybrid_bge"}:
        profile = "bge-m3"
    elif name in {"neural", "hybrid_neural"}:
        profile = "minilm"
    neural = NeuralDenseRetriever(
        documents,
        model_name=str(settings.get("neural_model") or {
            "e5": "intfloat/multilingual-e5-base",
            "bge-m3": "BAAI/bge-m3",
            "hybrid_bge": "BAAI/bge-m3",
        }.get(name, "sentence-transformers/all-MiniLM-L6-v2")),
        device=str(settings.get("neural_device", "cpu")),
        profile=profile,
        cache_dir=settings.get("neural_cache_dir"),
    )
    if name in {"neural", "e5", "bge-m3"}:
        return neural
    return HybridRetriever(
        sparse,
        neural,
        sparse_weight=float(settings.get("bm25_weight", 0.6)),
        dense_weight=float(settings.get("dense_weight", 0.4)),
        rrf_k=int(settings.get("rrf_k", 20)),
    )


def backend_for_method(method: str) -> str | None:
    """Return the retrieval backend for a matched method name, if any."""

    if method.startswith("full+"):
        return method.split("+", 1)[1]
    if method in {"bm25", "dense", "dense_hash", "hybrid", "neural", "hybrid_neural", "e5", "bge-m3", "hybrid_bge"}:
        return "dense_hash" if method == "dense" else method
    if method in {"rewrite_hybrid", "rewrite", "multi_query"}:
        return "hybrid"
    if method in {"full", "noHyp", "noExplore", "noUpdate", "noAsk"}:
        return "hybrid"
    return None
