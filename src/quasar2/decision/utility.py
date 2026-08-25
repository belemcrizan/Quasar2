"""Auditable utility terms for ANSWER, EXPLORE, and ASK."""

from __future__ import annotations

from dataclasses import dataclass

from quasar2.models.belief import BeliefState


@dataclass(frozen=True, slots=True)
class UtilityModel:
    wrong_answer_cost: float = 1.4
    exploration_cost: float = 0.10
    ask_cost: float = 0.28

    def evaluate(
        self,
        belief: BeliefState,
        *,
        best_evidence: float,
        discriminative_power: float,
    ) -> tuple[dict[str, float], float]:
        expected_information_gain = (
            belief.normalized_entropy * max(0.0, min(1.0, discriminative_power))
        )
        answer = (
            belief.top_probability
            - self.wrong_answer_cost * (1.0 - belief.top_probability)
            + 0.15 * best_evidence
        )
        explore = expected_information_gain - self.exploration_cost
        # Asking is assumed to resolve much, but not all, ambiguity and has a UX cost.
        ask = 0.75 * (1.0 - belief.top_probability) - self.ask_cost
        return {"ANSWER": answer, "EXPLORE": explore, "ASK": ask}, expected_information_gain

