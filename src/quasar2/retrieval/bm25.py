"""Small, transparent Okapi BM25 implementation."""

from __future__ import annotations

from collections import Counter
import math
from typing import Sequence

from quasar2.retrieval.base import Document, SearchHit, filter_domain
from quasar2.signals.extractor import tokenize


class BM25Retriever:
    def __init__(self, documents: Sequence[Document], *, k1: float = 1.5, b: float = 0.75) -> None:
        if not documents:
            raise ValueError("BM25 requires at least one document")
        self.documents = tuple(documents)
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(document.searchable_text)) for document in documents]
        self.lengths = [sum(counter.values()) for counter in self.term_frequencies]
        self.average_length = sum(self.lengths) / len(self.lengths)
        self.document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            self.document_frequency.update(frequencies.keys())

    def _idf(self, token: str) -> float:
        frequency = self.document_frequency.get(token, 0)
        size = len(self.documents)
        return math.log(1.0 + (size - frequency + 0.5) / (frequency + 0.5))

    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        query_terms = Counter(tokenize(query))
        scores: list[tuple[float, int]] = []
        for index in filter_domain(self.documents, domain):
            frequencies = self.term_frequencies[index]
            length_norm = 1.0 - self.b + self.b * self.lengths[index] / self.average_length
            score = 0.0
            for token, query_frequency in query_terms.items():
                term_frequency = frequencies.get(token, 0)
                if term_frequency == 0:
                    continue
                numerator = term_frequency * (self.k1 + 1.0)
                denominator = term_frequency + self.k1 * length_norm
                score += self._idf(token) * numerator / denominator * min(query_frequency, 2)
            if score > 0:
                scores.append((score, index))
        scores.sort(key=lambda item: (-item[0], self.documents[item[1]].document_id))
        return tuple(
            SearchHit(
                document=self.documents[index],
                score=score,
                rank=rank,
                components={"bm25": score},
            )
            for rank, (score, index) in enumerate(scores[:top_k], start=1)
        )

