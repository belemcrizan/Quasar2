"""Source-neutral evidence contracts. Policy code depends only on these types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class SearchRequest:
    query: str
    kind: str = "METADATA"
    top_k: int = 8
    filters: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FetchRequest:
    indicator_id: str
    entity_code: str
    period: str
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    source_id: str
    source_name: str
    api_version: str
    snapshot_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    snapshot_id: str
    source: str
    source_id: str
    created_at: str
    content_hashes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NeutralEvidenceItem:
    evidence_id: str
    source: str
    source_snapshot: str
    kind: str
    payload: Mapping[str, Any]
    quality: float = 1.0
    retrieval_score: float = 0.0
    content_hash: str = ""
    acquisition_action_id: str = ""
    supports: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()


class EvidenceSource(Protocol):
    def search(self, request: SearchRequest) -> list[NeutralEvidenceItem]: ...

    def fetch(self, request: FetchRequest) -> list[NeutralEvidenceItem]: ...

    def metadata(self) -> SourceMetadata: ...

    def validate(self) -> ValidationReport: ...

    def provenance(self) -> ProvenanceRecord: ...
