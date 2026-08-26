"""Canonical public action labels. Frozen v0.1.1 Action remains three-valued."""

from __future__ import annotations

from enum import Enum


class EpistemicAction(str, Enum):
    ANSWER = "ANSWER"
    ANALYZE = "ANALYZE"
    EXPLORE = "EXPLORE"
    ASK = "ASK"
    VERIFY = "VERIFY"
    DEFER = "DEFER"


PUBLIC_ACTIONS = (
    EpistemicAction.ANSWER,
    EpistemicAction.ANALYZE,
    EpistemicAction.EXPLORE,
    EpistemicAction.ASK,
    EpistemicAction.VERIFY,
    EpistemicAction.DEFER,
)

# THINK/SEARCH are internal controller ops and must map to public labels.
INTERNAL_ACTION_MAP = {
    "THINK": EpistemicAction.ANALYZE.value,
    "SEARCH": EpistemicAction.EXPLORE.value,
}

# Default policy does not select VERIFY; existing five-action utilities stay intact.
DEFAULT_POLICY_ACTIONS = (
    EpistemicAction.ANSWER,
    EpistemicAction.ANALYZE,
    EpistemicAction.EXPLORE,
    EpistemicAction.ASK,
    EpistemicAction.DEFER,
)


LEGAL_TRANSITIONS = {
    "OBSERVE": frozenset(DEFAULT_POLICY_ACTIONS),
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
    EpistemicAction.VERIFY: frozenset(
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


def public_action_label(action: str) -> str:
    return INTERNAL_ACTION_MAP.get(action, action)
