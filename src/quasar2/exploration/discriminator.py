"""Find terms that separate the two most plausible hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from quasar2.models.belief import BeliefState
from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.models.observation import Observation
from quasar2.signals.extractor import tokenize


@dataclass(frozen=True, slots=True)
class DiscriminationPlan:
    hypothesis_ids: tuple[str, ...]
    terms_by_hypothesis: Mapping[str, tuple[str, ...]]
    power: float
    rationale: str


class HypothesisDiscriminator:
    def plan(
        self,
        observation: Observation,
        candidates: Sequence[HypothesisCandidate],
        belief: BeliefState,
    ) -> DiscriminationPlan:
        by_id = {candidate.hypothesis.hypothesis_id: candidate for candidate in candidates}
        ranked_ids = sorted(
            belief.probabilities,
            key=lambda key: (-belief.probabilities[key], key),
        )[:2]
        if len(ranked_ids) == 1:
            only = ranked_ids[0]
            terms = tuple(by_id[only].hypothesis.discriminators[:4])
            return DiscriminationPlan((only,), {only: terms}, 0.0, "only one hypothesis")

        left, right = ranked_ids
        observed = set(observation.tokens)
        left_vocabulary = set(tokenize(" ".join(by_id[left].hypothesis.discriminators)))
        right_vocabulary = set(tokenize(" ".join(by_id[right].hypothesis.discriminators)))
        left_unique = tuple(sorted((left_vocabulary - right_vocabulary) - observed))[:5]
        right_unique = tuple(sorted((right_vocabulary - left_vocabulary) - observed))[:5]
        union = left_vocabulary | right_vocabulary
        separation = len(left_vocabulary ^ right_vocabulary) / max(1, len(union))
        power = separation * belief.normalized_entropy
        return DiscriminationPlan(
            hypothesis_ids=(left, right),
            terms_by_hypothesis={left: left_unique, right: right_unique},
            power=power,
            rationale=f"contrast {by_id[left].hypothesis.label} vs {by_id[right].hypothesis.label}",
        )

