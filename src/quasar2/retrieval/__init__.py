"""Offline retrieval implementations used by the POC."""

from quasar2.retrieval.base import Document, Retriever, SearchHit, load_corpus
from quasar2.retrieval.bm25 import BM25Retriever
from quasar2.retrieval.dense import HashingDenseRetriever
from quasar2.retrieval.factory import ALL_BACKENDS, build_retriever
from quasar2.retrieval.hybrid import HybridRetriever

__all__ = [
    "ALL_BACKENDS",
    "BM25Retriever",
    "Document",
    "HashingDenseRetriever",
    "HybridRetriever",
    "Retriever",
    "SearchHit",
    "build_retriever",
    "load_corpus",
]

