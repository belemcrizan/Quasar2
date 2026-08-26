"""Versioned EvidenceEnvelope. Raw scores stay distinct from derived weights."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

ENVELOPE_SCHEMA_VERSION = "1.0.0"

MODALITIES = frozenset({"TEXT", "TABLE", "GRAPH", "IMAGE", "SPECTRUM", "TIME_SERIES"})
POLARITIES = frozenset({"SUPPORTS", "CONTRADICTS", "NEUTRAL", "UNCERTAIN"})
MISSINGNESS = frozenset(
    {
        "NOT_REPORTED",
        "NOT_OBSERVED",
        "NOT_APPLICABLE",
        "EMBARGOED_OR_RESTRICTED",
        "FILTERED_BY_KNOWLEDGE_CUTOFF",
        "RETRIEVAL_FAILED",
        "CORRUPT_OR_INVALID",
        "UNKNOWN_REASON",
    }
)
CONFLICT_STATES = frozenset(
    {
        "VALUE_CONFLICT",
        "UNIT_CONFLICT",
        "ENTITY_CONFLICT",
        "TEMPORAL_CONFLICT",
        "CALIBRATION_CONFLICT",
        "METHODOLOGY_CONFLICT",
        "CLAIM_CONFLICT",
        "PROVENANCE_CONFLICT",
    }
)


@dataclass(frozen=True, slots=True)
class UncertaintyBundle:
    measurement_uncertainty: str | float | None = None
    calibration_uncertainty: str | float | None = None
    sampling_uncertainty: str | float | None = None
    aleatoric_uncertainty: str | float | None = None
    epistemic_uncertainty: str | float | None = None
    retrieval_uncertainty: str | float | None = None
    source_uncertainty: str | float | None = None
    model_uncertainty: str | float | None = None
    conflict_uncertainty: str | float | None = None
    missingness_uncertainty: str | float | None = None


@dataclass(frozen=True, slots=True)
class EvidenceEnvelope:
    evidence_id: str
    source_id: str
    source_record_id: str
    source_type: str
    modality: str
    content_or_reference: Any
    content_hash: str
    retrieved_at: str | None = None
    published_at: str | None = None
    observed_at: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    revision_at: str | None = None
    supersedes: str | None = None
    pipeline_version: str | None = None
    calibration_context: str | None = None
    software_environment: str | None = None
    license: str | None = None
    attribution: str | None = None
    authority_class: str | None = None
    quality_flags: tuple[str, ...] = ()
    uncertainty: UncertaintyBundle = field(default_factory=UncertaintyBundle)
    missingness: str | None = None
    lineage: tuple[str, ...] = ()
    derived_from: tuple[str, ...] = ()
    independence_group: str | None = None
    access_status: str = "AVAILABLE"
    knowledge_cutoff_eligible: bool = True
    polarity: str = "NEUTRAL"
    raw_retrieval_score: float = 0.0
    adjusted_score: float | None = None
    conflict_state: str | None = None
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.modality not in MODALITIES:
            raise ValueError(f"Unsupported modality {self.modality!r}")
        if self.polarity not in POLARITIES:
            raise ValueError(f"Unsupported polarity {self.polarity!r}")
        if self.missingness is not None and self.missingness not in MISSINGNESS:
            raise ValueError(f"Unsupported missingness {self.missingness!r}")
        if self.conflict_state is not None and self.conflict_state not in CONFLICT_STATES:
            raise ValueError(f"Unsupported conflict_state {self.conflict_state!r}")


def envelope_from_neutral(
    item: Mapping[str, Any],
    *,
    modality: str = "TEXT",
    source_type: str = "DOCUMENT",
    retrieved_at: str | None = None,
) -> EvidenceEnvelope:
    """Adapt existing NeutralEvidenceItem mappings without mutating them."""

    return EvidenceEnvelope(
        evidence_id=str(item.get("evidence_id") or ""),
        source_id=str(item.get("source") or ""),
        source_record_id=str(item.get("evidence_id") or ""),
        source_type=source_type,
        modality=modality,
        content_or_reference=item.get("payload"),
        content_hash=str(item.get("content_hash") or ""),
        retrieved_at=retrieved_at,
        raw_retrieval_score=float(item.get("retrieval_score") or 0.0),
        polarity="SUPPORTS" if item.get("supports") else ("CONTRADICTS" if item.get("contradicts") else "NEUTRAL"),
        payload=dict(item.get("payload") or {}),
        knowledge_cutoff_eligible=True,
        access_status="AVAILABLE",
    )
