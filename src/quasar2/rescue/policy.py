"""Experimental action contract. Does not rewrite the frozen v0.1.1 loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from quasar2.models.decision import Action
from quasar2.rescue.actions import analyze_only, defer_should_fire
from quasar2.rescue.pipeline import Arm, RescuePipeline, RescueRun

UNIMPLEMENTED = "UNIMPLEMENTED"
SHADOW = "SHADOW"
ELIGIBLE = "ELIGIBLE"
ACTIVE = "ACTIVE"
DISABLED_BY_GATE = "DISABLED_BY_GATE"

MATURITY_ORDER = (UNIMPLEMENTED, SHADOW, ELIGIBLE, ACTIVE, DISABLED_BY_GATE)

ACTION_TO_ARM: dict[str, Arm] = {
    "ANSWER": "fast",
    "BM25": "bm25",
    "DENSE": "dense",
    "HYBRID": "hybrid",
    "RERANK": "discriminative_rerank",
    "DISCRIMINATIVE": "falsification",
}

# Mechanism-test regimes: causal reason an action *could* win, not frequency in nature.
MECHANISM_REGIMES = (
    "ANSWER_OPTIMAL",
    "BM25_OPTIMAL",
    "DENSE_OPTIMAL",
    "DISCRIMINATIVE_OPTIMAL",
    "ANALYZE_OPTIMAL",
    "ASK_OPTIMAL",
    "VERIFY_OPTIMAL",
    "DEFER_OPTIMAL",
)


@dataclass(frozen=True, slots=True)
class ActionEstimate:
    name: str
    gain: float
    cost: float
    risk: float
    net_value: float
    maturity: str
    eligible: bool
    reason: str


@dataclass
class ActionCatalog:
    maturity: dict[str, str] = field(
        default_factory=lambda: {
            "ANSWER": ACTIVE,
            "BM25": ELIGIBLE,
            "DENSE": ELIGIBLE,
            "HYBRID": ELIGIBLE,
            "RERANK": ELIGIBLE,
            "DISCRIMINATIVE": ELIGIBLE,
            "ANALYZE": ELIGIBLE,
            "ASK": SHADOW,
            "DEFER": ELIGIBLE,
            "VERIFY": DISABLED_BY_GATE,
        }
    )
    verifier_available: bool = False

    def status(self, name: str) -> str:
        if name == "VERIFY" and not self.verifier_available:
            return DISABLED_BY_GATE
        return self.maturity.get(name, UNIMPLEMENTED)

    def selectable(self, name: str) -> bool:
        return self.status(name) in {ELIGIBLE, ACTIVE}


def estimate_action_table(
    *,
    entropy: float,
    margin: float,
    unknown_mass: float,
    top_generation: float,
    catalog: ActionCatalog | None = None,
) -> list[ActionEstimate]:
    catalog = catalog or ActionCatalog()
    rows: list[ActionEstimate] = []
    specs: tuple[tuple[str, float, float, float, str], ...] = (
        ("ANSWER", 1.0 - entropy, 0.0, 0.2 * entropy, "commit with current evidence"),
        ("BM25", 0.15 * entropy, 0.10, 0.05, "cheap lexical acquisition"),
        ("DENSE", 0.18 * entropy, 0.20, 0.08, "hashing dense; not a neural encoder"),
        ("HYBRID", 0.20 * entropy, 0.18, 0.07, "combine lexical and hashing channels"),
        ("RERANK", 0.22 * entropy, 0.22, 0.08, "heuristic discriminative rerank; neural CE optional"),
        ("DISCRIMINATIVE", 0.35 * entropy * (1.0 - margin), 0.25, 0.10, "falsification/contrast queries"),
        ("ANALYZE", 0.05 * entropy, 0.02, 0.02, "re-score frozen evidence; no new documents"),
        ("ASK", 0.40 * entropy, 0.28, 0.05, "shadow user simulator only"),
        ("DEFER", 0.0, 0.05, max(0.0, unknown_mass), "abstain when open-set risk dominates"),
        ("VERIFY", 0.0, 0.0, 0.0, "no independent verifier wired; not an ANALYZE alias"),
    )
    for name, gain, cost, risk, reason in specs:
        maturity = catalog.status(name)
        eligible = catalog.selectable(name)
        if name == "DEFER":
            eligible = eligible and defer_should_fire(
                entropy=entropy, unknown_mass=unknown_mass, top_generation=top_generation
            )
        net = gain - cost - 0.5 * risk if eligible else float("-inf")
        rows.append(
            ActionEstimate(
                name=name,
                gain=gain,
                cost=cost,
                risk=risk,
                net_value=net if eligible else float("-inf"),
                maturity=maturity,
                eligible=eligible,
                reason=reason,
            )
        )
    return rows


def select_action(estimates: Sequence[ActionEstimate]) -> ActionEstimate:
    eligible = [row for row in estimates if row.eligible]
    if not eligible:
        return next(row for row in estimates if row.name == "ANSWER")
    return max(eligible, key=lambda row: (row.net_value, -row.cost, row.name))


def map_executed_label(run: RescueRun, selected: str) -> str:
    if selected == "ANALYZE":
        return "ANALYZE"
    if selected == "DEFER":
        return "DEFER"
    if selected == "ASK":
        return "ASK"
    if selected == "ANSWER":
        return "ANSWER" if run.explore_rounds == 0 else run.arm.upper()
    return selected


def execute_selected(
    pipeline: RescuePipeline,
    query: str,
    domain: str,
    selected: str,
) -> dict[str, Any]:
    """Execute the selected action on the experimental rescue pipeline.

    Integration invariant: executed_action == selected_action.
    The frozen QuasarPipeline is not used here.
    """

    catalog = ActionCatalog()
    if not catalog.selectable(selected):
        raise PermissionError(f"action {selected} is {catalog.status(selected)} and cannot execute")
    if selected == "VERIFY":
        raise PermissionError("VERIFY is not an ANALYZE alias and has no verifier")
    if selected == "ANALYZE":
        analysis = analyze_only(pipeline, query, domain)
        if analysis["analyze_added_retrieval"] != 0:
            raise RuntimeError("ANALYZE acquired documents")
        return {
            "selected_action": "ANALYZE",
            "executed_action": "ANALYZE",
            "arm": "fast",
            "retrieval_delta": 0,
            "predicted_id": analysis["predicted_after"],
            "evidence_frozen": analysis["evidence_ids_before"] == analysis["evidence_ids_after"],
            "run": None,
        }
    if selected == "DEFER":
        run = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
        return {
            "selected_action": "DEFER",
            "executed_action": "DEFER",
            "arm": "fast",
            "retrieval_delta": 0,
            "predicted_id": None,
            "coverage": 0.0,
            "run": run,
        }
    if selected == "ASK":
        run = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
        return {
            "selected_action": "ASK",
            "executed_action": "ASK",
            "arm": "fast",
            "interaction_cost": 0.28,
            "predicted_id": run.predicted_id,
            "run": run,
        }
    arm = ACTION_TO_ARM[selected]
    run = pipeline.run(query, domain, arm=arm, mode="predicted_hypothesis")
    executed = "ANSWER" if selected == "ANSWER" else selected
    if selected == "ANSWER" and run.explore_rounds != 0:
        raise RuntimeError("ANSWER executed an explore round")
    if selected != "ANSWER" and run.arm != arm:
        raise RuntimeError(f"policy selected {selected} mapped to {arm} but ran {run.arm}")
    return {
        "selected_action": selected,
        "executed_action": executed,
        "arm": run.arm,
        "retrieval_calls": run.retrieval_calls,
        "predicted_id": run.predicted_id,
        "run": run,
    }


def gated_policy_action(
    *,
    entropy: float,
    margin: float,
    unknown_mass: float,
    top_generation: float,
    catalog: ActionCatalog | None = None,
) -> str:
    catalog = catalog or ActionCatalog()
    if catalog.selectable("DEFER") and defer_should_fire(
        entropy=entropy, unknown_mass=unknown_mass, top_generation=top_generation
    ):
        return "DEFER"
    estimates = estimate_action_table(
        entropy=entropy,
        margin=margin,
        unknown_mass=unknown_mass,
        top_generation=top_generation,
        catalog=catalog,
    )
    return select_action(estimates).name


def evaluate_gated_policy(
    pipeline: RescuePipeline,
    queries: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Run the experimental gated policy. Default v0.1.1 product policy is unchanged."""

    rows = []
    mismatches = 0
    for query, domain in queries:
        probe = pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
        top_gen = max((c.generation_score for c in probe.candidates), default=0.0)
        selected = gated_policy_action(
            entropy=probe.belief.normalized_entropy,
            margin=probe.belief.margin,
            unknown_mass=probe.belief.probabilities.get("H_unknown", 0.0),
            top_generation=top_gen,
        )
        outcome = execute_selected(pipeline, query, domain, selected)
        match = outcome["selected_action"] == outcome["executed_action"]
        mismatches += int(not match)
        rows.append(
            {
                "query": query,
                "domain": domain,
                "selected_action": outcome["selected_action"],
                "executed_action": outcome["executed_action"],
                "match": match,
                "fast_action": probe.action,
                "behavior_changed": outcome["selected_action"] != "ANSWER"
                or probe.action != Action.ANSWER.value,
            }
        )
    return {
        "n": len(rows),
        "mismatches": mismatches,
        "rows": rows,
        "policy_changes_execution": any(row["behavior_changed"] for row in rows),
        "frozen_loop_unchanged": True,
        "gate_c_policy": "FAIL" if mismatches else "TESTED_EXPERIMENTAL",
        "note": "Cycle 6 remains BLOCKED for product promotion; this is mechanism execution, not ΔNEU proof.",
    }


def action_registry() -> list[dict[str, str]]:
    catalog = ActionCatalog()
    return [
        {
            "name": name,
            "maturity": catalog.status(name),
            "semantics": {
                "ANSWER": "respond with current state",
                "BM25": "cheap lexical acquisition",
                "DENSE": "hashing semantic proxy",
                "HYBRID": "combine channels",
                "RERANK": "pay for posterior discrimination",
                "DISCRIMINATIVE": "contrastive/falsification queries",
                "ANALYZE": "internal recompute; no new evidence",
                "ASK": "user information; interaction cost",
                "VERIFY": "independent checker; disabled without verifier",
                "DEFER": "do not answer when risk exceeds benefit",
            }[name],
        }
        for name in (
            "ANSWER",
            "BM25",
            "DENSE",
            "HYBRID",
            "RERANK",
            "DISCRIMINATIVE",
            "ANALYZE",
            "ASK",
            "VERIFY",
            "DEFER",
        )
    ]
