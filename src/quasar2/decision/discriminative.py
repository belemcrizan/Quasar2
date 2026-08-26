"""Discriminative evidence scoring. Not wired into the frozen retrieval loop."""

from __future__ import annotations

import math
from typing import Mapping, Protocol


class DiscriminativeEvidenceScorer(Protocol):
    name: str
    fidelity: str

    def score(
        self,
        document: str,
        hypotheses: Mapping[str, str],
        belief: Mapping[str, float],
        state: Mapping[str, object] | None = None,
    ) -> float:
        ...


class LikelihoodRatioProxyScorer:
    """score(d; Hi, Hj) ≈ log P(tokens(d)|Hi) / P(tokens(d)|Hj) under bag-of-words.

    Diagnostic, not an exact SPRT increment. Fidelity: concept-inspired baseline.
    """

    name = "likelihood_ratio_proxy"
    fidelity = "concept-inspired baseline"

    def score(
        self,
        document: str,
        hypotheses: Mapping[str, str],
        belief: Mapping[str, float],
        state: Mapping[str, object] | None = None,
    ) -> float:
        ranked = sorted(belief, key=lambda hyp: (-float(belief.get(hyp, 0.0)), hyp))
        if len(ranked) < 2:
            return 0.0
        left, right = ranked[0], ranked[1]
        tokens = [token for token in document.lower().split() if token]
        if not tokens:
            return 0.0
        return _smoothed_llr(tokens, hypotheses.get(left, ""), hypotheses.get(right, ""))


class HypothesisScoreDifferenceScorer:
    name = "hypothesis_score_difference"
    fidelity = "concept-inspired baseline"

    def score(
        self,
        document: str,
        hypotheses: Mapping[str, str],
        belief: Mapping[str, float],
        state: Mapping[str, object] | None = None,
    ) -> float:
        ranked = sorted(belief, key=lambda hyp: (-float(belief.get(hyp, 0.0)), hyp))
        if len(ranked) < 2:
            return 0.0
        left, right = ranked[0], ranked[1]
        tokens = set(document.lower().split())
        left_terms = set(hypotheses.get(left, "").lower().split())
        right_terms = set(hypotheses.get(right, "").lower().split())
        return float(len(tokens & left_terms) - len(tokens & right_terms))


class RelevanceScorer:
    """Traditional score(d, q). Contrast class for discrimination experiments."""

    name = "relevance"
    fidelity = "concept-inspired baseline"

    def score(
        self,
        document: str,
        hypotheses: Mapping[str, str],
        belief: Mapping[str, float],
        state: Mapping[str, object] | None = None,
    ) -> float:
        query = ""
        if state and "query" in state:
            query = str(state["query"])
        q_tokens = set(query.lower().split())
        d_tokens = set(document.lower().split())
        if not q_tokens:
            return 0.0
        return len(q_tokens & d_tokens) / len(q_tokens)


def _smoothed_llr(tokens: list[str], text_i: str, text_j: str, *, alpha: float = 0.5) -> float:
    vocab_i = text_i.lower().split()
    vocab_j = text_j.lower().split()
    counts_i: dict[str, int] = {}
    counts_j: dict[str, int] = {}
    for token in vocab_i:
        counts_i[token] = counts_i.get(token, 0) + 1
    for token in vocab_j:
        counts_j[token] = counts_j.get(token, 0) + 1
    vocab = set(counts_i) | set(counts_j) | set(tokens)
    size = max(1, len(vocab))
    total_i = sum(counts_i.values()) + alpha * size
    total_j = sum(counts_j.values()) + alpha * size
    llr = 0.0
    for token in tokens:
        p_i = (counts_i.get(token, 0) + alpha) / total_i
        p_j = (counts_j.get(token, 0) + alpha) / total_j
        llr += math.log(p_i / p_j)
    return llr


def compare_relevance_vs_discrimination(
    documents: list[str],
    query: str,
    hypotheses: Mapping[str, str],
    belief: Mapping[str, float],
    *,
    gold_left: bool,
) -> dict[str, float]:
    """Equal-budget diagnostic: does LLR ranking change 0-1 decision more than relevance?"""

    relevance = RelevanceScorer()
    discriminative = LikelihoodRatioProxyScorer()
    state = {"query": query}
    rel_ranked = sorted(documents, key=lambda doc: -relevance.score(doc, hypotheses, belief, state))
    disc_ranked = sorted(documents, key=lambda doc: -abs(discriminative.score(doc, hypotheses, belief, state)))
    top_rel = rel_ranked[0] if rel_ranked else ""
    top_disc = disc_ranked[0] if disc_ranked else ""
    rel_llr = discriminative.score(top_rel, hypotheses, belief, state)
    disc_llr = discriminative.score(top_disc, hypotheses, belief, state)
    sign = 1.0 if gold_left else -1.0
    return {
        "relevance_top_llr": rel_llr,
        "discriminative_top_llr": disc_llr,
        "delta_llr": abs(disc_llr) - abs(rel_llr),
        "aligned_relevance": 1.0 if rel_llr * sign > 0 else 0.0,
        "aligned_discriminative": 1.0 if disc_llr * sign > 0 else 0.0,
        "recall_unchanged_possible": 1.0,
    }
