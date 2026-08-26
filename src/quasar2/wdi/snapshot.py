"""Immutable WDI snapshot write/read. Completed snapshots are never mutated."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from quasar2.wdi.catalog import entities_for_stage, indicators_for_stage
from quasar2.wdi.client import WorldBankClient
from quasar2.wdi.normalize import (
    normalize_entity,
    normalize_indicator,
    normalize_observation,
    sha256_bytes,
    sha256_canonical_text,
    sha256_json,
)
from quasar2.wdi.taxonomy import EntityType


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8")
    path.write_bytes(payload)
    return sha256_bytes(payload)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, default=_json_default)
        for row in rows
    ]
    body = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    path.write_bytes(body)
    return len(lines), sha256_bytes(body)


def _json_default(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(type(value))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def snapshot_paths(root: Path) -> dict[str, Path]:
    return {
        "manifest": root / "snapshot_manifest.json",
        "validation": root / "validation_report.json",
        "attribution": root / "LICENSE_AND_ATTRIBUTION.md",
        "raw_countries": root / "raw" / "countries_or_entities",
        "raw_indicators": root / "raw" / "indicators",
        "raw_observations": root / "raw" / "observations",
        "raw_metadata": root / "raw" / "metadata",
        "entities": root / "normalized" / "entities.jsonl",
        "indicators": root / "normalized" / "indicators.jsonl",
        "observations": root / "normalized" / "observations.jsonl",
    }


def sync_slice(
    destination: Path,
    *,
    stage: str = "ci",
    source_id: int = 2,
    client: WorldBankClient | None = None,
    years: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Fetch a bounded WDI slice and write an immutable snapshot directory."""

    destination = destination.resolve()
    if (destination / "snapshot_manifest.json").exists():
        existing = json.loads((destination / "snapshot_manifest.json").read_text(encoding="utf-8"))
        if existing.get("status") == "COMPLETE":
            raise FileExistsError(f"Refusing to mutate completed snapshot at {destination}")
    client = client or WorldBankClient()
    indicators = indicators_for_stage(stage)
    entities = list(entities_for_stage(stage))
    from quasar2.wdi.catalog import CI_AGGREGATES, CI_YEARS, PILOT_YEARS

    entities.extend(CI_AGGREGATES)
    year_list = tuple(years or (CI_YEARS if stage == "ci" else PILOT_YEARS))
    paths = snapshot_paths(destination)
    for path in paths.values():
        if path.suffix == "":
            path.mkdir(parents=True, exist_ok=True)

    request_log: list[dict[str, Any]] = []
    raw_hashes: dict[str, str] = {}

    country_codes = ";".join(spec.entity_code for spec in entities)
    indicator_ids = [spec.indicator_id for spec in indicators]
    created_at = utc_now()

    responses, country_rows = client.paginate(
        f"country/{country_codes}",
        {"per_page": 1000},
    )
    raw_hashes["countries"] = _store_raw(paths["raw_countries"] / "countries.json", responses, request_log)

    indicator_rows: list[dict[str, Any]] = []
    for indicator_id in indicator_ids:
        responses, rows = client.paginate(f"indicator/{indicator_id}", {"per_page": 20})
        indicator_rows.extend(rows)
        raw_hashes[f"indicator_{indicator_id}"] = _store_raw(
            paths["raw_indicators"] / f"{indicator_id}.json",
            responses,
            request_log,
        )

    observation_rows: list[dict[str, Any]] = []
    date_range = f"{year_list[0]}:{year_list[-1]}"
    fetch_errors: list[str] = []
    for indicator_id in indicator_ids:
        try:
            responses, rows = client.paginate(
                f"country/{country_codes}/indicator/{indicator_id}",
                {"source": source_id, "date": date_range, "per_page": 1000},
            )
        except ValueError as error:
            fetch_errors.append(f"{indicator_id}: {error}")
            continue
        observation_rows.extend(rows)
        raw_hashes[f"obs_{indicator_id}"] = _store_raw(
            paths["raw_observations"] / f"{indicator_id}.json",
            responses,
            request_log,
        )

    write_json(paths["raw_metadata"] / "requests.json", request_log)

    entities_norm = [normalize_entity(row) for row in country_rows if isinstance(row, dict)]
    indicators_norm = [normalize_indicator(row) for row in indicator_rows if isinstance(row, dict)]
    observations_norm = [normalize_observation(row) for row in observation_rows if isinstance(row, dict)]

    entity_count, entity_hash = write_jsonl(paths["entities"], entities_norm)
    indicator_count, indicator_hash = write_jsonl(paths["indicators"], indicators_norm)
    observation_count, observation_hash = write_jsonl(paths["observations"], observations_norm)

    errors: list[str] = []
    warnings = list(fetch_errors)
    if entity_count < 8:
        errors.append(f"expected at least 8 entities, got {entity_count}")
    if indicator_count < 12:
        errors.append(f"expected at least 12 indicators, got {indicator_count}")
    observed = sum(1 for row in observations_norm if row["observation_status"] == "OBSERVED")
    missing = sum(1 for row in observations_norm if row["observation_status"] == "NOT_AVAILABLE")
    if observed == 0:
        errors.append("no OBSERVED values in snapshot")
    if missing == 0:
        errors.append("no NOT_AVAILABLE values; missingness untested")
    country_like = [row for row in entities_norm if row["entity_type"] == EntityType.COUNTRY.value]
    non_country = [row for row in entities_norm if row["entity_type"] != EntityType.COUNTRY.value]
    if not country_like:
        errors.append("no COUNTRY entities")
    if stage == "ci" and not non_country:
        errors.append("CI snapshot must include at least one non-country aggregate")

    attribution = (
        "# World Bank WDI attribution\n\n"
        "This snapshot contains World Development Indicators retrieved from the "
        "World Bank Indicators API V2, source ID 2.\n\n"
        "World Bank datasets are generally provided under CC BY 4.0 unless a "
        "dataset is specifically labeled otherwise. Additional dataset terms apply:\n"
        "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets\n\n"
        f"Snapshot created: {created_at}\n"
        "Source: World Bank World Development Indicators (source=2)\n"
        "API: https://api.worldbank.org/v2\n"
    )
    attr_hash = sha256_bytes(attribution.encode("utf-8"))
    paths["attribution"].write_text(attribution, encoding="utf-8")

    completed_at = utc_now()
    status = "FAILED" if errors else "COMPLETE"
    periods = sorted({row["period"] for row in observations_norm if row.get("period")})
    manifest = {
        "snapshot_id": f"wdi-{stage}-{created_at[:10]}-{sha256_json(indicator_ids)[:8]}",
        "source": "worldbank_wdi",
        "source_id": 2,
        "api_version": "2",
        "stage": stage,
        "created_at": created_at,
        "completed_at": completed_at,
        "request_count": len(request_log),
        "row_counts": {
            "entities": entity_count,
            "indicators": indicator_count,
            "observations": observation_count,
            "observed": observed,
            "not_available": missing,
        },
        "indicator_count": indicator_count,
        "country_entity_count": len(country_like),
        "period_range": [periods[0] if periods else None, periods[-1] if periods else None],
        "schema_versions": {"snapshot": "2.4.0", "normalized": "2.4.0"},
        "software_commit": "unknown",
        "status": status,
        "hashes": {
            "entities": entity_hash,
            "indicators": indicator_hash,
            "observations": observation_hash,
            "attribution": attr_hash,
            **raw_hashes,
        },
        "errors": errors,
        "warnings": warnings,
    }
    if status == "COMPLETE":
        write_json(paths["manifest"], manifest)
    else:
        write_json(destination / "snapshot_manifest.FAILED.json", manifest)
        raise RuntimeError("WDI snapshot validation failed: " + "; ".join(errors))
    write_json(
        paths["validation"],
        {"ok": True, "errors": [], "observed": observed, "not_available": missing},
    )
    return manifest


