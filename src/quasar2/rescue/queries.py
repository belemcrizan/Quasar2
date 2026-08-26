"""Deployment-valid discriminative query construction. Never takes H*."""

from __future__ import annotations

from typing import Sequence

from quasar2.models.belief import BeliefState
from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.models.observation import Observation
from quasar2.rescue.leakage import FORBIDDEN_DEPLOYMENT_FIELDS, LeakageError
from quasar2.signals.extractor import tokenize


def _ranked_ids(belief: BeliefState, limit: int = 2) -> tuple[str, ...]:
    ordered = sorted(belief.probabilities, key=lambda key: (-belief.probabilities[key], key))
    return tuple(ordered[:limit])


def build_discriminative_queries(
    observation: Observation,
    candidates: Sequence[HypothesisCandidate],
    belief: BeliefState,
    *,
    seen_document_ids: Sequence[str] = (),
) -> dict[str, str]:
    """Build contrast / falsification / difference queries from observables only.

    Inputs may include the observed query, predicted hypotheses, current belief,
    and already-seen document ids. Gold labels are rejected if smuggled in
    observation.metadata.
    """

    metadata = dict(observation.metadata)
    leak = FORBIDDEN_DEPLOYMENT_FIELDS.intersection(metadata)
    if leak:
        raise LeakageError(f"query builder received gold metadata {sorted(leak)}")
    by_id = {candidate.hypothesis.hypothesis_id: candidate.hypothesis for candidate in candidates}
    ranked = [hid for hid in _ranked_ids(belief, 2) if hid in by_id]
    queries: dict[str, str] = {}
    q = observation.normalized_query
    if len(ranked) < 2:
        hid = ranked[0] if ranked else next(iter(by_id))
        hyp = by_id[hid]
        queries["relevance"] = q
        queries["hypothesis"] = " ".join((q, hyp.label, " ".join(hyp.discriminators[:4])))
        return queries
    left, right = ranked
    hi, hj = by_id[left], by_id[right]
    left_terms = set(tokenize(" ".join(hi.discriminators)))
    right_terms = set(tokenize(" ".join(hj.discriminators)))
    observed = set(observation.tokens)
    plus = " ".join(sorted((left_terms - right_terms) - observed)[:5])
    minus = " ".join(sorted((right_terms - left_terms) - observed)[:5])
    delta = " ".join(sorted((left_terms ^ right_terms) - observed)[:6])
    queries["pairwise_plus"] = " ".join(
        part for part in (q, "evidence favoring", hi.label, "over", hj.label, plus) if part
    )
    queries["falsification"] = " ".join(
        part for part in (q, "evidence that would falsify", hi.label, minus) if part
    )
    queries["contrast"] = " ".join(part for part in (q, "observable differences", delta) if part)
    if seen_document_ids:
        queries["novelty_hint"] = q
    return queries
