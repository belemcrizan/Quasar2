"""VERIFY uses an independent structured source, never retrieval or ANALYZE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class IndependentSource:
    source_id: str
    trust: float
    independence: float
    claims: Mapping[str, str]


DEFAULT_CATALOG = IndependentSource(
    source_id="sanity_structured_facts_v1",
    trust=0.8,
    independence=1.0,
    claims={
        "cepheid_variable.period_stable": "true",
        "microlensing.single_event": "true",
        "stellar_flare.xray": "true",
        "transit.flat_bottom": "true",
    },
)


@dataclass(frozen=True, slots=True)
class VerifyResult:
    claim: str
    source_id: str
    method: str
    result: str
    confidence: float
    independence: float
    cost: float
    retrieval_calls: int
    decision_changed: bool


def verify_claim(
    claim: str,
    *,
    predicted_id: str,
    source: IndependentSource | None = None,
    cost: float = 0.12,
) -> VerifyResult:
    source = source or DEFAULT_CATALOG
    key = claim if claim in source.claims else f"{predicted_id}.{claim}"
    hit = source.claims.get(claim) or source.claims.get(key)
    if hit is None:
        result = "INCONCLUSIVE"
        confidence = 0.2 * source.trust
        changed = False
    else:
        result = "CONFIRMED" if hit.lower() in {"true", "yes", "1"} else "REFUTED"
        confidence = source.trust * source.independence
        changed = result == "REFUTED"
    return VerifyResult(
        claim=claim,
        source_id=source.source_id,
        method="structured_lookup",
        result=result,
        confidence=confidence,
        independence=source.independence,
        cost=cost,
        retrieval_calls=0,
        decision_changed=changed,
    )


def claim_for_hypothesis(hypothesis_id: str) -> str:
    mapping = {
        "astro.cepheid_variable": "cepheid_variable.period_stable",
        "astro.microlensing": "microlensing.single_event",
        "astro.stellar_flare": "stellar_flare.xray",
        "astro.exoplanet_transit": "transit.flat_bottom",
    }
    return mapping.get(hypothesis_id, f"{hypothesis_id.split('.')[-1]}.observed")
