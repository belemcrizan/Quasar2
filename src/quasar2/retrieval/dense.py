"""Deterministic dense-vector proxy based on feature hashing.

This is not presented as a neural embedding model.  It gives the POC a dense,
cosine-based retrieval path with no model download, GPU, API key, or network.
The interface can later be backed by sentence-transformers without changing the
pipeline.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import math
from typing import Iterable, Sequence

from quasar2.retrieval.base import Document, SearchHit, filter_domain
from quasar2.signals.extractor import tokenize


SparseVector = dict[int, float]


class HashingDenseRetriever:
    def __init__(self, documents: Sequence[Document], *, dimensions: int = 384) -> None:
        if dimensions < 32:
            raise ValueError("dimensions must be at least 32")
        self.documents = tuple(documents)
        self.dimensions = dimensions
        self.vectors = tuple(self._vectorize(document.searchable_text) for document in documents)

    def _bucket(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        return value % self.dimensions, -1.0 if value & 1 else 1.0

    @staticmethod
    def _features(text: str) -> Iterable[tuple[str, float]]:
        words = tokenize(text)
        for word in words:
            yield f"w:{word}", 1.0
            padded = f"^{word}$"
            for index in range(max(0, len(padded) - 2)):
                yield f"c:{padded[index:index + 3]}", 0.22
        for left, right in zip(words, words[1:]):
            yield f"b:{left}_{right}", 0.35

    def _vectorize(self, text: str) -> SparseVector:
        vector: defaultdict[int, float] = defaultdict(float)
        for feature, weight in self._features(text):
            index, sign = self._bucket(feature)
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        return {index: value / norm for index, value in vector.items()}

    @staticmethod
    def _cosine(left: SparseVector, right: SparseVector) -> float:
        if len(left) > len(right):
            left, right = right, left
        return sum(value * right.get(index, 0.0) for index, value in left.items())

    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        query_vector = self._vectorize(query)
        scores = [
            (max(0.0, self._cosine(query_vector, self.vectors[index])), index)
            for index in filter_domain(self.documents, domain)
        ]
        scores = [item for item in scores if item[0] > 0]
        scores.sort(key=lambda item: (-item[0], self.documents[item[1]].document_id))
        return tuple(
            SearchHit(
                document=self.documents[index],
                score=score,
                rank=rank,
                components={"dense_hash": score},
            )
            for rank, (score, index) in enumerate(scores[:top_k], start=1)
        )

