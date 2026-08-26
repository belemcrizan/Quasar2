"""Typed source registry. Adapters declare license, snapshot, and live-test policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

SOURCE_FAMILIES = frozenset(
    {
        "WORLD_BANK_WDI",
        "JWST_MAST",
        "JWST_CRDS",
        "NASA_ADS",
        "CERN_OPEN_DATA",
        "INSPIRE_HEP",
    }
)


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    source_id: str
    provider: str
    source_type: str
    family: str
    official_base_url: str
    authentication_mode: str
    license_or_terms_url: str
    attribution_text: str
    rate_limit_policy: str
    snapshot_method: str
    supported_modalities: tuple[str, ...]
    temporal_semantics: str
    known_quality_limits: tuple[str, ...]
    redistribution_allowed: bool
    live_test_enabled: bool
    role: str
    docs_urls: tuple[str, ...] = ()
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.family not in SOURCE_FAMILIES:
            raise ValueError(f"Unknown source family {self.family!r}")


class SourceAdapter(Protocol):
    def descriptor(self) -> SourceDescriptor: ...

    def validate(self) -> Mapping[str, Any]: ...

    def records(self) -> Sequence[Mapping[str, Any]]: ...

    def filter_by_cutoff(self, cutoff: str) -> Sequence[Mapping[str, Any]]: ...


class SourceRegistry:
    def __init__(self, descriptors: Sequence[SourceDescriptor] | None = None) -> None:
        self._by_id: dict[str, SourceDescriptor] = {}
        for item in descriptors or ():
            self.register(item)

    def register(self, descriptor: SourceDescriptor) -> None:
        existing = self._by_id.get(descriptor.source_id)
        if existing is not None and existing != descriptor:
            raise ValueError(f"Conflicting registration for {descriptor.source_id}")
        self._by_id[descriptor.source_id] = descriptor

    def get(self, source_id: str) -> SourceDescriptor:
        try:
            return self._by_id[source_id]
        except KeyError as error:
            raise KeyError(f"Unknown source_id {source_id!r}") from error

    def by_family(self, family: str) -> tuple[SourceDescriptor, ...]:
        return tuple(item for item in self._by_id.values() if item.family == family)

    def all(self) -> tuple[SourceDescriptor, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))


def default_descriptors() -> tuple[SourceDescriptor, ...]:
    return (
        SourceDescriptor(
            source_id="worldbank_wdi",
            provider="World Bank",
            source_type="structured_time_series",
            family="WORLD_BANK_WDI",
            official_base_url="https://api.worldbank.org/v2",
            authentication_mode="none",
            license_or_terms_url="https://www.worldbank.org/ext/en/legal/terms-conditions/datasets",
            attribution_text="World Bank World Development Indicators (source=2).",
            rate_limit_policy="honor HTTP 429; exponential backoff with jitter",
            snapshot_method="immutable local snapshot directory with SHA-256 manifests",
            supported_modalities=("TABLE", "TEXT"),
            temporal_semantics="observation year; latest-available relative to snapshot cutoff",
            known_quality_limits=(
                "indicator-level source metadata may differ from the World Bank",
                "missing values are not zeros",
            ),
            redistribution_allowed=True,
            live_test_enabled=False,
            role="structured numeric and temporal ground truth",
            docs_urls=(
                "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392",
                "https://datahelpdesk.worldbank.org/knowledgebase/articles/898581",
                "https://datahelpdesk.worldbank.org/knowledgebase/articles/1886695",
            ),
        ),
        SourceDescriptor(
            source_id="jwst_mast",
            provider="STScI MAST",
            source_type="observation_archive_metadata",
            family="JWST_MAST",
            official_base_url="https://mast.stsci.edu/api/v0.1/",
            authentication_mode="none_or_token_for_proprietary",
            license_or_terms_url="https://jwst-docs.stsci.edu/accessing-jwst-data/citing-jwst-data",
            attribution_text="JWST data from MAST; cite program, DOI, and CRDS context.",
            rate_limit_policy="honor HTTP 429; do not scrape bulk FITS by default",
            snapshot_method="metadata-only frozen JSON fixture or MAST TAP/API dump",
            supported_modalities=("TABLE", "TEXT"),
            temporal_semantics="observation date, public/proprietary at cutoff, product revision",
            known_quality_limits=(
                "MAST is an observation archive, not a unique physical-source catalog",
                "target name is not entity resolution",
            ),
            redistribution_allowed=False,
            live_test_enabled=False,
            role="deterministic archive metadata retrieval and product lineage",
            docs_urls=(
                "https://outerspace.stsci.edu/spaces/MASTDOCS/pages/153686876/API+Advanced+Search",
                "https://astroquery.readthedocs.io/en/stable/mast/mast_obsquery.html",
            ),
        ),
        SourceDescriptor(
            source_id="jwst_crds",
            provider="STScI CRDS",
            source_type="calibration_context",
            family="JWST_CRDS",
            official_base_url="https://jwst-crds.stsci.edu",
            authentication_mode="none",
            license_or_terms_url="https://jwst-docs.stsci.edu/accessing-jwst-data/citing-jwst-data",
            attribution_text="JWST CRDS context and reference files; pipeline version is required.",
            rate_limit_policy="bounded metadata requests only in this cycle",
            snapshot_method="documented context identifiers in fixtures",
            supported_modalities=("TEXT", "TABLE"),
            temporal_semantics="calibration context supersession; not newer-is-better",
            known_quality_limits=("newer CRDS context is not automatically compatible with an older pipeline",),
            redistribution_allowed=False,
            live_test_enabled=False,
            role="calibration provenance for JWST Tier 2",
            docs_urls=("https://jwst-docs.stsci.edu/jwst-science-calibration-pipeline",),
        ),
        SourceDescriptor(
            source_id="nasa_ads",
            provider="NASA ADS",
            source_type="bibliographic_metadata",
            family="NASA_ADS",
            official_base_url="https://api.adsabs.harvard.edu/v1",
            authentication_mode="token",
            license_or_terms_url="https://ui.adsabs.harvard.edu/help/terms/",
            attribution_text="NASA ADS bibliographic metadata. Abstracts are not full claims.",
            rate_limit_policy="token quota; honor 429",
            snapshot_method="identifier + metadata snapshot; no unauthorized full text",
            supported_modalities=("TEXT",),
            temporal_semantics="publication and revision dates for time-travel evaluation",
            known_quality_limits=("abstract is not the complete scientific claim",),
            redistribution_allowed=False,
            live_test_enabled=False,
            role="literature discovery and retrospective evidence timelines",
            docs_urls=("https://ui.adsabs.harvard.edu/help/api/",),
        ),
        SourceDescriptor(
            source_id="cern_open_data",
            provider="CERN",
            source_type="dataset_and_software_records",
            family="CERN_OPEN_DATA",
            official_base_url="https://opendata.cern.ch/api",
            authentication_mode="none",
            license_or_terms_url="https://opendata.cern.ch/docs/terms-of-use",
            attribution_text="CERN Open Data. Data levels are not interchangeable evidence.",
            rate_limit_policy="bounded record metadata; storage cap on event data",
            snapshot_method="record metadata JSON; no default bulk event download",
            supported_modalities=("TEXT", "TABLE"),
            temporal_semantics="release date, software environment, data level",
            known_quality_limits=(
                "Level 2 educational representations are not Level 3 reconstructed data",
                "QUASAR DEFER is not particle-physics significance",
            ),
            redistribution_allowed=False,
            live_test_enabled=False,
            role="DOI-grounded high-noise scientific record retrieval",
            docs_urls=("https://opendata.cern.ch/docs/about",),
        ),
        SourceDescriptor(
            source_id="inspire_hep",
            provider="INSPIRE",
            source_type="hep_literature_metadata",
            family="INSPIRE_HEP",
            official_base_url="https://inspirehep.net/api",
            authentication_mode="none",
            license_or_terms_url="https://inspirehep.net",
            attribution_text="INSPIRE-HEP metadata. Not collision-event evidence.",
            rate_limit_policy="honor 429; metadata only in this cycle",
            snapshot_method="record metadata JSON fixtures",
            supported_modalities=("TEXT",),
            temporal_semantics="publication timelines and record identifiers",
            known_quality_limits=("metadata is not event data",),
            redistribution_allowed=False,
            live_test_enabled=False,
            role="HEP literature and data-record identifier resolution",
            docs_urls=("https://github.com/inspirehep/rest-api-doc",),
        ),
    )


def builtin_registry() -> SourceRegistry:
    return SourceRegistry(default_descriptors())
