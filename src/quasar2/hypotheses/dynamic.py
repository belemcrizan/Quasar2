"""Mode B boundary for an LLM or knowledge-base hypothesis backend.

Mode B is intentionally dependency-injected: the POC never sends data to an
external model by itself.  A backend must return typed hypotheses, and this
adapter applies domain validation, deduplication, and deterministic ranking.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from quasar2.models.hypothesis import Hypothesis, HypothesisCandidate
from quasar2.models.observation import Observation


class DynamicHypothesisBackend(Protocol):
    def propose(self, observation: Observation, limit: int) -> Sequence[Hypothesis]:
        ...


class DynamicHypothesisGenerator:
    def __init__(self, backend: DynamicHypothesisBackend) -> None:
        self.backend = backend

    def generate(
        self, observation: Observation, *, max_candidates: int
    ) -> tuple[HypothesisCandidate, ...]:
        proposals = self.backend.propose(observation, max_candidates)
        accepted: list[HypothesisCandidate] = []
        seen: set[str] = set()
        for hypothesis in proposals:
            if hypothesis.domain != observation.domain or hypothesis.hypothesis_id in seen:
                continue
            seen.add(hypothesis.hypothesis_id)
            accepted.append(
                HypothesisCandidate(
                    hypothesis=hypothesis,
                    generation_score=max(0.0, 1.0 - 0.1 * len(accepted)),
                    rank=len(accepted) + 1,
                    rationale="validated dynamic proposal",
                )
            )
            if len(accepted) == max_candidates:
                break
        if not accepted:
            raise ValueError("Dynamic backend returned no valid hypotheses")
        return tuple(accepted)

