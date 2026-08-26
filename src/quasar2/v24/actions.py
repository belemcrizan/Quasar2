"""V2.4 five-action vocabulary. Frozen v0.1.1 Action remains three-valued."""

from __future__ import annotations

from enum import Enum


class EpistemicAction(str, Enum):
    ANSWER = "ANSWER"
    ANALYZE = "ANALYZE"
    EXPLORE = "EXPLORE"
    ASK = "ASK"
    DEFER = "DEFER"


LEGAL_TRANSITIONS = {
    "OBSERVE": frozenset(EpistemicAction),
    EpistemicAction.ANALYZE: frozenset(
        {EpistemicAction.ANSWER, EpistemicAction.EXPLORE, EpistemicAction.ASK, EpistemicAction.DEFER}
    ),
    EpistemicAction.EXPLORE: frozenset(
        {
            EpistemicAction.ANALYZE,
            EpistemicAction.ANSWER,
            EpistemicAction.EXPLORE,
            EpistemicAction.ASK,
            EpistemicAction.DEFER,
        }
    ),
    EpistemicAction.ASK: frozenset(
        {
            EpistemicAction.ANALYZE,
            EpistemicAction.EXPLORE,
            EpistemicAction.ANSWER,
            EpistemicAction.ASK,
            EpistemicAction.DEFER,
        }
    ),
    EpistemicAction.ANSWER: frozenset(),
    EpistemicAction.DEFER: frozenset(),
}

FORBIDDEN_POLICY_FIELDS = frozenset(
    {
        "canonical_intent",
        "canonical_intent_id",
        "acceptable_intents",
        "expected_action",
        "degradation_level",
        "degradation_factors",
        "recoverability_label",
        "recoverability",
        "ground_truth",
        "ground_truth_indicator",
        "ground_truth_value",
        "simulator_state",
        "partition_metadata",
        "test_partition_metadata",
        "expected_observation",
    }
)
