"""Offline metadata fixtures for JWST/MAST, CERN Open Data, and INSPIRE."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from quasar2.wdi.normalize import sha256_json
from quasar2.wdi.snapshot import utc_now, write_json


def _eligible(record: Mapping[str, Any], cutoff: str | None) -> bool:
    if cutoff is None:
        return True
    available = str(record.get("available_at") or record.get("published_at") or "")
    return bool(available) and available <= cutoff


class FrozenMetadataSource:
    """Small legal snapshot: identifiers and metadata, not bulk scientific files."""

    def __init__(self, records: Sequence[Mapping[str, Any]], descriptor: Mapping[str, Any]) -> None:
        self._records = tuple(dict(item) for item in records)
        self._descriptor = dict(descriptor)

    def descriptor(self) -> Mapping[str, Any]:
        return dict(self._descriptor)

    def validate(self) -> dict[str, Any]:
        errors = []
        for record in self._records:
            if not record.get("record_id"):
                errors.append("missing record_id")
            if not record.get("available_at"):
                errors.append(f"{record.get('record_id')}: missing available_at")
        return {"ok": not errors, "errors": errors, "n": len(self._records)}

    def records(self, *, cutoff: str | None = None) -> tuple[dict[str, Any], ...]:
        return tuple(item for item in self._records if _eligible(item, cutoff))

    def filter_by_cutoff(self, cutoff: str) -> tuple[dict[str, Any], ...]:
        return self.records(cutoff=cutoff)

    def search(self, query: str, *, cutoff: str | None = None) -> tuple[dict[str, Any], ...]:
        tokens = {token.lower() for token in query.replace(",", " ").split() if token}
        hits = []
        for record in self.records(cutoff=cutoff):
            hay = " ".join(str(value) for value in record.values()).lower()
            score = sum(1.0 for token in tokens if token in hay)
            if score:
                hits.append({**record, "retrieval_score": score})
        return tuple(sorted(hits, key=lambda item: (-item["retrieval_score"], item["record_id"])))


JWST_FIXTURE_RECORDS = (
    {
        "record_id": "jwst-obs-001",
        "source_id": "jwst_mast",
        "instrument": "NIRCam",
        "filter": "F444W",
        "program": "2736",
        "target": "WASP-39",
        "product_type": "calibrated",
        "calibration_level": 2,
        "pipeline_version": "1.12.5",
        "crds_context": "jwst_1140.pmap",
        "available_at": "2023-06-01",
        "published_at": "2023-06-01",
        "observed_at": "2022-07-10",
        "license": "see STScI citing JWST data",
    },
    {
        "record_id": "jwst-obs-002",
        "source_id": "jwst_mast",
        "instrument": "NIRSpec",
        "filter": "G395H",
        "program": "2736",
        "target": "WASP-39",
        "product_type": "reprocessed",
        "calibration_level": 3,
        "pipeline_version": "1.14.0",
        "crds_context": "jwst_1215.pmap",
        "available_at": "2024-02-15",
        "published_at": "2024-02-15",
        "observed_at": "2022-07-10",
        "supersedes": "jwst-obs-001",
        "license": "see STScI citing JWST data",
    },
    {
        "record_id": "jwst-obs-003",
        "source_id": "jwst_mast",
        "instrument": "MIRI",
        "filter": "F770W",
        "program": "1180",
        "target": "NGC 1333",
        "product_type": "calibrated",
        "calibration_level": 2,
        "pipeline_version": "1.12.5",
        "crds_context": "jwst_1140.pmap",
        "available_at": "2023-01-20",
        "published_at": "2023-01-20",
        "observed_at": "2022-09-01",
        "license": "see STScI citing JWST data",
    },
)

CERN_FIXTURE_RECORDS = (
    {
        "record_id": "cern-od-1",
        "source_id": "cern_open_data",
        "title": "CMS 2012 dimuon sample (educational Level 2)",
        "experiment": "CMS",
        "collision_energy": "8TeV",
        "data_level": "Level2",
        "software_environment": "CMSSW_5_3_32",
        "doi": "10.7483/OPENDATA.CMS.EXAMPLE",
        "available_at": "2014-11-20",
        "published_at": "2014-11-20",
        "license": "https://opendata.cern.ch/docs/terms-of-use",
    },
    {
        "record_id": "cern-od-2",
        "source_id": "cern_open_data",
        "title": "CMS 2016 reconstructed subset (Level 3)",
        "experiment": "CMS",
        "collision_energy": "13TeV",
        "data_level": "Level3",
        "software_environment": "CMSSW_8_0_32",
        "doi": "10.7483/OPENDATA.CMS.EXAMPLE2",
        "available_at": "2020-06-01",
        "published_at": "2020-06-01",
        "license": "https://opendata.cern.ch/docs/terms-of-use",
    },
)

INSPIRE_FIXTURE_RECORDS = (
    {
        "record_id": "inspire-1",
        "source_id": "inspire_hep",
        "title": "Observation of a new particle in the search for the Standard Model Higgs boson",
        "arxiv": "1207.7235",
        "doi": "10.1016/j.physletb.2012.08.021",
        "experiment": "ATLAS",
        "available_at": "2012-07-31",
        "published_at": "2012-09-17",
        "license": "publisher / arXiv terms",
    },
    {
        "record_id": "inspire-2",
        "source_id": "inspire_hep",
        "title": "Unrelated later software note",
        "arxiv": "2101.00001",
        "doi": "10.1000/example.later",
        "experiment": "CMS",
        "available_at": "2021-01-02",
        "published_at": "2021-01-02",
        "license": "publisher / arXiv terms",
    },
)


def jwst_mast_source() -> FrozenMetadataSource:
    return FrozenMetadataSource(
        JWST_FIXTURE_RECORDS,
        {"source_id": "jwst_mast", "family": "JWST_MAST", "tier": 1, "mode": "metadata_only"},
    )


def cern_open_data_source() -> FrozenMetadataSource:
    return FrozenMetadataSource(
        CERN_FIXTURE_RECORDS,
        {"source_id": "cern_open_data", "family": "CERN_OPEN_DATA", "tier": 1, "mode": "metadata_only"},
    )


def inspire_hep_source() -> FrozenMetadataSource:
    return FrozenMetadataSource(
        INSPIRE_FIXTURE_RECORDS,
        {"source_id": "inspire_hep", "family": "INSPIRE_HEP", "tier": 1, "mode": "metadata_only"},
    )


def write_source_fixture(family: str, destination: str | Path) -> Path:
    mapping = {
        "jwst_mast": (JWST_FIXTURE_RECORDS, "jwst_mast"),
        "cern_open_data": (CERN_FIXTURE_RECORDS, "cern_open_data"),
        "inspire_hep": (INSPIRE_FIXTURE_RECORDS, "inspire_hep"),
    }
    if family not in mapping:
        raise ValueError(f"Unknown fixture family {family!r}")
    records, source_id = mapping[family]
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_id": source_id,
        "created_at": utc_now(),
        "records": list(records),
        "content_hash": sha256_json(list(records)),
        "redistribution": "metadata identifiers only; not a scientific benchmark",
        "status": "FIXTURE",
    }
    path = dest / "snapshot_manifest.json"
    write_json(path, payload)
    return path
