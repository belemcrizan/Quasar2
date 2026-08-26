"""ANALYZE / ASK / DEFER experiments independent of the frozen loop."""

from __future__ import annotations

from typing import Sequence

from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.rescue.belief import DiscriminativeBeliefUpdater
from quasar2.rescue.pipeline import RescuePipeline


def analyze_only(
    pipeline: RescuePipeline,
    query: str,
    domain: str,
    *,
    extra_rounds: int = 2,
) -> dict[str, object]:
    """All evidence is fetched once; ANALYZE may only re-update belief."""

    fast = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
    updater = DiscriminativeBeliefUpdater(
        evidence_strength=pipeline.disc_updater.evidence_strength,
        temperature=pipeline.disc_updater.temperature,
        probability_floor=pipeline.disc_updater.probability_floor,
    )
    belief = fast.belief
    by_hid: dict[str, list] = {}
    for item in fast.evidence:
        by_hid.setdefault(item.hypothesis_id, []).append(item)
    from quasar2.models.evidence import EvidenceBundle

    bundles = [
        EvidenceBundle(
            hypothesis_id=hid,
            items=tuple(items),
            aggregate_support=max((item.support_score for item in items), default=0.0),
            novel_item_count=len(items),
        )
        for hid, items in by_hid.items()
    ]
    entropy_before = belief.normalized_entropy
    predicted_before = belief.top_hypothesis_id
    for round_index in range(1, extra_rounds + 1):
        belief = updater.update(belief, bundles, round_index=round_index)
    return {
        "predicted_before": predicted_before,
        "predicted_after": belief.top_hypothesis_id,
        "entropy_before": entropy_before,
        "entropy_after": belief.normalized_entropy,
        "evidence_ids_before": sorted({item.document_id for item in fast.evidence}),
        "evidence_ids_after": sorted({item.document_id for item in fast.evidence}),
        "retrieval_calls": fast.retrieval_calls,
        "analyze_added_retrieval": 0,
        "changed_prediction": predicted_before != belief.top_hypothesis_id,
    }


def ask_simulator(
    *,
    candidates: Sequence[HypothesisCandidate],
    gold_id: str,
    noise: float,
    seed: int,
) -> str | None:
    """Oracle user simulator (evaluation only). Not a deployment component."""

    import random

    rng = random.Random(seed)
    ids = [c.hypothesis.hypothesis_id for c in candidates]
    if gold_id not in ids:
        return None
    if rng.random() < noise:
        others = [hid for hid in ids if hid != gold_id]
        return others[0] if others else None
    return gold_id


def defer_should_fire(*, entropy: float, unknown_mass: float, top_generation: float) -> bool:
    return unknown_mass >= 0.4 or (entropy >= 0.9 and top_generation < 0.05)


def open_set_query_pack() -> tuple[tuple[str, str], ...]:
    """Queries whose true need is outside the astronomy/AI catalogs."""

    return (
        ("please reset the billing SKU for tenant 7f3", "astronomy"),
        ("how do I file a tax extension for a deceased spouse", "ai"),
        ("calibrate the espresso pump pressure after descaling", "astronomy"),
    )
