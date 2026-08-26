"""WDI entity types, observation statuses, and time-resolution rules."""

from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    COUNTRY = "COUNTRY"
    ECONOMY = "ECONOMY"
    REGION = "REGION"
    INCOME_GROUP = "INCOME_GROUP"
    AGGREGATE = "AGGREGATE"
    UNKNOWN_ENTITY_TYPE = "UNKNOWN_ENTITY_TYPE"


class ObservationStatus(str, Enum):
    OBSERVED = "OBSERVED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED_INDICATOR = "UNSUPPORTED_INDICATOR"
    UNSUPPORTED_ENTITY = "UNSUPPORTED_ENTITY"
    UNSUPPORTED_PERIOD = "UNSUPPORTED_PERIOD"
    STALE_LATEST = "STALE_LATEST"
    SOURCE_ERROR = "SOURCE_ERROR"
    MALFORMED_SOURCE_RECORD = "MALFORMED_SOURCE_RECORD"


class DeferReason(str, Enum):
    OPEN_SET = "OPEN_SET"
    UNSUPPORTED_INTENT = "UNSUPPORTED_INTENT"
    DATA_NOT_AVAILABLE = "DATA_NOT_AVAILABLE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    EXTERNAL_AUTHORITY_REQUIRED = "EXTERNAL_AUTHORITY_REQUIRED"
    BUDGET_EXHAUSTED_UNSAFE = "BUDGET_EXHAUSTED_UNSAFE"
    POLICY_CONSTRAINT = "POLICY_CONSTRAINT"


def classify_entity(raw: dict) -> EntityType:
    """Map a World Bank country-endpoint record to a typed entity class.

    The country endpoint also returns regions, income groups, and other
    aggregates. Empty or ``NA`` region ids are treated as non-country.
    """

    region = raw.get("region") or {}
    region_id = str(region.get("id") or "").strip()
    region_value = str(region.get("value") or "").strip().lower()
    income = raw.get("incomeLevel") or {}
    income_id = str(income.get("id") or "").strip()
    entity_id = str(raw.get("id") or "").strip().upper()
    if region_value == "aggregates" or region_id in {"", "NA"}:
        if income_id in {"HIC", "UMC", "LMC", "LIC", "INX"} and entity_id == income_id:
            return EntityType.INCOME_GROUP
        if entity_id in _KNOWN_REGIONS:
            return EntityType.REGION
        return EntityType.AGGREGATE
    if len(entity_id) == 3:
        return EntityType.COUNTRY
    return EntityType.UNKNOWN_ENTITY_TYPE


_KNOWN_REGIONS = frozenset(
    {
        "AFE",
        "AFW",
        "ARB",
        "CEB",
        "CSS",
        "EAP",
        "EAR",
        "EAS",
        "ECA",
        "ECS",
        "EMU",
        "EUU",
        "LAC",
        "LCN",
        "LDC",
        "MEA",
        "MNA",
        "NAC",
        "OED",
        "PSS",
        "SAS",
        "SSA",
        "SSF",
        "WLD",
    }
)
