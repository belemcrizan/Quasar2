"""Weighted reciprocal-rank fusion of sparse and dense paths."""

from __future__ import annotations

from quasar2.retrieval.base import Retriever, SearchHit


class HybridRetriever:
    def __init__(
        self,
        sparse: Retriever,
        dense: Retriever,
        *,
        sparse_weight: float = 0.6,
        dense_weight: float = 0.4,
        rrf_k: int = 20,
    ) -> None:
        if sparse_weight < 0 or dense_weight < 0 or sparse_weight + dense_weight <= 0:
            raise ValueError("Hybrid weights must be non-negative and not both zero")
        self.sparse = sparse
        self.dense = dense
        total = sparse_weight + dense_weight
        self.sparse_weight = sparse_weight / total
        self.dense_weight = dense_weight / total
        self.rrf_k = rrf_k

    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        pool_size = max(top_k * 3, 10)
        sparse_hits = self.sparse.search(query, top_k=pool_size, domain=domain)
        dense_hits = self.dense.search(query, top_k=pool_size, domain=domain)
        documents = {hit.document.document_id: hit.document for hit in (*sparse_hits, *dense_hits)}
        sparse_by_id = {hit.document.document_id: hit for hit in sparse_hits}
        dense_by_id = {hit.document.document_id: hit for hit in dense_hits}
        raw_scores: dict[str, float] = {}
        for document_id in documents:
            sparse_rank = sparse_by_id.get(document_id)
            dense_rank = dense_by_id.get(document_id)
            raw_scores[document_id] = (
                self.sparse_weight / (self.rrf_k + sparse_rank.rank) if sparse_rank else 0.0
            ) + (
                self.dense_weight / (self.rrf_k + dense_rank.rank) if dense_rank else 0.0
            )
        maximum = max(raw_scores.values(), default=1.0)
        ranked = sorted(raw_scores, key=lambda item: (-raw_scores[item], item))[:top_k]
        return tuple(
            SearchHit(
                document=documents[document_id],
                score=raw_scores[document_id] / maximum,
                rank=rank,
                components={
                    "rrf": raw_scores[document_id],
                    "bm25_rank": float(sparse_by_id[document_id].rank)
                    if document_id in sparse_by_id
                    else 0.0,
                    "dense_rank": float(dense_by_id[document_id].rank)
                    if document_id in dense_by_id
                    else 0.0,
                },
            )
            for rank, document_id in enumerate(ranked, start=1)
        )

