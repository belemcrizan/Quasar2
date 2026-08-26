"""Separate relevance from discrimination. Disc is a heuristic, not exact EIG."""

from __future__ import annotations

from typing import Sequence

from quasar2.models.hypothesis import Hypothesis
from quasar2.retrieval.base import Document, SearchHit
from quasar2.signals.extractor import tokenize


def lexical_support(document: Document, hypothesis: Hypothesis, query: str) -> float:
    doc_tokens = set(tokenize(document.searchable_text))
    query_tokens = set(tokenize(query))
    hyp_tokens = set(tokenize(" ".join(hypothesis.anchors + hypothesis.discriminators + (hypothesis.label,))))
    if not doc_tokens:
        return 0.0
    rel = len(doc_tokens & query_tokens) / max(1, len(query_tokens))
    hyp = len(doc_tokens & hyp_tokens) / max(1, len(hyp_tokens))
    foreign = bool(document.hypothesis_ids) and hypothesis.hypothesis_id not in document.hypothesis_ids
    return max(0.0, 0.45 * rel + 0.55 * hyp - 0.25 * float(foreign))


def discrimination(document: Document, left: Hypothesis, right: Hypothesis, query: str) -> float:
    return lexical_support(document, left, query) - lexical_support(document, right, query)


def novelty(document: Document, seen_ids: Sequence[str]) -> float:
    return 0.0 if document.document_id in set(seen_ids) else 1.0


def composite_score(
    document: Document,
    query: str,
    left: Hypothesis,
    right: Hypothesis | None,
    *,
    retrieval_score: float,
    seen_ids: Sequence[str],
    alpha: float = 0.35,
    beta: float = 0.45,
    gamma: float = 0.20,
    delta: float = 0.05,
    cost: float = 1.0,
) -> float:
    rel = max(0.0, min(1.0, retrieval_score))
    disc = discrimination(document, left, right, query) if right is not None else 0.0
    nov = novelty(document, seen_ids)
    return alpha * rel + beta * disc + gamma * nov - delta * cost


def rerank_hits(
    hits: Sequence[SearchHit],
    query: str,
    left: Hypothesis,
    right: Hypothesis | None,
    *,
    seen_ids: Sequence[str],
    top_k: int,
) -> tuple[SearchHit, ...]:
    scored = []
    for hit in hits:
        score = composite_score(
            hit.document,
            query,
            left,
            right,
            retrieval_score=hit.score,
            seen_ids=seen_ids,
        )
        scored.append((score, hit))
    scored.sort(key=lambda item: (-item[0], item[1].document.document_id))
    return tuple(
        SearchHit(
            document=item[1].document,
            score=item[0],
            rank=rank,
            components={**dict(item[1].components), "disc_composite": item[0]},
        )
        for rank, item in enumerate(scored[:top_k], start=1)
    )


def approx_eig_score(belief_entropy: float, disc_abs: float) -> float:
    """Entropy-weighted |Disc| proxy. Not exact expected information gain."""

    return max(0.0, belief_entropy) * max(0.0, disc_abs)
