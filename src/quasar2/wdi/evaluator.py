"""Deterministic structured WDI answer evaluator. Hidden truth never enters policy."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    indicator_match: bool
    entity_match: bool
    entity_type_match: bool
    period_match: bool
    unit_match: bool
    status_match: bool
    value_match: bool
    intent_exact: bool
    committed_wrong: bool
    details: Mapping[str, object]


def _finite_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return numeric if math.isfinite(numeric) else None


def _close(left: float | None, right: float | None, *, relative: float, absolute: float) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= max(absolute, relative * max(abs(right), 1.0))


def evaluate_answer(
    predicted: Mapping[str, object], truth: Mapping[str, object]
) -> EvaluationResult:
    acceptable = list(truth.get("acceptable_intents") or ())
    observation = dict(truth.get("expected_observation") or {})
    pred_period = str(predicted.get("period") or predicted.get("disclosed_period") or "")
    pred_status = predicted.get("observation_status")
    raw_value = predicted.get("value")
    if raw_value is None:
        raw_value = predicted.get("value_numeric")
    pred_value = _finite_number(raw_value)

    def period_matches(item: Mapping[str, object]) -> bool:
        wanted = str(item.get("period") or "")
        if wanted == "latest":
            disclosed = str(predicted.get("disclosed_period") or "")
            expected = str(observation.get("period") or "")
            return bool(expected and disclosed) and pred_period == disclosed == expected
        return bool(wanted) and pred_period == wanted

    # Retain field diagnostics, but exactness requires ONE complete acceptable
    # intent. A Cartesian product of individually acceptable fields is not valid.
    matches = [
        (
            item.get("indicator_id") == predicted.get("indicator_id"),
            item.get("entity_code") == predicted.get("entity_code"),
            item.get("entity_type") is None
            or item.get("entity_type") == predicted.get("entity_type"),
            period_matches(item),
            item.get("unit") is None or item.get("unit") == predicted.get("unit"),
        )
        for item in acceptable
    ]
    indicator_match = any(row[0] for row in matches)
    entity_match = any(row[1] for row in matches)
    type_match = any(row[2] for row in matches)
    period_ok = any(row[3] for row in matches)
    unit_match = any(row[4] for row in matches)
    intent_exact = any(all(row) for row in matches)
    status_match = pred_status == observation.get("status")

    if observation.get("status") == "OBSERVED":
        truth_value = _finite_number(observation.get("value"))
        if truth_value is None:
            raise ValueError("OBSERVED ground truth must contain a finite numeric value")
        relative = _finite_number(observation.get("relative_tolerance", 1e-6))
        absolute = _finite_number(observation.get("absolute_tolerance", 0.0))
        if relative is None or absolute is None or min(relative, absolute) < 0:
            raise ValueError("Evaluation tolerances must be finite and non-negative")
        value_match = _close(pred_value, truth_value, relative=relative, absolute=absolute)
    else:
        # Missing/unsupported answers must not fabricate a numeric observation.
        value_match = status_match and raw_value is None
    committed = str(predicted.get("final_action") or "") == "ANSWER"
    committed_wrong = committed and not (intent_exact and status_match and value_match)
    return EvaluationResult(
        indicator_match=indicator_match,
        entity_match=entity_match,
        entity_type_match=type_match,
        period_match=period_ok,
        unit_match=unit_match,
        status_match=status_match,
        value_match=value_match,
        intent_exact=intent_exact,
        committed_wrong=committed_wrong,
        details={"predicted": dict(predicted), "truth_status": observation.get("status")},
    )
