"""Deterministic primary-failure assignment under a frozen causal order."""

from __future__ import annotations

from quasar2.rescue.evidence_oracle import CAUSAL_ORDER


def classify_primary(
    *,
    catalog_has_h_star: bool,
    sufficient: str,
    h_star_in_generated: bool,
    gold_retrieved: bool,
    oracle_hypothesis_correct: bool,
    oracle_retrieval_correct: bool,
    oracle_evidence_correct: bool,
    oracle_belief_correct: bool,
    predicted_correct: bool,
    belief_top_is_h_star: bool,
    delta_b_star: float | None,
    factorial_conflict: bool,
) -> tuple[str, tuple[str, ...], str]:
    secondary: list[str] = []
    if not catalog_has_h_star:
        return "OPEN_SET", (), "H* is not in the catalog"
    if sufficient == "undetermined":
        return "INDETERMINATE", (), "evidence sufficiency could not be verified"
    if sufficient == "false":
        return "MISSING_EVIDENCE", (), "corpus has no sufficient gold evidence for H*"
    if factorial_conflict:
        return "NON_MONOTONIC_INTERACTION", tuple(CAUSAL_ORDER[:3]), "oracle combination conflict"
    if not h_star_in_generated:
        if oracle_hypothesis_correct:
            return "HYPOTHESIS_FAILURE", (), "injecting H* allows rescue"
        secondary.append("HYPOTHESIS_FAILURE")
    if not gold_retrieved:
        if oracle_retrieval_correct:
            return "RETRIEVAL_FAILURE", tuple(secondary), "gold evidence exists but was not retrieved in budget"
        secondary.append("RETRIEVAL_FAILURE")
    if gold_retrieved and not predicted_correct and oracle_evidence_correct:
        return "DISCRIMINATION_FAILURE", tuple(secondary), "gold docs retrieved but scoring did not separate H*"
    if (delta_b_star is not None and delta_b_star <= 0) and oracle_belief_correct and not predicted_correct:
        return "BELIEF_UPDATE_FAILURE", tuple(secondary), "discriminative signal did not raise b(H*)"
    if belief_top_is_h_star and not predicted_correct:
        return "DECISION_FAILURE", tuple(secondary), "belief ranking is correct but the committed prediction is not"
    if oracle_belief_correct and not predicted_correct:
        return "DECISION_FAILURE", tuple(secondary), "oracle belief ranking rescues; live decision did not"
    if predicted_correct:
        return "NONE", tuple(secondary), "deliberative path already correct"
    if not oracle_belief_correct:
        return "INDETERMINATE", tuple(secondary), "even oracle belief failed; attribution blocked"
    return "INDETERMINATE", tuple(secondary), "no single first-failure matched the intervention pattern"
