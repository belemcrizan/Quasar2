"""ASK generates a specific clarification from competing hypotheses. No gold fields."""

from __future__ import annotations

from typing import Sequence

from quasar2.aera.security import sanitize_ask
from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.rescue.leakage import LeakageError, assert_no_gold_fields


ASK_TYPES = (
    "entity",
    "time",
    "scope",
    "unit",
    "location",
    "preference",
    "discriminant_attribute",
    "hypothesis_confirmation",
)


def interaction_cost(*, history_asks: int, stakes: float = 1.0, fatigue_step: float = 0.08) -> float:
    return 0.28 + fatigue_step * history_asks + 0.05 * max(0.0, stakes - 1.0)


def candidate_questions(
    query: str,
    candidates: Sequence[HypothesisCandidate],
    *,
    history_asks: int = 0,
) -> list[dict[str, object]]:
    assert_no_gold_fields({"query": query}, context="ask")
    ranked = sorted(candidates, key=lambda item: (-item.generation_score, item.hypothesis.hypothesis_id))
    if len(ranked) < 2:
        question = sanitize_ask(f"Which catalog interpretation matches: {query}?")
        return [
            {
                "type": "hypothesis_confirmation",
                "question": question,
                "voi_proxy": 0.05,
                "cost": interaction_cost(history_asks=history_asks),
                "net": 0.05 - interaction_cost(history_asks=history_asks),
            }
        ]
    left, right = ranked[0].hypothesis, ranked[1].hypothesis
    disc_left = left.discriminators[:3] or left.anchors[:2]
    disc_right = right.discriminators[:3] or right.anchors[:2]
    specs = (
        (
            "discriminant_attribute",
            f"Did you observe {' / '.join(disc_left) or left.label} rather than "
            f"{' / '.join(disc_right) or right.label}?",
            0.45,
        ),
        ("entity", f"Is the target closer to {left.label} or {right.label}?", 0.35),
        ("time", "Is the timescale seconds, hours, or periodic over days?", 0.20),
        ("scope", "Is this about one object, a class, or an instrument pipeline?", 0.15),
    )
    rows: list[dict[str, object]] = []
    cost = interaction_cost(history_asks=history_asks)
    for qtype, text, voi in specs:
        question = sanitize_ask(text)
        rows.append({"type": qtype, "question": question, "voi_proxy": voi, "cost": cost, "net": voi - cost})
    rows.sort(key=lambda row: (-float(row["net"]), str(row["type"])))
    return rows


def select_ask(
    query: str,
    candidates: Sequence[HypothesisCandidate],
    *,
    history_asks: int = 0,
) -> dict[str, object]:
    rows = candidate_questions(query, candidates, history_asks=history_asks)
    chosen = rows[0]
    if "gold" in str(chosen["question"]).lower() or "correct_hypothesis" in str(chosen["question"]):
        raise LeakageError("ASK question leaked gold vocabulary")
    return chosen
