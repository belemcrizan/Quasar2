"""First-class failure taxonomy. Labels are descriptive, not causal claims."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

FOUR_WAY = ("BOTH_CORRECT", "OVERTHINKING", "RESCUE", "BOTH_WRONG")

FAILURE_CLASSES = (
    "EASY",
    "OVERTHINKING",
    "RESCUE",
    "UNRESOLVED",
    "WRONG_HYPOTHESIS",
    "WRONG_EVIDENCE",
    "MISSING_EVIDENCE",
    "CONTRADICTORY_EVIDENCE",
    "STALE_EVIDENCE",
    "DUPLICATED_EVIDENCE",
    "PREMATURE_ANSWER",
    "PREMATURE_DEFER",
    "PREMATURE_ASK",
    "USELESS_EXPLORE",
    "USELESS_ANALYZE",
    "BAD_VERIFY",
    "OPEN_SET_FAILURE",
    "GATE_FAILURE",
    "SOURCE_FAILURE",
    "CANDIDATE_MISS",
    "HYPOTHESIS_FLOODING",
    "INFORMATION_OVERLOAD",
    "INFORMATION_STARVATION",
    "BOTH_CORRECT",
    "BOTH_WRONG",
)

FOUR_WAY_SET = frozenset(FOUR_WAY)
FAILURE_CLASS_SET = frozenset(FAILURE_CLASSES)


@dataclass(frozen=True, slots=True)
class FourWayOutcome:
    """Matched FAST vs QUASAR correctness.

    OVERTHINKING: FAST correct AND QUASAR wrong.
    RESCUE: FAST wrong AND QUASAR correct.
    """

    label: str
    fast_correct: bool
    quasar_correct: bool

    def __post_init__(self) -> None:
        if self.label not in FOUR_WAY_SET:
            raise ValueError(f"Unknown four-way class {self.label!r}")


def four_way_class(fast_correct: bool, quasar_correct: bool) -> FourWayOutcome:
    if fast_correct and quasar_correct:
        label = "BOTH_CORRECT"
    elif fast_correct and not quasar_correct:
        label = "OVERTHINKING"
    elif not fast_correct and quasar_correct:
        label = "RESCUE"
    else:
        label = "BOTH_WRONG"
    return FourWayOutcome(label=label, fast_correct=fast_correct, quasar_correct=quasar_correct)


def secondary_failure_labels(row: Mapping[str, object]) -> tuple[str, ...]:
    """Heuristic extra labels. Never replace the four-way class."""

    labels: list[str] = []
    recoverability = str(row.get("recoverability") or "")
    four = str(row.get("four_way_class") or "")
    fast_action = str(row.get("fast_action") or "")
    quasar_action = str(row.get("quasar_action") or "")
    gated_route = str(row.get("gated_route") or row.get("gate_route") or "")
    if recoverability == "OPEN_SET" and four in {"BOTH_WRONG", "OVERTHINKING", "RESCUE"}:
        labels.append("OPEN_SET_FAILURE")
    if four == "BOTH_CORRECT" and recoverability == "CLEAR":
        labels.append("EASY")
    if four == "BOTH_WRONG":
        labels.append("UNRESOLVED")
        if recoverability in {"SOURCE_MISSING", "UNRECOVERABLE_MISSING"}:
            labels.append("INFORMATION_STARVATION")
    if fast_action == "ANSWER" and not bool(row.get("fast_correct")):
        labels.append("PREMATURE_ANSWER")
        labels.append("WRONG_HYPOTHESIS")
    if quasar_action == "DEFER" and four == "OVERTHINKING":
        labels.append("PREMATURE_DEFER")
    if quasar_action == "ASK" and four == "OVERTHINKING":
        labels.append("PREMATURE_ASK")
    if quasar_action == "EXPLORE" and four == "OVERTHINKING":
        labels.append("USELESS_EXPLORE")
    if gated_route == "QUASAR" and four == "OVERTHINKING":
        labels.append("GATE_FAILURE")
    if gated_route == "FAST" and four == "RESCUE":
        labels.append("GATE_FAILURE")
    return tuple(dict.fromkeys(labels))


def primary_failure_class(four_way: str, extras: tuple[str, ...]) -> str:
    if four_way in FOUR_WAY_SET:
        return four_way
    if extras:
        return extras[0]
    return "UNRESOLVED"
