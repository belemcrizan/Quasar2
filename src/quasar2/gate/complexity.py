"""Cheap deterministic epistemic complexity gate. No LLM required.

Hypothesis C1: Selective reasoning is more compute-efficient than universal
reasoning. The gate is allowed to fail this hypothesis on matched WDI runs.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Sequence

COMPLEXITY_LABELS = (
    "SIMPLE",
    "AMBIGUOUS",
    "UNDERSPECIFIED",
    "OPEN_SET_RISK",
    "HIGH_RISK",
    "CONTRADICTORY",
    "TEMPORALLY_SENSITIVE",
    "STRUCTURALLY_COMPLEX",
)

ROUTES = ("FAST", "QUASAR", "DEFER_EARLY")

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_TEMPORAL = re.compile(r"\b(latest|lately|now|today|current|recent|yesterday)\b", re.I)
_COMPARE = re.compile(r"\b(vs|versus|compare|compared|rank|ranking|delta|difference|between|trend)\b", re.I)
_HIGH_RISK = re.compile(r"\b(diagnos|medical|clinical|dose|investment advice|credit default)\b", re.I)
_OPEN_SET = re.compile(
    r"\b(bitcoin|crypto|weather|temperature|fifa|stock price|closing price|household income of)\b",
    re.I,
)
_SLOT_HINT = re.compile(r"\b(what|which|how|qual|quando|para)\b", re.I)


@dataclass(frozen=True, slots=True)
class GateConfig:
    fast_complexity_max: float = 0.38
    fast_ambiguity_max: float = 0.42
    fast_margin_min: float = 0.12
    defer_open_set_min: float = 0.72
    estimated_fast_cost: float = 1.0
    estimated_quasar_cost: float = 3.0
    estimated_defer_cost: float = 0.2


@dataclass(frozen=True, slots=True)
class RetrievalSignals:
    scores: tuple[float, ...] = ()
    top_kinds: tuple[str, ...] = ()
    retriever_disagreement: float = 0.0
    open_set_prior: float = 0.0


@dataclass(frozen=True, slots=True)
class GateDecision:
    route: str
    complexity_score: float
    ambiguity_score: float
    open_set_score: float
    reasons: tuple[str, ...]
    estimated_cost: float
    labels: tuple[str, ...]
    top1_score: float = 0.0
    top2_score: float = 0.0
    margin: float = 0.0
    entropy: float = 0.0


def _normalize_scores(scores: Sequence[float]) -> tuple[float, ...]:
    values = [max(0.0, float(score)) for score in scores]
    total = sum(values)
    if total <= 0:
        n = len(values)
        return tuple(1.0 / n for _ in values) if n else ()
    return tuple(item / total for item in values)


def _entropy(probs: Sequence[float]) -> float:
    entropy = 0.0
    for prob in probs:
        if prob > 0:
            entropy -= prob * math.log(prob)
    if len(probs) <= 1:
        return 0.0
    return entropy / math.log(len(probs))


def _token_count(query: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", query))


def evaluate_gate(
    query: str,
    signals: RetrievalSignals | None = None,
    *,
    config: GateConfig | None = None,
) -> GateDecision:
    """Route FAST / QUASAR / DEFER_EARLY from cheap query and probe features."""

    config = config or GateConfig()
    signals = signals or RetrievalSignals()
    reasons: list[str] = []
    labels: list[str] = []
    scores = tuple(signals.scores[:8])
    probs = _normalize_scores(scores)
    entropy = _entropy(probs)
    top1 = scores[0] if scores else 0.0
    top2 = scores[1] if len(scores) > 1 else 0.0
    denom = top1 + top2 if (top1 + top2) > 0 else 1.0
    margin = (top1 - top2) / denom if scores else 0.0
    tokens = _token_count(query)
    missing_year = _YEAR.search(query) is None
    temporally = _TEMPORAL.search(query) is not None
    structural = _COMPARE.search(query) is not None
    high_risk = _HIGH_RISK.search(query) is not None
    open_lex = 1.0 if _OPEN_SET.search(query) else 0.0
    underspec = tokens <= 4 or (missing_year and tokens <= 8)
    if underspec:
        labels.append("UNDERSPECIFIED")
        reasons.append("missing_slots_or_short_query")
    if temporally:
        labels.append("TEMPORALLY_SENSITIVE")
        reasons.append("temporal_language")
    if structural:
        labels.append("STRUCTURALLY_COMPLEX")
        reasons.append("comparison_or_ranking")
    if high_risk:
        labels.append("HIGH_RISK")
        reasons.append("high_risk_lexicon")
    if open_lex or signals.open_set_prior >= 0.5:
        labels.append("OPEN_SET_RISK")
        reasons.append("open_set_lexicon")
    if margin < config.fast_margin_min and scores:
        labels.append("AMBIGUOUS")
        reasons.append("low_retrieval_margin")
    if entropy >= 0.85 and scores:
        labels.append("AMBIGUOUS")
        reasons.append("high_score_entropy")
    if signals.retriever_disagreement >= 0.4:
        labels.append("AMBIGUOUS")
        reasons.append("retriever_disagreement")

    ambiguity = min(
        1.0,
        0.45 * (1.0 - margin)
        + 0.35 * entropy
        + 0.15 * (1.0 if underspec else 0.0)
        + 0.20 * signals.retriever_disagreement,
    )
    open_set_score = min(1.0, max(open_lex, signals.open_set_prior) + 0.15 * (1.0 if not scores else 0.0))
    complexity = min(
        1.0,
        0.30 * ambiguity
        + 0.20 * (1.0 if structural else 0.0)
        + 0.15 * (1.0 if temporally else 0.0)
        + 0.20 * (1.0 if underspec else 0.0)
        + 0.25 * open_set_score
        + 0.20 * (1.0 if high_risk else 0.0)
        + min(0.15, max(0, 12 - tokens) / 40.0),
    )
    if complexity <= config.fast_complexity_max and not labels:
        labels.append("SIMPLE")
        reasons.append("low_complexity")

    if open_set_score >= config.defer_open_set_min and (not scores or margin < 0.05):
        route = "DEFER_EARLY"
        cost = config.estimated_defer_cost
        reasons.append("defer_open_set")
    elif (
        complexity <= config.fast_complexity_max
        and ambiguity <= config.fast_ambiguity_max
        and margin >= config.fast_margin_min
        and not high_risk
        and open_set_score < 0.5
        and not structural
    ):
        route = "FAST"
        cost = config.estimated_fast_cost
        reasons.append("fast_path")
    else:
        route = "QUASAR"
        cost = config.estimated_quasar_cost
        reasons.append("deliberation")

    # Stable unique labels/reasons
    uniq_labels = tuple(dict.fromkeys(labels))
    uniq_reasons = tuple(dict.fromkeys(reasons))
    return GateDecision(
        route=route,
        complexity_score=round(complexity, 6),
        ambiguity_score=round(ambiguity, 6),
        open_set_score=round(open_set_score, 6),
        reasons=uniq_reasons,
        estimated_cost=cost,
        labels=uniq_labels,
        top1_score=top1,
        top2_score=top2,
        margin=round(margin, 6),
        entropy=round(entropy, 6),
    )
