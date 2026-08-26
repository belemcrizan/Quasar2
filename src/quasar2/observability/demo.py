"""Offline incident demo cases. Status is derived from artifacts or live experimental runs."""

from __future__ import annotations

from typing import Any

from quasar2.datasets.ops_runbook import HYPOTHESES
from quasar2.observability import default_rescue_dir, load_run

DEMO_CASES: tuple[dict[str, str], ...] = (
    {
        "id": "fast_correct",
        "title": "Fast correct without deliberation",
        "symptom": "The starlight keeps dipping when something crosses the disk",
        "domain": "astronomy",
        "expected_class": "BOTH_CORRECT",
    },
    {
        "id": "rescue",
        "title": "FastWrong rescued",
        "symptom": "brightness oscillates with a characteristic period like a standard candle",
        "domain": "astronomy",
        "expected_class": "RESCUE",
    },
    {
        "id": "ask",
        "title": "ASK actually useful",
        "symptom": "the numbers look wrong after the deploy",
        "domain": "ops",
        "expected_class": "ASK",
    },
    {
        "id": "analyze",
        "title": "ANALYZE actually useful",
        "symptom": "same evidence, need a second look at competing hypotheses",
        "domain": "astronomy",
        "expected_class": "ANALYZE",
    },
    {
        "id": "verify",
        "title": "VERIFY actually useful",
        "symptom": "confirm the citation against an independent catalog",
        "domain": "astronomy",
        "expected_class": "VERIFY",
    },
    {
        "id": "defer",
        "title": "DEFER on open-set",
        "symptom": "please reset the billing SKU for tenant 7f3",
        "domain": "astronomy",
        "expected_class": "DEFER",
    },
    {
        "id": "both_wrong",
        "title": "BothWrong explained",
        "symptom": "the dip looks stellar but catalogs disagree",
        "domain": "astronomy",
        "expected_class": "BOTH_WRONG",
    },
)


def classify_demo_cases() -> dict[str, dict[str, Any]]:
    loaded = load_run(default_rescue_dir())
    anatomy = loaded.get("anatomy") or []
    by_class: dict[str, list] = {}
    for row in anatomy:
        by_class.setdefault(str(row.get("four_way_class")), []).append(row)
    analyze = ((loaded.get("analyze") or {}).get("prediction_changes")) if loaded.get("available") else None
    ask_beats = ((loaded.get("ask") or {}).get("beats_explore")) if loaded.get("available") else None
    defer_n = ((loaded.get("defer") or {}).get("defer_count")) if loaded.get("available") else None
    out: dict[str, dict[str, Any]] = {}
    out["fast_correct"] = {
        "status": "demonstrated" if by_class.get("BOTH_CORRECT") else "not_demonstrated",
        "note": f"BOTH_CORRECT rows={len(by_class.get('BOTH_CORRECT', []))}",
    }
    out["rescue"] = {
        "status": "demonstrated" if by_class.get("RESCUE") else "not_demonstrated",
        "note": f"RESCUE rows={len(by_class.get('RESCUE', []))}; predicted disc arm may be 0 while falsification rescued 1",
    }
    out["ask"] = {
        "status": "demonstrated" if (ask_beats or 0) > 0 else "not_demonstrated",
        "note": "ASK uses an evaluation simulator, not a live user. Shadow maturity.",
    }
    out["analyze"] = {
        "status": "demonstrated" if (analyze or 0) > 0 else "not_demonstrated",
        "note": "ANALYZE must freeze the evidence set. 0 prediction changes on the diagnostic sample is a negative.",
    }
    out["verify"] = {
        "status": "not_demonstrated",
        "note": "VERIFY remains DISABLED_BY_GATE: no independent verifier is wired.",
    }
    out["defer"] = {
        "status": "demonstrated" if (defer_n or 0) > 0 else "not_demonstrated",
        "note": "Open-set pack in Cycle 7A diagnostics.",
    }
    out["both_wrong"] = {
        "status": "demonstrated" if by_class.get("BOTH_WRONG") else "not_demonstrated",
        "note": f"BOTH_WRONG rows={len(by_class.get('BOTH_WRONG', []))}",
    }
    out["ops_hypotheses"] = {"count": len(HYPOTHESES), "maturity": "SCHEMA_FAITHFUL"}
    return out


def decide_runtime(query: str, domain: str) -> dict[str, Any]:
    """Deployment-valid decide: experimental rescue pipeline, runtime namespace only."""

    from quasar2.config import ProjectConfig
    from quasar2.rescue.policy import execute_selected, gated_policy_action
    from quasar2.rescue.runner import _build_rescue_pipeline
    from quasar2.rescue.trace import build_trace, compact_runtime_from_run, runtime_only

    config = ProjectConfig.load(None)
    pipeline, _, _, _ = _build_rescue_pipeline(config)
    probe = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
    top_gen = max((c.generation_score for c in probe.candidates), default=0.0)
    selected = gated_policy_action(
        entropy=probe.belief.normalized_entropy,
        margin=probe.belief.margin,
        unknown_mass=probe.belief.probabilities.get("H_unknown", 0.0),
        top_generation=top_gen,
    )
    outcome = execute_selected(pipeline, query, domain, selected)
    run = outcome.get("run") or probe
    runtime = compact_runtime_from_run(
        query=query,
        domain=domain,
        arm=str(outcome.get("arm") or run.arm),
        mode="predicted_hypothesis",
        predicted_id=str(outcome.get("predicted_id") or run.predicted_id or ""),
        action=run.action,
        retrieval_calls=run.retrieval_calls,
        seed_calls=run.seed_calls,
        explore_rounds=run.explore_rounds,
        belief_top=run.belief.top_hypothesis_id,
        entropy=run.belief.normalized_entropy,
        margin=run.belief.margin,
        selected_action=outcome["selected_action"],
        executed_action=outcome["executed_action"],
        document_ids=run.retrieved_ids[:12],
        costs={"exploration_cost": 0.10, "ask_cost": 0.28},
    )
    trace = runtime_only(build_trace(run_id="live-decide", runtime=runtime))
    return {
        "predicted_id": runtime["decision"]["predicted_id"],
        "selected_action": outcome["selected_action"],
        "executed_action": outcome["executed_action"],
        "trace": trace,
        "oracle_exposed": False,
    }
