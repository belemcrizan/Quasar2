"""Strong, compatible retrieval baselines for the same corpus and queries."""

from __future__ import annotations

from dataclasses import dataclass
import time

from quasar2.hypotheses.catalog import CatalogHypothesisGenerator
from quasar2.retrieval.base import Retriever, SearchHit
from quasar2.signals.extractor import SignalExtractor


@dataclass(frozen=True, slots=True)
class BaselineResult:
    method: str
    query: str
    predicted_hypothesis_id: str | None
    hits: tuple[SearchHit, ...]
    retrieval_calls: int
    elapsed_ms: float


class DirectRetrievalBaseline:
    def __init__(self, name: str, retriever: Retriever) -> None:
        self.name = name
        self.retriever = retriever

    def run(self, query: str, domain: str, *, top_k: int = 10) -> BaselineResult:
        started = time.perf_counter()
        hits = self.retriever.search(query, top_k=top_k, domain=domain)
        predicted = hits[0].document.hypothesis_ids[0] if hits and hits[0].document.hypothesis_ids else None
        return BaselineResult(
            method=self.name,
            query=query,
            predicted_hypothesis_id=predicted,
            hits=hits,
            retrieval_calls=1,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )


class RewriteHybridBaseline:
    """Single-commitment rewrite followed by hybrid retrieval.

    This is deliberately stronger than a synonym table: it uses the same Mode-A
    catalog to choose one interpretation, then commits to that interpretation in
    a single expanded query.  QUASAR2's claimed mechanism must beat this strong
    compatible baseline, not only raw BM25.
    """

    def __init__(
        self,
        retriever: Retriever,
        extractor: SignalExtractor,
        generator: CatalogHypothesisGenerator,
    ) -> None:
        self.retriever = retriever
        self.extractor = extractor
        self.generator = generator

    def run(self, query: str, domain: str, *, top_k: int = 10) -> BaselineResult:
        started = time.perf_counter()
        observation = self.extractor.extract(query, domain)
        chosen = self.generator.generate(observation, max_candidates=1)[0].hypothesis
        rewritten = " ".join(
            (observation.normalized_query, chosen.label, " ".join(chosen.anchors[:2]))
        )
        hits = self.retriever.search(rewritten, top_k=top_k, domain=domain)
        predicted = hits[0].document.hypothesis_ids[0] if hits and hits[0].document.hypothesis_ids else None
        return BaselineResult(
            method="rewrite_hybrid",
            query=rewritten,
            predicted_hypothesis_id=predicted,
            hits=hits,
            retrieval_calls=1,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )


class MultiQueryBaseline:
    """Single-shot fusion of the original query plus catalog expansions.

    This is a compatible multi-query control, not HyDE.  LLM-HyDE remains an
    optional external baseline when a generator is supplied at experiment time.
    """

    def __init__(
        self,
        retriever: Retriever,
        extractor: SignalExtractor,
        generator: CatalogHypothesisGenerator,
    ) -> None:
        self.retriever = retriever
        self.extractor = extractor
        self.generator = generator

    def run(self, query: str, domain: str, *, top_k: int = 10) -> BaselineResult:
        started = time.perf_counter()
        observation = self.extractor.extract(query, domain)
        candidates = self.generator.generate(observation, max_candidates=3)
        queries = [observation.normalized_query]
        for candidate in candidates[:2]:
            queries.append(
                " ".join((observation.normalized_query, candidate.hypothesis.label))
            )
        pool: dict[str, SearchHit] = {}
        scores: dict[str, float] = {}
        calls = 0
        for variant in queries:
            hits = self.retriever.search(variant, top_k=top_k, domain=domain)
            calls += 1
            for hit in hits:
                document_id = hit.document.document_id
                pool[document_id] = hit
                scores[document_id] = scores.get(document_id, 0.0) + 1.0 / (20 + hit.rank)
        ranked = sorted(scores, key=lambda item: (-scores[item], item))[:top_k]
        hits = tuple(
            SearchHit(
                document=pool[document_id].document,
                score=scores[document_id],
                rank=rank,
                components={"multi_query_rrf": scores[document_id]},
            )
            for rank, document_id in enumerate(ranked, start=1)
        )
        predicted = hits[0].document.hypothesis_ids[0] if hits and hits[0].document.hypothesis_ids else None
        return BaselineResult(
            method="multi_query",
            query=query,
            predicted_hypothesis_id=predicted,
            hits=hits,
            retrieval_calls=calls,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

