"""Deterministic ANALYZE: recompute beliefs from existing evidence only."""

from __future__ import annotations

import hashlib
import math
from typing import Sequence

from quasar2.v24.state import HypothesisView, PolicyState


def analysis_config_hash(config: str = "v24-analyze-v1") -> str:
    return hashlib.sha256(config.encode("utf-8")).hexdigest()[:16]


def analyze(state: PolicyState, supports: Sequence[tuple[str, float, float]]) -> PolicyState:
    """Update belief scores from (hypothesis_id, support, contradiction) pairs.

    ``supports`` must be derived from evidence already in ``state.evidence_ids``.
    """

    version = hashlib.sha256(
        f"{tuple(sorted(state.evidence_ids))}:{analysis_config_hash()}".encode("utf-8")
    ).hexdigest()
    if version in state.analyzed_versions:
        return state
    by_id = {item[0]: item for item in supports}
    raw: dict[str, float] = {}
    for hyp in state.hypotheses:
        support, contradiction = 0.0, 0.0
        if hyp.hypothesis_id in by_id:
            support, contradiction = by_id[hyp.hypothesis_id][1], by_id[hyp.hypothesis_id][2]
        if hyp.hypothesis_id == "H_unknown":
            raw[hyp.hypothesis_id] = max(0.05, state.unknown_score)
        else:
            raw[hyp.hypothesis_id] = max(1e-6, hyp.belief_score * math.exp(support - contradiction))
    total = sum(raw.values()) or 1.0
    updated = []
    for hyp in state.hypotheses:
        updated.append(
            HypothesisView(
                hypothesis_id=hyp.hypothesis_id,
                indicator_id=hyp.indicator_id,
                entity_code=hyp.entity_code,
                entity_type=hyp.entity_type,
                period=hyp.period,
                unit=hyp.unit,
                belief_score=raw[hyp.hypothesis_id] / total,
                required_slots=hyp.required_slots,
                status=hyp.status,
            )
        )
    ranked = sorted(
        (item for item in updated if item.hypothesis_id != "H_unknown"),
        key=lambda item: (-item.belief_score, item.hypothesis_id),
    )
    margin = 0.0
    if len(ranked) >= 2:
        margin = ranked[0].belief_score - ranked[1].belief_score
    elif ranked:
        margin = ranked[0].belief_score
    entropy = 0.0
    for item in updated:
        p = item.belief_score
        if p > 0:
            entropy -= p * math.log(p)
    unknown = next((item.belief_score for item in updated if item.hypothesis_id == "H_unknown"), 0.0)
    coverage = 0.0
    if ranked:
        filled = sum(1 for slot in ranked[0].required_slots if getattr(ranked[0], slot))
        coverage = filled / max(1, len(ranked[0].required_slots))
    return PolicyState(
        query=state.query,
        language=state.language,
        hypotheses=tuple(updated),
        evidence_ids=state.evidence_ids,
        entropy=entropy,
        margin=margin,
        unknown_score=unknown,
        coverage=coverage,
        contradiction=max((item[2] for item in supports), default=0.0),
        source_available=state.source_available,
        budget=state.budget,
        analyzed_versions=state.analyzed_versions + (version,),
        history=state.history,
    )