def _store_raw(path: Path, responses: list[Any], request_log: list[dict[str, Any]]) -> str:
    payload = [
        {
            "url": item.url,
            "status": item.status,
            "elapsed_ms": item.elapsed_ms,
            "sha256": sha256_bytes(item.body),
            "body": json.loads(item.body.decode("utf-8")),
        }
        for item in responses
    ]
    digest = write_json(path, payload)
    for item in responses:
        request_log.append(
            {
                "url": item.url,
                "status": item.status,
                "elapsed_ms": item.elapsed_ms,
                "sha256": sha256_bytes(item.body),
            }
        )
    return digest


def load_snapshot(root: Path) -> dict[str, Any]:
    paths = snapshot_paths(root)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETE":
        raise ValueError(f"Snapshot {root} is not COMPLETE")
    entities = load_jsonl(paths["entities"])
    indicators = load_jsonl(paths["indicators"])
    observations = load_jsonl(paths["observations"])
    for name, expected, actual_path in (
        ("entities", manifest["hashes"]["entities"], paths["entities"]),
        ("indicators", manifest["hashes"]["indicators"], paths["indicators"]),
        ("observations", manifest["hashes"]["observations"], paths["observations"]),
    ):
        raw = actual_path.read_bytes()
        digest = sha256_canonical_text(raw)
        if digest != expected and sha256_bytes(raw) != expected:
            raise ValueError(f"Hash mismatch for {name}: {digest} != {expected}")
    return {
        "manifest": manifest,
        "entities": entities,
        "indicators": indicators,
        "observations": observations,
        "root": root,
    }
