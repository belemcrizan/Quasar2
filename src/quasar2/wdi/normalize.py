"""Deterministic WDI record normalization. Missing values stay missing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from quasar2.wdi.taxonomy import EntityType, ObservationStatus, classify_entity


def canonical_text_bytes(payload: bytes) -> bytes:
    """Normalize newlines to LF so Windows CRLF checkouts hash like Unix.

    Immutable snapshot hashes are defined over LF-encoded UTF-8 text. Git
    ``core.autocrlf`` must not change those hashes.
    """

    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_canonical_text(payload: bytes) -> str:
    return sha256_bytes(canonical_text_bytes(payload))


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_entity(raw: dict[str, Any]) -> dict[str, Any]:
    entity_type = classify_entity(raw)
    region = raw.get("region") or {}
    income = raw.get("incomeLevel") or {}
    return {
        "entity_code": str(raw.get("id") or "").upper(),
        "iso2_code": str(raw.get("iso2Code") or ""),
        "name": str(raw.get("name") or ""),
        "entity_type": entity_type.value,
        "region_id": str(region.get("id") or ""),
        "region_name": str(region.get("value") or ""),
        "income_group_id": str(income.get("id") or ""),
        "income_group_name": str(income.get("value") or ""),
        "capital_city": str(raw.get("capitalCity") or ""),
        "source_hash": sha256_json(raw),
    }


def normalize_indicator(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "indicator_id": str(raw.get("id") or ""),
        "name": str(raw.get("name") or ""),
        "unit": str(raw.get("unit") or ""),
        "source_note": str(raw.get("sourceNote") or ""),
        "source_organization": str(raw.get("sourceOrganization") or ""),
        "topics": tuple(
            str(topic.get("value") or "")
            for topic in (raw.get("topics") or [])
            if isinstance(topic, dict)
        ),
        "source_hash": sha256_json(raw),
    }


def normalize_observation(raw: dict[str, Any]) -> dict[str, Any]:
    indicator = raw.get("indicator") or {}
    country = raw.get("country") or {}
    indicator_id = str(indicator.get("id") or "")
    entity_code = str(raw.get("countryiso3code") or country.get("id") or "").upper()
    period = str(raw.get("date") or "")
    raw_value = raw.get("value")
    numeric = None
    status = ObservationStatus.NOT_AVAILABLE.value
    if raw_value is None:
        status = ObservationStatus.NOT_AVAILABLE.value
    else:
        try:
            numeric = float(raw_value)
            status = ObservationStatus.OBSERVED.value
        except (TypeError, ValueError):
            status = ObservationStatus.MALFORMED_SOURCE_RECORD.value
    return {
        "indicator_id": indicator_id,
        "entity_code": entity_code,
        "period": period,
        "value_raw": None if raw_value is None else str(raw_value),
        "value_numeric": numeric,
        "observation_status": status,
        "obs_status_source": str(raw.get("obs_status") or ""),
        "decimal": raw.get("decimal"),
        "source_hash": sha256_json(raw),
    }


def latest_available(observations: list[dict[str, Any]], *, indicator_id: str, entity_code: str) -> dict[str, Any] | None:
    candidates = [
        item
        for item in observations
        if item["indicator_id"] == indicator_id
        and item["entity_code"] == entity_code
        and item["observation_status"] == ObservationStatus.OBSERVED.value
        and item["period"].isdigit()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: int(item["period"]))


def resolve_period(
    observations: list[dict[str, Any]],
    *,
    indicator_id: str,
    entity_code: str,
    requested: str,
) -> dict[str, Any]:
    """Resolve exact year or latest-available. Never silently swap exact years."""

    if requested == "latest":
        found = latest_available(observations, indicator_id=indicator_id, entity_code=entity_code)
        if found is None:
            return {
                "observation_status": ObservationStatus.NOT_AVAILABLE.value,
                "period": None,
                "disclosed_period": None,
                "rule": "latest_available",
            }
        return {
            **found,
            "disclosed_period": found["period"],
            "rule": "latest_available",
        }
    matches = [
        item
        for item in observations
        if item["indicator_id"] == indicator_id
        and item["entity_code"] == entity_code
        and item["period"] == requested
    ]
    if not matches:
        return {
            "indicator_id": indicator_id,
            "entity_code": entity_code,
            "period": requested,
            "value_numeric": None,
            "observation_status": ObservationStatus.UNSUPPORTED_PERIOD.value
            if not any(
                item["indicator_id"] == indicator_id and item["entity_code"] == entity_code
                for item in observations
            )
            else ObservationStatus.NOT_AVAILABLE.value,
            "disclosed_period": requested,
            "rule": "exact_year",
        }
    chosen = matches[0]
    return {**chosen, "disclosed_period": requested, "rule": "exact_year"}
