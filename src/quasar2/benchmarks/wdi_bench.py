"""Deterministic QUASAR-Bench-WDI generation. Hidden labels stay on the instance, not policy input."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from quasar2.wdi.catalog import OPEN_SET_CONCEPTS, indicators_for_stage
from quasar2.wdi.normalize import resolve_period
from quasar2.wdi.snapshot import load_snapshot
from quasar2.wdi.taxonomy import EntityType, ObservationStatus


@dataclass(frozen=True, slots=True)
class BenchInstance:
    query_id: str
    canonical_intent_id: str
    query_text: str
    language: str
    period: str
    recoverability: str
    degradation_level: int
    factors: tuple[str, ...]
    split: str
    acceptable_intents: tuple[dict[str, Any], ...]
    expected_observation: dict[str, Any]
    user_owned_slots: tuple[str, ...] = ()

    def policy_query(self) -> dict[str, str]:
        return {"query_text": self.query_text, "language": self.language}


def _split_for(canonical_id: str) -> str:
    digest = int(hashlib.sha256(canonical_id.encode("utf-8")).hexdigest()[:8], 16)
    bucket = digest % 10
    if bucket == 0:
        return "sealed_test"
    if bucket <= 2:
        return "validation"
    if bucket <= 4:
        return "calibration"
    return "development"


def _observation(snapshot: dict[str, Any], indicator_id: str, entity_code: str, period: str) -> dict[str, Any]:
    resolved = resolve_period(
        snapshot["observations"],
        indicator_id=indicator_id,
        entity_code=entity_code,
        requested=period,
    )
    return {
        "status": resolved.get("observation_status"),
        "value": resolved.get("value_numeric"),
        "period": resolved.get("disclosed_period") or period,
        "relative_tolerance": 1e-6,
        "absolute_tolerance": 0.0,
        "value_ref": f"snapshot://{snapshot['manifest']['snapshot_id']}/{indicator_id}/{entity_code}/{period}",
    }


def build_benchmark(snapshot_dir: str | Path, *, stage: str = "ci", seed: int = 42) -> dict[str, Any]:
    snapshot = load_snapshot(Path(snapshot_dir))
    indicators = {row["indicator_id"]: row for row in snapshot["indicators"]}
    entities = {
        row["entity_code"]: row
        for row in snapshot["entities"]
        if row["entity_type"] == EntityType.COUNTRY.value
    }
    wanted = [spec for spec in indicators_for_stage("ci" if stage == "ci" else "pilot") if spec.indicator_id in indicators]
    countries = list(entities.values())
    if stage == "ci":
        countries = countries[:8]
        wanted = wanted[:12]
    else:
        countries = countries[:20]
        wanted = wanted[:30]
    years = ["2022", "2020", "2018"]
    instances: list[BenchInstance] = []
    canonical = 0
    for indicator in wanted:
        for entity in countries:
            canonical += 1
            canonical_id = f"wdi_{canonical:06d}"
            split = _split_for(canonical_id)
            period = years[canonical % len(years)]
            obs = _observation(snapshot, indicator.indicator_id, entity["entity_code"], period)
            intent = {
                "indicator_id": indicator.indicator_id,
                "entity_code": entity["entity_code"],
                "entity_type": entity["entity_type"],
                "period": period,
                "unit": indicator.unit,
            }
            name = indicator.name if hasattr(indicator, "name") else indicators[indicator.indicator_id]["name"]
            d0 = f"What was {name} for {entity['name']} in {period}?"
            d2 = f"How {indicator.aliases[0]} in {entity['name']} around {period}?" if indicator.aliases else d0
            d3 = f"How rich or developed was {entity['name']} in {period}?" if "GDP" in name.upper() or "gdp" in indicator.aliases[0] else f"What is the social outcome for {entity['name']} in {period} related to {indicator.topic}?"
            d5 = f"Tell me about {entity['name']} lately."
            pt = f"Qual era {name} de {entity['name']} em {period}?"
            variants = (
                (0, d0, "CLEAR", ("none",), "en"),
                (2, d2, "SOURCE_RECOVERABLE", ("indicator_abstraction",), "en"),
                (3, d3, "USER_RESOLVABLE" if "rich" in d3 else "SOURCE_RECOVERABLE", ("semantic",), "en"),
                (5, d5, "USER_RESOLVABLE", ("temporal", "semantic"), "en"),
                (0, pt, "CLEAR", ("language",), "pt"),
            )
            recoverability_missing = obs["status"] != ObservationStatus.OBSERVED.value
            for level, text, recover, factors, language in variants:
                instances.append(
                    BenchInstance(
                        query_id=f"{canonical_id}_d{level}_{language}",
                        canonical_intent_id=canonical_id,
                        query_text=text,
                        language=language,
                        period=period,
                        recoverability="DATA_UNAVAILABLE" if recoverability_missing and level == 0 else recover,
                        degradation_level=level,
                        factors=factors,
                        split=split,
                        acceptable_intents=(intent,),
                        expected_observation=obs,
                        user_owned_slots=("indicator_id",) if recover == "USER_RESOLVABLE" else (),
                    )
                )
            # Counterfactual: swap entity for Brazil vs USA when both exist.
            if entity["entity_code"] == "BRA" and "USA" in entities:
                usa_obs = _observation(snapshot, indicator.indicator_id, "USA", period)
                instances.append(
                    BenchInstance(
                        query_id=f"{canonical_id}_cf_entity_en",
                        canonical_intent_id=canonical_id,
                        query_text=f"What was {name} for the United States in {period}?",
                        language="en",
                        period=period,
                        recoverability="CLEAR",
                        degradation_level=0,
                        factors=("entity_swap",),
                        split=split,
                        acceptable_intents=(
                            {
                                **intent,
                                "entity_code": "USA",
                                "entity_type": entities["USA"]["entity_type"],
                            },
                        ),
                        expected_observation=usa_obs,
                    )
                )
    for index, (text, kind) in enumerate(OPEN_SET_CONCEPTS, start=1):
        instances.append(
            BenchInstance(
                query_id=f"open_{index:03d}_en",
                canonical_intent_id=f"open_{index:03d}",
                query_text=text,
                language="en",
                period="2022",
                recoverability="OPEN_SET",
                degradation_level=5,
                factors=(kind,),
                split="development",
                acceptable_intents=(),
                expected_observation={"status": "UNSUPPORTED_INDICATOR", "value": None},
            )
        )
    payload = {
        "schema_version": "2.4.0",
        "stage": stage,
        "seed": seed,
        "snapshot_id": snapshot["manifest"]["snapshot_id"],
        "n_canonical": canonical,
        "n_instances": len(instances),
        "instances": [asdict(item) for item in instances],
    }
    payload["hash"] = hashlib.sha256(
        json.dumps({"n": payload["n_instances"], "snapshot": payload["snapshot_id"], "seed": seed}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def write_benchmark(snapshot_dir: str | Path, destination: str | Path, *, stage: str = "ci") -> Path:
    payload = build_benchmark(snapshot_dir, stage=stage)
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
