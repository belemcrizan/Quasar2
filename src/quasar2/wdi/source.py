"""WDI EvidenceSource adapter: metadata search then structured observation fetch."""

from __future__ import annotations

from pathlib import Path

from quasar2.evidence.contracts import (
    EvidenceSource,
    FetchRequest,
    NeutralEvidenceItem,
    ProvenanceRecord,
    SearchRequest,
    SourceMetadata,
    ValidationReport,
)
from quasar2.retrieval.base import Document
from quasar2.retrieval.bm25 import BM25Retriever
from quasar2.wdi.normalize import resolve_period, sha256_json
from quasar2.wdi.snapshot import load_snapshot
from quasar2.wdi.taxonomy import ObservationStatus


def indicator_document(row: dict) -> Document:
    text = " ".join(
        part
        for part in (
            row.get("name", ""),
            row.get("source_note", ""),
            " ".join(row.get("topics") or []),
            row.get("unit", ""),
        )
        if part
    )
    return Document(
        document_id=f"ind:{row['indicator_id']}",
        domain="wdi",
        title=str(row.get("name") or row["indicator_id"]),
        text=text,
        hypothesis_ids=(row["indicator_id"],),
        tags=tuple(row.get("topics") or ()),
        metadata={
            "kind": "INDICATOR_METADATA",
            "indicator_id": row["indicator_id"],
            "unit": str(row.get("unit") or ""),
        },
    )


def entity_document(row: dict) -> Document:
    text = " ".join(
        part
        for part in (
            row.get("name", ""),
            row.get("entity_type", ""),
            row.get("region_name", ""),
            row.get("income_group_name", ""),
            row.get("capital_city", ""),
        )
        if part
    )
    return Document(
        document_id=f"ent:{row['entity_code']}",
        domain="wdi",
        title=str(row.get("name") or row["entity_code"]),
        text=text,
        hypothesis_ids=(row["entity_code"],),
        metadata={
            "kind": "ENTITY_METADATA",
            "entity_code": row["entity_code"],
            "entity_type": row["entity_type"],
        },
    )


class WDIEvidenceSource:
    def __init__(self, snapshot_dir: str | Path) -> None:
        loaded = load_snapshot(Path(snapshot_dir))
        self.snapshot_dir = Path(snapshot_dir)
        self.manifest = loaded["manifest"]
        self.entities = {row["entity_code"]: row for row in loaded["entities"]}
        self.indicators = {row["indicator_id"]: row for row in loaded["indicators"]}
        self.observations = loaded["observations"]
        self._documents = tuple(
            [indicator_document(row) for row in loaded["indicators"]]
            + [entity_document(row) for row in loaded["entities"]]
        )
        self._retriever = BM25Retriever(self._documents)

    def documents(self) -> tuple[Document, ...]:
        return self._documents

    def metadata(self) -> SourceMetadata:
        return SourceMetadata(
            source_id="2",
            source_name="worldbank_wdi",
            api_version="2",
            snapshot_id=str(self.manifest["snapshot_id"]),
        )

    def provenance(self) -> ProvenanceRecord:
        return ProvenanceRecord(
            snapshot_id=str(self.manifest["snapshot_id"]),
            source="worldbank_wdi",
            source_id="2",
            created_at=str(self.manifest["created_at"]),
            content_hashes=self.manifest.get("hashes", {}),
        )

    def validate(self) -> ValidationReport:
        errors = []
        if self.manifest.get("status") != "COMPLETE":
            errors.append("snapshot is not COMPLETE")
        return ValidationReport(ok=not errors, errors=tuple(errors), details=self.manifest.get("row_counts", {}))

    def search(self, request: SearchRequest) -> list[NeutralEvidenceItem]:
        hits = self._retriever.search(request.query, top_k=request.top_k, domain="wdi")
        items: list[NeutralEvidenceItem] = []
        snapshot_id = str(self.manifest["snapshot_id"])
        for hit in hits:
            kind = hit.document.metadata.get("kind", "METADATA")
            payload = dict(hit.document.metadata)
            payload["title"] = hit.document.title
            payload["text"] = hit.document.text
            items.append(
                NeutralEvidenceItem(
                    evidence_id=hit.document.document_id,
                    source="worldbank_wdi",
                    source_snapshot=snapshot_id,
                    kind=str(kind),
                    payload=payload,
                    retrieval_score=hit.score,
                    content_hash=sha256_json(payload),
                )
            )
        return items

    def fetch(self, request: FetchRequest) -> list[NeutralEvidenceItem]:
        snapshot_id = str(self.manifest["snapshot_id"])
        if request.indicator_id not in self.indicators:
            payload = {
                "observation_status": ObservationStatus.UNSUPPORTED_INDICATOR.value,
                "indicator_id": request.indicator_id,
                "entity_code": request.entity_code,
                "period": request.period,
            }
        elif request.entity_code not in self.entities:
            payload = {
                "observation_status": ObservationStatus.UNSUPPORTED_ENTITY.value,
                "indicator_id": request.indicator_id,
                "entity_code": request.entity_code,
                "period": request.period,
            }
        else:
            payload = resolve_period(
                self.observations,
                indicator_id=request.indicator_id,
                entity_code=request.entity_code,
                requested=request.period,
            )
            payload["entity_type"] = self.entities[request.entity_code]["entity_type"]
            payload["unit"] = request.unit or self.indicators[request.indicator_id].get("unit") or ""
        return [
            NeutralEvidenceItem(
                evidence_id=f"obs:{request.indicator_id}:{request.entity_code}:{request.period}",
                source="worldbank_wdi",
                source_snapshot=snapshot_id,
                kind="OBSERVATION",
                payload=payload,
                content_hash=sha256_json(payload),
            )
        ]


def assert_evidence_source(source: EvidenceSource) -> None:
    source.metadata()
    source.validate()
    source.provenance()
