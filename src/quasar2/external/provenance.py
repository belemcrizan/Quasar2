"""Provenance records. Never invent official archive IDs as live dumps."""

from __future__ import annotations

from typing import Any, Mapping

PROVENANCE_KINDS = (
    "OFFICIAL_FIXTURE_METADATA",
    "SCHEMA_FAITHFUL_SYNTHETIC",
    "EXISTING_ASTRONOMY_SANITY",
    "EXISTING_OPS_RUNBOOK",
    "EXISTING_WDI_SNAPSHOT",
    "CONTROLLED_DEGRADATION_OF_ABOVE",
)

ORACLE_ONLY_FIELDS = (
    "gold_hypothesis",
    "hidden_evidence",
    "true_kernel",
    "oracle_q",
    "r_star",
    "future_observation",
    "answer_key",
    "manually_curated_discriminator_not_in_query",
)


def deployment_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """Strip oracle-only and future fields for decision-time features."""

    blocked = {name.lower() for name in ORACLE_ONLY_FIELDS}
    blocked.update({"correct_hypothesis", "gold", "hidden_text", "future"})
    out = {}
    for key, value in record.items():
        low = key.lower()
        if any(token in low for token in blocked):
            continue
        out[key] = value
    return out


def card_template(source_id: str, **fields: Any) -> dict[str, Any]:
    required = {
        "source": source_id,
        "ownership": fields.get("ownership", ""),
        "public_access": fields.get("public_access", ""),
        "license_terms": fields.get("license_terms", ""),
        "snapshot": fields.get("snapshot", ""),
        "retrieval_date": fields.get("retrieval_date", "not_a_live_fetch"),
        "filtering": fields.get("filtering", ""),
        "transformations": fields.get("transformations", ""),
        "exclusions": fields.get("exclusions", ""),
        "known_biases": fields.get("known_biases", ""),
        "ambiguity_construction": fields.get("ambiguity_construction", ""),
        "ground_truth": fields.get("ground_truth", ""),
        "limitations": fields.get("limitations", ""),
        "live_nasa_esa_dump": False,
    }
    required.update(fields)
    return required
