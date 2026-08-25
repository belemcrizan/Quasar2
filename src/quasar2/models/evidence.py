"""Evidence retrieved and scored for one candidate hypothesis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    hypothesis_id: str
    document_id: str
    title: str
    snippet: str
    retrieval_score: float
    observation_coverage: float
    anchor_coverage: float
    discriminator_coverage: float
    foreign_hypothesis: bool
    support_score: float
    retrieval_rank: int
    round_index: int
    query: str


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    hypothesis_id: str
    items: tuple[EvidenceItem, ...]
    aggregate_support: float
    novel_item_count: int

