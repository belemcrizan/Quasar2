"""Non-compensatory maturity ceilings (Section 84)."""

from __future__ import annotations

from typing import Any, Mapping


def _ceiling(gates: Mapping[str, str], rules: list[tuple[set[str], float]]) -> float:
    score = 10.0
    for names, cap in rules:
        if any(gates.get(name) in {"FAIL", "NOT_RUN", "INCONCLUSIVE"} for name in names):
            score = min(score, cap)
        if any(gates.get(name) == "PARTIAL" for name in names):
            score = min(score, cap + 0.5)
    if any(v == "CRITICAL_INTEGRITY_FAIL" for v in gates.values()):
        score = min(score, 4.0)
    return score


def score_recoverability(gates: Mapping[str, str], *, negative_conclusion: bool) -> tuple[float, list[str]]:
    notes = []
    score = 8.8
    if gates.get("heldout_family") != "PASS":
        score = min(score, 6.5)
        notes.append("no held-out-family PASS -> <=6.5")
    if gates.get("mismatch") != "PASS":
        score = min(score, 6.5)
        notes.append("no proxy/oracle mismatch PASS -> <=6.5")
    if gates.get("calibrated_uncertainty") != "PASS":
        score = min(score, 7.0)
        notes.append("no calibrated uncertainty PASS -> <=7.0")
    if gates.get("equal_budget_acquisition") != "PASS":
        score = min(score, 7.0)
        notes.append("no equal-budget acquisition PASS -> <=7.0")
    if gates.get("gate1_followup") != "PASS":
        score = min(score, 7.0)
        notes.append("Gate 1 remains failed without decisive operational follow-up -> <=7.0")
    if negative_conclusion:
        notes.append("explicit negative/narrowing conclusion recorded; not operational utility")
    if score > 8.5 and any(v != "PASS" for k, v in gates.items() if k != "gate1_followup"):
        score = min(score, 8.4)
        notes.append(">8.5 requires all hard gates PASS")
    return round(score, 1), notes


def score_policy(gates: Mapping[str, str]) -> tuple[float, list[str]]:
    notes = []
    score = 8.8
    if gates.get("bound_as_q") == "FAIL":
        return 4.0, ["bound used as Q -> <=4.0"]
    if gates.get("empirical_q") != "PASS":
        score = min(score, 6.0)
        notes.append("no empirical action values -> <=6.0")
    if gates.get("baseline_fallback") != "PASS":
        score = min(score, 6.5)
        notes.append("no baseline fallback -> <=6.5")
    if gates.get("ope_unsupported") == "FAIL":
        score = min(score, 5.0)
        notes.append("OPE claimed without support -> <=5.0")
    if gates.get("equal_budget") != "PASS":
        score = min(score, 7.0)
        notes.append("no equal-budget strong baseline -> <=7.0")
    if gates.get("fault_tests") != "PASS":
        score = min(score, 7.0)
        notes.append("no deployment-like fault tests -> <=7.0")
    return round(score, 1), notes


def score_synthetic(gates: Mapping[str, str]) -> tuple[float, list[str]]:
    notes = []
    score = 9.6
    if gates.get("counterfactual_oracle") != "PASS":
        score = min(score, 8.0)
        notes.append("no validated counterfactual oracle -> <=8.0")
    if gates.get("family_holdout") != "PASS":
        score = min(score, 8.0)
        notes.append("no held-out generator family -> <=8.0")
    if gates.get("only_row_split") == "FAIL":
        score = min(score, 7.5)
        notes.append("only random row split -> <=7.5")
    if gates.get("anti_quasar") != "PASS":
        score = min(score, 8.5)
        notes.append("no anti-QUASAR regime -> <=8.5")
    if gates.get("oracle_leakage") == "FAIL":
        return 4.0, ["policy observed oracle/generator leakage -> <=4.0"]
    return round(score, 1), notes


def score_deployment(gates: Mapping[str, str]) -> tuple[float, list[str]]:
    notes = []
    score = 8.6
    if gates.get("not_synthetic_only") != "PASS":
        score = min(score, 5.0)
        notes.append("synthetic only -> <=5.0")
    if gates.get("wdi_snapshot") != "PASS":
        score = min(score, 6.0)
        notes.append("WDI without frozen snapshot -> <=6.0")
    if gates.get("neural_executed") == "FAIL":
        score = min(score, 6.5)
        notes.append("neural claimed but not executed -> <=6.5")
    if gates.get("real_retrieval_x_policy") != "PASS":
        score = min(score, 7.0)
        notes.append("no real retrieval crossed with policy -> <=7.0")
    if gates.get("shadow_as_causal") == "FAIL":
        score = min(score, 5.0)
        notes.append("replay/shadow as causal online value -> <=5.0")
    if gates.get("ops_sequential") != "PASS":
        score = min(score, 7.0)
        notes.append("no OPS sequential/fault environment -> <=7.0")
    return round(score, 1), notes


def assign_maturity(payload: Mapping[str, Any]) -> dict[str, Any]:
    rec_gates = payload["recoverability_gates"]
    pol_gates = payload["policy_gates"]
    syn_gates = payload["synthetic_gates"]
    dep_gates = payload["deployment_gates"]
    rec, rec_notes = score_recoverability(rec_gates, negative_conclusion=bool(payload.get("r_negative")))
    pol, pol_notes = score_policy(pol_gates)
    syn, syn_notes = score_synthetic(syn_gates)
    dep, dep_notes = score_deployment(dep_gates)
    return {
        "Operational Recoverability": rec,
        "Deployment-Ready Policy": pol,
        "Controlled Synthetic Evidence": syn,
        "Deployment-Like Evidence": dep,
        "notes": {
            "recoverability": rec_notes,
            "policy": pol_notes,
            "synthetic": syn_notes,
            "deployment": dep_notes,
        },
        "gates": {
            "recoverability": rec_gates,
            "policy": pol_gates,
            "synthetic": syn_gates,
            "deployment": dep_gates,
        },
    }
