"""Write a tiny COMPLETE WDI snapshot for offline tests (no network)."""

from __future__ import annotations

from pathlib import Path

from quasar2.wdi.snapshot import snapshot_paths, utc_now, write_json, write_jsonl
from quasar2.wdi.taxonomy import EntityType, ObservationStatus


def write_offline_ci_snapshot(root: Path) -> dict:
    root = Path(root)
    paths = snapshot_paths(root)
    entities = [
        {
            "entity_code": "BRA",
            "iso2_code": "BR",
            "name": "Brazil",
            "entity_type": EntityType.COUNTRY.value,
            "region_id": "LCN",
            "region_name": "Latin America & Caribbean",
            "income_group_id": "UMC",
            "income_group_name": "Upper middle income",
            "capital_city": "Brasilia",
            "source_hash": "a",
        },
        {
            "entity_code": "USA",
            "iso2_code": "US",
            "name": "United States",
            "entity_type": EntityType.COUNTRY.value,
            "region_id": "NAC",
            "region_name": "North America",
            "income_group_id": "HIC",
            "income_group_name": "High income",
            "capital_city": "Washington D.C.",
            "source_hash": "b",
        },
        {
            "entity_code": "LCN",
            "iso2_code": "ZJ",
            "name": "Latin America & Caribbean (excluding high income)",
            "entity_type": EntityType.REGION.value,
            "region_id": "NA",
            "region_name": "Aggregates",
            "income_group_id": "",
            "income_group_name": "Aggregates",
            "capital_city": "",
            "source_hash": "c",
        },
    ]
    for code, name in (
        ("CHN", "China"),
        ("IND", "India"),
        ("DEU", "Germany"),
        ("NGA", "Nigeria"),
        ("JPN", "Japan"),
        ("ARG", "Argentina"),
    ):
        entities.append(
            {
                "entity_code": code,
                "iso2_code": code[:2],
                "name": name,
                "entity_type": EntityType.COUNTRY.value,
                "region_id": "EAS",
                "region_name": "East Asia",
                "income_group_id": "UMC",
                "income_group_name": "Upper middle income",
                "capital_city": "",
                "source_hash": code.lower(),
            }
        )
    indicators = []
    from quasar2.wdi.catalog import CI_INDICATORS

    for spec in CI_INDICATORS:
        indicators.append(
            {
                "indicator_id": spec.indicator_id,
                "name": spec.aliases[0].title() if spec.aliases else spec.indicator_id,
                "unit": spec.unit,
                "source_note": spec.topic,
                "source_organization": "World Bank",
                "topics": [spec.topic],
                "source_hash": spec.indicator_id,
            }
        )
    observations = []
    for spec in CI_INDICATORS:
        for entity in entities:
            for year, missing in (("2020", False), ("2021", False), ("2022", entity["entity_code"] == "NGA" and spec.indicator_id == "SE.ADT.LITR.ZS")):
                observations.append(
                    {
                        "indicator_id": spec.indicator_id,
                        "entity_code": entity["entity_code"],
                        "period": year,
                        "value_raw": None if missing else "100.5",
                        "value_numeric": None if missing else (8917.67 if spec.indicator_id == "NY.GDP.PCAP.CD" and entity["entity_code"] == "BRA" and year == "2022" else 100.5),
                        "observation_status": ObservationStatus.NOT_AVAILABLE.value if missing else ObservationStatus.OBSERVED.value,
                        "obs_status_source": "",
                        "decimal": 1,
                        "source_hash": f"{spec.indicator_id}{entity['entity_code']}{year}",
                    }
                )
    entity_n, entity_h = write_jsonl(paths["entities"], entities)
    ind_n, ind_h = write_jsonl(paths["indicators"], indicators)
    obs_n, obs_h = write_jsonl(paths["observations"], observations)
    attribution = "# World Bank WDI attribution\n\nOffline CI fixture derived from WDI schema; live snapshots replace this for external validity.\n"
    paths["attribution"].parent.mkdir(parents=True, exist_ok=True)
    paths["attribution"].write_text(attribution, encoding="utf-8")
    from quasar2.wdi.normalize import sha256_bytes

    created = utc_now()
    manifest = {
        "snapshot_id": "wdi-ci-offline-fixture",
        "source": "worldbank_wdi",
        "source_id": 2,
        "api_version": "2",
        "stage": "ci",
        "created_at": created,
        "completed_at": created,
        "request_count": 0,
        "row_counts": {
            "entities": entity_n,
            "indicators": ind_n,
            "observations": obs_n,
            "observed": sum(1 for row in observations if row["observation_status"] == "OBSERVED"),
            "not_available": sum(1 for row in observations if row["observation_status"] == "NOT_AVAILABLE"),
        },
        "indicator_count": ind_n,
        "country_entity_count": sum(1 for row in entities if row["entity_type"] == "COUNTRY"),
        "period_range": ["2020", "2022"],
        "schema_versions": {"snapshot": "2.4.0", "normalized": "2.4.0"},
        "software_commit": "offline-fixture",
        "status": "COMPLETE",
        "hashes": {
            "entities": entity_h,
            "indicators": ind_h,
            "observations": obs_h,
            "attribution": sha256_bytes(attribution.encode("utf-8")),
        },
        "errors": [],
        "fixture": True,
    }
    write_json(paths["manifest"], manifest)
    write_json(paths["validation"], {"ok": True, "errors": [], "fixture": True})
    return manifest
