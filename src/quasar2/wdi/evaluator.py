"""Deterministic structured WDI answer evaluator. Hidden truth never enters policy."""

from __future__ import annotations

from dataclasses import dataclass
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


def _close(left: float | None, right: float | None, *, relative: float, absolute: float) -> bool:
    if left is None or right is None:
        return left is right
    scale = max(abs(right), 1.0)
    return abs(left - right) <= max(absolute, relative * scale)


def evaluate_answer(predicted: Mapping[str, object], truth: Mapping[str, object]) -> EvaluationResult:
    acceptable = list(truth.get("acceptable_intents") or ())
    observation = dict(truth.get("expected_observation") or {})
    pred_indicator = predicted.get("indicator_id")
    pred_entity = predicted.get("entity_code")
    pred_type = predicted.get("entity_type")
    pred_period = str(predicted.get("period") or predicted.get("disclosed_period") or "")
    pred_unit = predicted.get("unit")
    pred_status = predicted.get("observation_status")
    pred_value = predicted.get("value")
    if pred_value is None:
        pred_value = predicted.get("value_numeric")
    if pred_value is not None:
        try:
            pred_value = float(pred_value)
        except (TypeError, ValueError):
            pred_value = None

    indicator_match = any(item.get("indicator_id") == pred_indicator for item in acceptable) if acceptable else False
    entity_match = any(item.get("entity_code") == pred_entity for item in acceptable) if acceptable else False
    type_match = any(item.get("entity_type") == pred_type for item in acceptable) if acceptable else pred_type is None
    period_ok = False
    for item in acceptable:
        wanted = str(item.get("period") or "")
        if wanted == "latest":
            period_ok = bool(predicted.get("disclosed_period")) and pred_period == str(predicted.get("disclosed_period"))
        else:
            period_ok = period_ok or pred_period == wanted
    unit_match = any((item.get("unit") in {None, pred_unit}) for item in acceptable) if acceptable else True
    status_match = pred_status == observation.get("status")
    truth_value = observation.get("value")
    relative = float(observation.get("relative_tolerance") or 1e-6)
    absolute = float(observation.get("absolute_tolerance") or 0.0)
    value_match = _close(
        pred_value if isinstance(pred_value, float) else None,
        float(truth_value) if truth_value is not None else None,
        relative=relative,
        absolute=absolute,
    ) if observation.get("status") == "OBSERVED" else pred_status == observation.get("status")
    intent_exact = indicator_match and entity_match and period_ok
    committed = str(predicted.get("final_action") or "") == "ANSWER"
    committed_wrong = committed and not (intent_exact and status_match and (value_match or observation.get("status") != "OBSERVED"))
    return EvaluationResult(
        indicator_match=indicator_match,
        entity_match=entity_match,
        entity_type_match=bool(type_match),
        period_match=period_ok,
        unit_match=bool(unit_match),
        status_match=bool(status_match),
        value_match=bool(value_match),
        intent_exact=intent_exact,
        committed_wrong=committed_wrong,
        details={
            "predicted": dict(predicted),
            "truth_status": observation.get("status"),
        },
    )
