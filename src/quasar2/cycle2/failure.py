"""Scientific failure taxonomy for cycle-2 attribution."""

from __future__ import annotations

from typing import Mapping

LAYER_FAILURES = (
    "uncertainty_estimation_failure",
    "recoverability_estimation_failure",
    "observation_model_mismatch",
    "action_value_estimation_failure",
    "policy_selection_failure",
    "retrieval_failure",
    "evidence_failure",
    "open_set_failure",
    "cost_model_failure",
    "near_tie",
    "anti_quasar_expected_simple_behavior",
)


def classify_policy_error(row: Mapping[str, object], selected: str, optimal: str) -> tuple[str, ...]:
    labels: list[str] = []
    if selected == optimal:
        if row.get("anti_quasar") and selected in {"ANSWER", "DEFER"}:
            labels.append("anti_quasar_expected_simple_behavior")
        return tuple(labels)
    if row.get("near_tie"):
        labels.append("near_tie")
    if row.get("open_set") and selected == "ANSWER":
        labels.append("open_set_failure")
    if not row.get("proxy_matches_true") and selected != optimal:
        labels.append("observation_model_mismatch")
    abs_err = row.get("abs_error_R")
    if isinstance(abs_err, (int, float)) and abs_err > 0.25:
        labels.append("recoverability_estimation_failure")
    if selected == "EXPLORE" and float(row.get("tau_explore_net") or 0.0) <= 0.0:
        labels.append("action_value_estimation_failure")
    if selected != optimal:
        labels.append("policy_selection_failure")
    explore_cost = float(row.get("explore_cost") or 0.0)
    if explore_cost >= 0.4 and selected == "EXPLORE":
        labels.append("cost_model_failure")
    return tuple(dict.fromkeys(labels))


def regret_decomposition(rows: list[Mapping[str, object]]) -> dict[str, float]:
    """Diagnostic attribution. Not claimed to be an exact additive identity."""

    n = max(1, len(rows))
    totals = {
        "total_policy_regret": 0.0,
        "recoverability_error_share": 0.0,
        "mismatch_share": 0.0,
        "open_set_share": 0.0,
        "cost_share": 0.0,
        "residual_share": 0.0,
    }
    for row in rows:
        regret = float(row.get("regret") or 0.0)
        totals["total_policy_regret"] += regret
        labels = row.get("failure_labels") or ()
        assigned = 0.0
        if "recoverability_estimation_failure" in labels:
            totals["recoverability_error_share"] += regret
            assigned += regret
        if "observation_model_mismatch" in labels:
            totals["mismatch_share"] += regret
            assigned += regret
        if "open_set_failure" in labels:
            totals["open_set_share"] += regret
            assigned += regret
        if "cost_model_failure" in labels:
            totals["cost_share"] += regret
            assigned += regret
        totals["residual_share"] += max(0.0, regret - assigned)
    totals["n"] = float(n)
    totals["additive_identity_claimed"] = 0.0
    return totals
