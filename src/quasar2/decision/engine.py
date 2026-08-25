"""Choose actions using utilities subject to safety/quality gates."""

from __future__ import annotations

from typing import Mapping

from quasar2.decision.utility import UtilityModel
from quasar2.models.belief import BeliefState
from quasar2.models.decision import Action, Decision


class DecisionEngine:
    def __init__(
        self,
        *,
        answer_confidence: float,
        answer_margin: float,
        minimum_evidence: float,
        minimum_exploration_value: float,
        max_explore_rounds: int,
        allow_ask: bool,
        utility_model: UtilityModel,
    ) -> None:
        self.answer_confidence = answer_confidence
        self.answer_margin = answer_margin
        self.minimum_evidence = minimum_evidence
        self.minimum_exploration_value = minimum_exploration_value
        self.max_explore_rounds = max_explore_rounds
        self.allow_ask = allow_ask
        self.utility_model = utility_model

    def decide(
        self,
        belief: BeliefState,
        evidence_support: Mapping[str, float],
        *,
        explore_rounds: int,
        discriminative_power: float,
        exploration_enabled: bool = True,
        ask_enabled: bool | None = None,
    ) -> Decision:
        best_evidence = evidence_support.get(belief.top_hypothesis_id, 0.0)
        utilities, information_gain = self.utility_model.evaluate(
            belief,
            best_evidence=best_evidence,
            discriminative_power=discriminative_power,
        )
        if (
            belief.top_probability >= self.answer_confidence
            and belief.margin >= self.answer_margin
            and best_evidence >= self.minimum_evidence
        ):
            action = Action.ANSWER
            rationale = "answer quality gates passed"
        elif (
            exploration_enabled
            and explore_rounds < self.max_explore_rounds
            and information_gain >= self.minimum_exploration_value
        ):
            action = Action.EXPLORE
            rationale = "uncertainty remains and discriminative retrieval has positive value"
        elif (self.allow_ask if ask_enabled is None else ask_enabled):
            action = Action.ASK
            rationale = "automatic evidence is insufficient; request user disambiguation"
        else:
            action = Action.ANSWER
            rationale = "forced answer because ASK is disabled and exploration is exhausted"
        return Decision(
            action=action,
            selected_hypothesis_id=belief.top_hypothesis_id if action == Action.ANSWER else None,
            utilities=utilities,
            rationale=rationale,
            confidence=belief.top_probability,
            margin=belief.margin,
            expected_information_gain=information_gain,
        )
