"""Ambiguity taxonomy. Labels are multi-label; none is exclusive."""

from __future__ import annotations

AMBIGUITY_LABELS = (
    "lexical_ambiguity",
    "semantic_ambiguity",
    "observational_degeneracy",
    "missing_evidence",
    "conflicting_evidence",
    "incomplete_context",
    "temporal_ambiguity",
    "cross_source_disagreement",
    "open_set",
    "non_recoverable_ambiguity",
    "recoverable_ambiguity",
    "misleading_proxy_evidence",
)

RECOVERABILITY_CLASSES = (
    "recoverable",
    "non_recoverable",
    "mismatch_sensitive",
    "unknown",
)

DEGRADATION_KINDS = (
    "clean",
    "lexical",
    "missing_context",
    "entity_removed",
    "temporal_removed",
    "conflicting",
    "partial",
    "severe",
)

GENERALIZATION_AXES = (
    "larger_dataset",
    "cross_source",
    "cross_instrument",
    "cross_mission",
    "temporal",
    "cross_domain",
)
