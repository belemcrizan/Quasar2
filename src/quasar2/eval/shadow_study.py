"""Shadow evaluation of v2 recommenders on the frozen sanity fixture.

Executed legacy actions are unchanged. Counterfactual utilities use proxy kernels.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quasar2.benchmark import BenchmarkRunner
from quasar2.config import ProjectConfig
from quasar2.decision.kernels import bernoulli_support_kernels
from quasar2.decision.policies import MyopicVoIPolicy, SPRTInspiredPolicy, ThresholdPolicy
from quasar2.decision.shadow import recommended_action_v2_shadow
from quasar2.models.decision import Action
from quasar2.pipeline import QuasarPipeline


def classify_divergence(legacy: str, recommended: str, *, recoverability: float | None, entropy: float, unknown: float, cost: float | None) -> str:
    if legacy == recommended:
        return "agree"
    if unknown >= 0.45:
        return "open-set-driven"
    if recommended == "EXPLORE" and recoverability is not None and recoverability >= 0.25:
        return "recoverability-driven"
    if recommended in {"ASK", "EXPLORE"} and entropy >= 0.5:
        return "uncertainty-driven"
    if recommended == "ANALYZE":
        return "inference-driven"
    if cost is not None and recommended == "ANSWER" and legacy == "EXPLORE":
        return "cost-driven"
    if recommended == "DEFER":
        return "open-set-driven"
    if recoverability is not None and recoverability < 0.05 and recommended == "ASK":
        return "recoverability-driven"
    return "unclassified"


def run_shadow_study(
    config: ProjectConfig,
    *,
    limit: int | None = None,
    conditions: tuple[str, ...] = ("q0", "q1", "q2"),
    shadow_policy: str = "quadrant",
) -> dict[str, Any]:
    runner = BenchmarkRunner(config)
    pipeline = QuasarPipeline.from_config(config)
    pipeline.v2_shadow_enabled = True
    intents = runner.intents[:limit] if limit else runner.intents
    rows: list[dict[str, Any]] = []
    myopic = MyopicVoIPolicy()
    threshold = ThresholdPolicy()
    sprt = SPRTInspiredPolicy()
    for intent in intents:
        for condition in conditions:
            query = getattr(intent, condition)
            result = pipeline.run(query, intent.domain, ablation="full", observation_id=f"{intent.intent_id}:{condition}")
            telemetry = result.v2_telemetry
            assert telemetry is not None
            supports = {
                candidate.hypothesis.hypothesis_id: result.final_belief.probabilities.get(
                    candidate.hypothesis.hypothesis_id, 0.0
                )
                for candidate in result.candidates
            }
            # Prefer evidence-max support when present.
            for item in result.evidence:
                hid = getattr(item, "hypothesis_id", None)
                if hid is None:
                    continue
                supports[str(hid)] = max(float(supports.get(str(hid), 0.0)), float(item.support_score))
            kernels = bernoulli_support_kernels(supports) if supports else None
            belief = dict(result.final_belief.probabilities)
            unknown = float(belief.get("H_unknown", 0.0))
            entropy = result.final_belief.normalized_entropy
            rec_myopic = myopic.recommend(
                belief=belief,
                kernels=kernels,
                entropy=entropy,
                unknown_mass=unknown,
                inference_error=telemetry.inference_error,
                evidence_present=bool(result.evidence),
            )
            rec_thr = threshold.recommend(
                top_probability=result.final_belief.top_probability,
                margin=result.final_belief.margin,
                unknown_mass=unknown,
                entropy=entropy,
            )
            rec_sprt = sprt.recommend(
                belief=belief,
                kernels=kernels,
                entropy=entropy,
                unknown_mass=unknown,
                inference_error=telemetry.inference_error,
                evidence_present=bool(result.evidence),
            )
            recommended = telemetry.recommended_action_v2
            if shadow_policy == "myopic_voi":
                recommended = rec_myopic.selected_action
            elif shadow_policy == "threshold":
                recommended = rec_thr.selected_action
            elif shadow_policy == "sprt_inspired":
                recommended = rec_sprt.selected_action
            taxonomy = classify_divergence(
                result.decision.action.value,
                str(recommended),
                recoverability=telemetry.recoverability,
                entropy=entropy,
                unknown=unknown,
                cost=telemetry.cost,
            )
            proxy_cf = rec_myopic.voi_empirical
            rows.append(
                {
                    "intent_id": intent.intent_id,
                    "condition": condition,
                    "domain": intent.domain,
                    "legacy_action": result.decision.action.value,
                    "v2_quadrant": telemetry.recommended_action_v2,
                    "v2_threshold": rec_thr.selected_action,
                    "v2_myopic": rec_myopic.selected_action,
                    "v2_sprt": rec_sprt.selected_action,
                    "recommended": recommended,
                    "legacy_correct": result.predicted_hypothesis_id == intent.correct_hypothesis,
                    "predicted": result.predicted_hypothesis_id,
                    "gold": intent.correct_hypothesis,
                    "recoverability": telemetry.recoverability,
                    "voi": telemetry.voi,
                    "voi_empirical_proxy": proxy_cf,
                    "voi_bound_binary": rec_myopic.voi_bound_binary,
                    "entropy": entropy,
                    "margin": result.final_belief.margin,
                    "retrieval_calls": result.retrieval_calls,
                    "divergence": taxonomy,
                    "kernel_source": telemetry.kernel_source,
                }
            )
    matrix: Counter[tuple[str, str]] = Counter((row["legacy_action"], row["recommended"]) for row in rows)
    taxonomy_counts = Counter(row["divergence"] for row in rows)
    n = len(rows)
    agree = sum(1 for row in rows if row["legacy_action"] == row["recommended"])
    by_calls: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_calls.setdefault(int(row["retrieval_calls"]), []).append(row)
    equal_budget = {
        str(calls): {
            "n": len(items),
            "legacy_irr": sum(item["legacy_correct"] for item in items) / len(items),
            "ask_rate": sum(item["legacy_action"] == Action.ASK.value for item in items) / len(items),
        }
        for calls, items in sorted(by_calls.items())
    }
    return {
        "schema_version": "shadow_study.1",
        "n": n,
        "intents": len(intents),
        "conditions": list(conditions),
        "shadow_policy": shadow_policy,
        "agreement_rate": agree / max(1, n),
        "transition_matrix": [
            {"legacy": left, "recommended": right, "count": count}
            for (left, right), count in sorted(matrix.items())
        ],
        "divergence_taxonomy": dict(taxonomy_counts),
        "equal_budget_by_realized_calls": equal_budget,
        "notes": (
            "Counterfactual v2 correctness is NOT computed: EXPLORE/ASK were not executed. "
            "voi_empirical_proxy uses Bernoulli support kernels, not oracle P(O|H)."
        ),
        "records": rows,
    }


def write_shadow_study(dest: Path, payload: dict[str, Any]) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "shadow_study.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md = dest / "shadow_study.md"
    lines = [
        "# 120-query shadow study",
        "",
        f"N={payload['n']} shadow_policy={payload['shadow_policy']} agreement={payload['agreement_rate']:.3f}",
        "",
        "| legacy | recommended | count |",
        "|---|---|---|",
    ]
    for row in payload["transition_matrix"]:
        lines.append(f"| {row['legacy']} | {row['recommended']} | {row['count']} |")
    lines.extend(["", "## Divergence taxonomy", ""])
    for key, value in payload["divergence_taxonomy"].items():
        lines.append(f"- {key}: {value}")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
