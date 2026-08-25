"""Build autonomous follow-up retrieval queries from a discrimination plan."""

from __future__ import annotations

from quasar2.exploration.discriminator import DiscriminationPlan
from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.models.observation import Observation


class Explorer:
    def build_queries(
        self,
        observation: Observation,
        candidates: tuple[HypothesisCandidate, ...],
        plan: DiscriminationPlan,
    ) -> dict[str, str]:
        by_id = {candidate.hypothesis.hypothesis_id: candidate for candidate in candidates}
        queries: dict[str, str] = {}
        for hypothesis_id in plan.hypothesis_ids:
            hypothesis = by_id[hypothesis_id].hypothesis
            discriminators = " ".join(plan.terms_by_hypothesis.get(hypothesis_id, ()))
            queries[hypothesis_id] = " ".join(
                part
                for part in (
                    observation.normalized_query,
                    hypothesis.label,
                    "discriminating evidence",
                    discriminators,
                )
                if part
            )
        return queries

