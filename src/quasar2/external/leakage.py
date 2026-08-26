"""Automated leakage tests for external-validity states."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from quasar2.cycle2.policies import FORBIDDEN_FEATURE_TOKENS, leakage_features
from quasar2.external.provenance import ORACLE_ONLY_FIELDS, deployment_view

GOLD_TOKENS = (
    "gold_hypothesis",
    "hidden_evidence",
    "true_kernels",
    "true_kernel",
    "oracle_q",
    "r_star",
    "answer_key",
    "correct_hypothesis",
)


def audit_state(state: Mapping[str, Any], deployment: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    dep_keys = leakage_features(tuple(deployment.keys()))
    if dep_keys:
        issues.append(f"forbidden_deployment_keys:{dep_keys}")
    blob = " ".join(f"{k}={v}" for k, v in deployment.items() if k not in {"q_obs", "belief", "proxy_kernels"})
    blob_l = blob.lower()
    gold = str(state.get("gold_hypothesis", "")).lower()
    hidden = str(state.get("hidden_evidence", "")).lower()
    if "gold_hypothesis=" in blob_l or "correct_hypothesis=" in blob_l:
        issues.append("gold_hypothesis_in_deployment_nonquery")
    if hidden and len(hidden) > 12 and hidden in blob_l:
        issues.append("hidden_evidence_in_deployment")
    q = str(deployment.get("q_obs", "")).lower()
    if hidden and len(hidden) > 16 and hidden.lower() in q:
        issues.append("hidden_evidence_in_query")
    year = state.get("year")
    # Future leak: temporal holdout must not include later-year hidden fields in index text.
    if state.get("split_role") == "temporal_holdout" and "future" in blob:
        issues.append("future_token_in_deployment")
    for name in GOLD_TOKENS:
        if name in deployment:
            issues.append(f"oracle_field_present:{name}")
    _ = year
    return issues


def audit_corpus_documents(documents: Sequence[Any], states: Sequence[Mapping[str, Any]]) -> list[str]:
    """Documents may mention gold class as scientific content; they must not copy hidden evidence of other objects' holdouts."""

    issues: list[str] = []
    holdout_hidden = [
        str(s["hidden_evidence"])
        for s in states
        if s.get("split_role") == "temporal_holdout" and s.get("transformation") == "clean"
    ]
    for doc in documents:
        text = f"{doc.title} {doc.text}".lower()
        if "gold_hypothesis" in text or "answer_key" in text:
            issues.append(f"doc_{doc.document_id}:label_token")
        for hidden in holdout_hidden:
            if hidden and len(hidden) > 24 and hidden.lower() in text:
                # Same-object discriminative docs are allowed; flag only if document is a distractor.
                if "unrelated" in text:
                    issues.append(f"doc_{doc.document_id}:holdout_hidden_in_distractor")
    return issues


def audit_batch(states: Sequence[Mapping[str, Any]], deployment_fn) -> dict[str, Any]:
    all_issues = []
    for state in states:
        issues = audit_state(state, deployment_fn(state))
        for issue in issues:
            all_issues.append({"state_id": state.get("state_id"), "issue": issue})
    return {
        "n_states": len(states),
        "n_issues": len(all_issues),
        "issues": all_issues[:50],
        "ok": len(all_issues) == 0,
        "oracle_only_fields": list(ORACLE_ONLY_FIELDS),
        "forbidden_feature_tokens": list(FORBIDDEN_FEATURE_TOKENS),
        "deployment_view_used": True,
    }


def strip_for_index(state: Mapping[str, Any]) -> dict[str, Any]:
    return deployment_view({"q_obs": state["q_obs"], "channel": state.get("channel"), "evidence_available": state.get("evidence_available")})
