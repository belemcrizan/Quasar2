"""Phase A1: matched RESCUE / OVERTHINKING decomposition.

Hypothesis: additional QUASAR compute is not uniformly helpful. This module
explains where FAST is already correct (overthinking) and where QUASAR
rescues FAST, without fitting a new gate on sealed_test.
"""

from __future__ import annotations

from collections import defaultdict
import math
import random
import statistics
from typing import Any, Mapping, Sequence

from quasar2.analysis.io_util import parse_float
from quasar2.analysis.matching import (
    ANALYSIS_SPLITS,
    PROPOSAL_SPLITS,
    SEALED_SPLITS,
    as_correct,
    numeric_feature,
)
from quasar2.failures.taxonomy import four_way_class, primary_failure_class, secondary_failure_labels
from quasar2.gate.complexity import RetrievalSignals, evaluate_gate
from quasar2.v24.artifacts import paired_mean_ci, percentile

FEATURE_COLUMNS = (
    "top1_score",
    "top2_score",
    "margin",
    "entropy",
    "complexity_score",
    "ambiguity_score",
    "open_set_score",
    "unknown_score",
    "missingness",
    "hypothesis_disagreement",
    "retriever_disagreement",
    "retrieval_calls",
    "latency_ms",
    "compute_proxy",
)

DECOMP_FIELDS = (
    "backend",
    "snapshot_id",
    "query_id",
    "canonical_intent_id",
    "split",
    "split_family_id",
    "used_for_feature_ranking",
    "used_for_threshold_proposal",
    "query_text",
    "domain",
    "language",
    "recoverability",
    "task_type",
    "ground_truth",
    "fast_policy",
    "quasar_policy",
    "gated_policy",
    "fast_prediction",
    "quasar_prediction",
    "gated_prediction",
    "fast_action",
    "quasar_action",
    "gated_action",
    "fast_correct",
    "quasar_correct",
    "gated_correct",
    "fast_score",
    "fast_margin",
    "top1_score",
    "top2_score",
    "margin",
    "entropy",
    "complexity_score",
    "ambiguity_score",
    "open_set_score",
    "unknown_score",
    "missingness",
    "hypothesis_disagreement",
    "retriever_disagreement",
    "retrieval_calls",
    "quasar_retrieval_calls",
    "latency_ms",
    "quasar_latency_ms",
    "compute_proxy",
    "quasar_compute_proxy",
    "gate_route",
    "gated_route",
    "action_history",
    "belief_state",
    "four_way_class",
    "failure_class",
    "secondary_labels",
    "missing_feature_flags",
)


def _prediction(row: Mapping[str, Any]) -> str:
    action = str(row.get("action") or "")
    if action:
        return action
    return str(row.get("reason_code") or "")


def _ground_truth(instance: Mapping[str, Any]) -> str:
    intents = instance.get("acceptable_intents") or ()
    if not intents:
        return ""
    first = intents[0]
    return "|".join(
        str(first.get(key) or "")
        for key in ("indicator_id", "entity_code", "entity_type", "period", "unit")
    )


def _missingness(recoverability: str) -> float:
    mapping = {
        "CLEAR": 0.0,
        "SOURCE_RECOVERABLE": 0.35,
        "USER_RESOLVABLE": 0.55,
        "OPEN_SET": 0.9,
        "UNRECOVERABLE_MISSING": 1.0,
        "SOURCE_MISSING": 0.8,
    }
    return mapping.get(recoverability, 0.5)


def _gate_features(query: str, fast: Mapping[str, Any]) -> dict[str, Any]:
    scores = []
    for key in ("top1_score", "top2_score"):
        value = parse_float(fast.get(key))
        if value is not None:
            scores.append(value)
    decision = evaluate_gate(query, RetrievalSignals(scores=tuple(scores)) if scores else None)
    return {
        "top1_score": decision.top1_score if scores else parse_float(fast.get("top1_score")),
        "top2_score": decision.top2_score if scores else parse_float(fast.get("top2_score")),
        "margin": decision.margin if scores else parse_float(fast.get("margin")),
        "entropy": decision.entropy if scores else parse_float(fast.get("entropy")),
        "query_gate_complexity": decision.complexity_score,
        "query_gate_ambiguity": decision.ambiguity_score,
        "query_gate_open_set": decision.open_set_score,
        "query_gate_route": decision.route,
    }


def decompose_pair(pair: Mapping[str, Any]) -> dict[str, Any]:
    fast = pair["fast"]
    quasar = pair["quasar"]
    gated = pair.get("gated") or {}
    instance = pair.get("instance") or {}
    query_text = str(instance.get("query_text") or fast.get("query_text") or "")
    recoverability = str(
        instance.get("recoverability") or fast.get("recoverability") or ""
    )
    split = str(instance.get("split") or fast.get("split") or "")
    family = str(
        instance.get("canonical_intent_id")
        or fast.get("canonical_intent_id")
        or pair["query_id"]
    )
    fast_ok = as_correct(fast)
    quasar_ok = as_correct(quasar)
    gated_ok = as_correct(gated) if gated else None
    outcome = four_way_class(fast_ok, quasar_ok)
    extra_gate = _gate_features(query_text, fast)
    complexity = numeric_feature(fast, "complexity_score")
    ambiguity = numeric_feature(fast, "ambiguity_score")
    open_set = numeric_feature(fast, "open_set_score")
    unknown = numeric_feature(fast, "unknown_score")
    q_unknown = numeric_feature(quasar, "unknown_score")
    disagreement = None
    if unknown is not None and q_unknown is not None:
        disagreement = abs(unknown - q_unknown)
    top1 = extra_gate["top1_score"]
    top2 = extra_gate["top2_score"]
    missing_flags = []
    if top1 is None:
        missing_flags.append("top1_score")
    if top2 is None:
        missing_flags.append("top2_score")
    if extra_gate["margin"] is None:
        missing_flags.append("margin")
    if extra_gate["entropy"] is None:
        missing_flags.append("entropy")
    if not query_text:
        missing_flags.append("query_text")
    if not gated:
        missing_flags.append("gated")
    row = {
        "backend": pair["backend"],
        "snapshot_id": pair.get("snapshot_id") or "",
        "query_id": pair["query_id"],
        "canonical_intent_id": family,
        "split": split,
        "split_family_id": family,
        "used_for_feature_ranking": split in ANALYSIS_SPLITS,
        "used_for_threshold_proposal": split in PROPOSAL_SPLITS,
        "query_text": query_text,
        "domain": str(fast.get("domain") or instance.get("domain") or "wdi"),
        "language": str(instance.get("language") or fast.get("language") or ""),
        "recoverability": recoverability,
        "task_type": str(fast.get("task_type") or ""),
        "ground_truth": _ground_truth(instance),
        "fast_policy": fast.get("policy"),
        "quasar_policy": quasar.get("policy"),
        "gated_policy": gated.get("policy") if gated else "",
        "fast_prediction": _prediction(fast),
        "quasar_prediction": _prediction(quasar),
        "gated_prediction": _prediction(gated) if gated else "",
        "fast_action": fast.get("action"),
        "quasar_action": quasar.get("action"),
        "gated_action": gated.get("action") if gated else "",
        "fast_correct": fast_ok,
        "quasar_correct": quasar_ok,
        "gated_correct": gated_ok if gated_ok is not None else "",
        "fast_score": complexity,
        "fast_margin": extra_gate["margin"] if extra_gate["margin"] is not None else ambiguity,
        "top1_score": top1 if top1 is not None else "",
        "top2_score": top2 if top2 is not None else "",
        "margin": extra_gate["margin"] if extra_gate["margin"] is not None else "",
        "entropy": extra_gate["entropy"] if extra_gate["entropy"] is not None else "",
        "complexity_score": complexity if complexity is not None else extra_gate["query_gate_complexity"],
        "ambiguity_score": ambiguity if ambiguity is not None else extra_gate["query_gate_ambiguity"],
        "open_set_score": open_set if open_set is not None else extra_gate["query_gate_open_set"],
        "unknown_score": unknown if unknown is not None else "",
        "missingness": _missingness(recoverability),
        "hypothesis_disagreement": disagreement if disagreement is not None else "",
        "retriever_disagreement": (
            numeric_feature(fast, "retriever_disagreement")
            if numeric_feature(fast, "retriever_disagreement") is not None
            else ""
        ),
        "retrieval_calls": numeric_feature(fast, "retrieval_calls"),
        "quasar_retrieval_calls": numeric_feature(quasar, "retrieval_calls"),
        "latency_ms": numeric_feature(fast, "latency_ms"),
        "quasar_latency_ms": numeric_feature(quasar, "latency_ms"),
        "compute_proxy": numeric_feature(fast, "compute_proxy"),
        "quasar_compute_proxy": numeric_feature(quasar, "compute_proxy"),
        "gate_route": fast.get("gate_route") or extra_gate["query_gate_route"],
        "gated_route": gated.get("gate_route") if gated else "",
        "action_history": f"{fast.get('action')}|{quasar.get('action')}"
        + (f"|{gated.get('action')}" if gated else ""),
        "belief_state": f"unknown_fast={unknown}|unknown_quasar={q_unknown}",
        "four_way_class": outcome.label,
        "secondary_labels": "",
        "missing_feature_flags": ",".join(missing_flags),
    }
    extras = secondary_failure_labels(row)
    row["secondary_labels"] = "|".join(extras)
    row["failure_class"] = primary_failure_class(outcome.label, extras)
    return row


def _rate_ci(flags: Sequence[bool]) -> dict[str, float]:
    n = len(flags)
    if n == 0:
        return {"n": 0.0, "rate": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    values = [1.0 if item else 0.0 for item in flags]
    zeros = [0.0] * n
    stats = paired_mean_ci(values, zeros)
    return {
        "n": float(n),
        "rate": sum(values) / n,
        "ci_low": stats["ci_low"],
        "ci_high": stats["ci_high"],
    }


def summarize_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    counts = {label: 0 for label in ("BOTH_CORRECT", "OVERTHINKING", "RESCUE", "BOTH_WRONG")}
    for row in rows:
        counts[str(row["four_way_class"])] += 1
    fast_wrong = [row for row in rows if not bool(row["fast_correct"])]
    rescue_given_wrong = (
        sum(1 for row in fast_wrong if row["four_way_class"] == "RESCUE") / len(fast_wrong)
        if fast_wrong
        else 0.0
    )
    overthink_given_right = (
        sum(1 for row in rows if row["four_way_class"] == "OVERTHINKING" and bool(row["fast_correct"]))
        / sum(1 for row in rows if bool(row["fast_correct"]))
        if any(bool(row["fast_correct"]) for row in rows)
        else 0.0
    )
    rates = {
        "n": n,
        "BothCorrectRate": counts["BOTH_CORRECT"] / n if n else 0.0,
        "OverthinkingRate": counts["OVERTHINKING"] / n if n else 0.0,
        "RescueRate": counts["RESCUE"] / n if n else 0.0,
        "BothWrongRate": counts["BOTH_WRONG"] / n if n else 0.0,
        "BeneficialReasoningRate": rescue_given_wrong,
        "OverthinkingAmongFastCorrect": overthink_given_right,
        "counts": counts,
        "BothCorrect": _rate_ci([row["four_way_class"] == "BOTH_CORRECT" for row in rows]),
        "Overthinking": _rate_ci([row["four_way_class"] == "OVERTHINKING" for row in rows]),
        "Rescue": _rate_ci([row["four_way_class"] == "RESCUE" for row in rows]),
        "BothWrong": _rate_ci([row["four_way_class"] == "BOTH_WRONG" for row in rows]),
    }
    if n:
        observed = sum(counts.values())
        if observed != n:
            raise ValueError("Four-way classes are not exhaustive")
        if sum(1 for row in rows if row["four_way_class"] not in counts) != 0:
            raise ValueError("Unknown four-way class")
    return rates


def reconcile_intent_exact(
    rows: Sequence[Mapping[str, Any]],
    summaries_by_snapshot: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    issues: list[str] = []
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["backend"]), str(row.get("snapshot_id") or ""))].append(row)
    for (backend, snapshot), group in grouped.items():
        summaries = summaries_by_snapshot.get(snapshot) or {}
        n = len(group)
        fast_rate = sum(bool(row["fast_correct"]) for row in group) / n if n else 0.0
        quasar_rate = sum(bool(row["quasar_correct"]) for row in group) / n if n else 0.0
        for key, observed in ((f"{backend}|fast_only", fast_rate), (f"{backend}|top1", fast_rate)):
            if key in summaries:
                reported_n = summaries[key].get("n")
                if reported_n is not None and int(reported_n) != n:
                    continue
                reported = float(summaries[key]["intent_exact"])
                if abs(reported - observed) > 1e-9:
                    issues.append(
                        f"{snapshot} {key} intent_exact {reported} != matched FAST {observed}"
                    )
        for key, observed in ((f"{backend}|quasar_always", quasar_rate), (f"{backend}|v24", quasar_rate)):
            if key in summaries:
                reported_n = summaries[key].get("n")
                if reported_n is not None and int(reported_n) != n:
                    continue
                reported = float(summaries[key]["intent_exact"])
                if abs(reported - observed) > 1e-9:
                    issues.append(
                        f"{snapshot} {key} intent_exact {reported} != matched QUASAR {observed}"
                    )
    return issues


def _cohens_d(positive: Sequence[float], other: Sequence[float]) -> float | None:
    if len(positive) < 2 or len(other) < 2:
        return None
    mp = statistics.fmean(positive)
    mo = statistics.fmean(other)
    vp = statistics.pvariance(positive)
    vo = statistics.pvariance(other)
    pooled = math.sqrt((vp + vo) / 2.0)
    if pooled == 0:
        return 0.0
    return (mp - mo) / pooled


def feature_associations(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Exploratory associations on calibration/development only. Not causal."""

    eligible = [row for row in rows if row.get("used_for_feature_ranking")]
    results: list[dict[str, Any]] = []
    backends = sorted({str(row["backend"]) for row in eligible})
    for backend in backends:
        snapshots = sorted({str(row.get("snapshot_id") or "") for row in eligible if row["backend"] == backend})
        for snapshot in snapshots:
            subset = [
                row
                for row in eligible
                if row["backend"] == backend and str(row.get("snapshot_id") or "") == snapshot
            ]
            label = f"{backend}|{snapshot}" if snapshot else backend
            for target in ("RESCUE", "OVERTHINKING"):
                pos = [row for row in subset if row["four_way_class"] == target]
                neg = [row for row in subset if row["four_way_class"] != target]
                for feature in FEATURE_COLUMNS:
                    pvals = [parse_float(row.get(feature)) for row in pos]
                    nvals = [parse_float(row.get(feature)) for row in neg]
                    pvals_f = [value for value in pvals if value is not None]
                    nvals_f = [value for value in nvals if value is not None]
                    base = {
                        "backend": label,
                        "target": target,
                        "feature": feature,
                        "n_positive": len(pvals_f),
                        "n_other": len(nvals_f),
                        "split_scope": "calibration+development",
                        "status": "EXPLORATORY",
                        "used_sealed_test": False,
                    }
                    if not pvals_f or not nvals_f:
                        results.append(
                            {
                                **base,
                                "mean_positive": None,
                                "mean_other": None,
                                "difference": None,
                                "cohens_d": None,
                                "ci_low": None,
                                "ci_high": None,
                            }
                        )
                        continue
                    observed = statistics.fmean(pvals_f) - statistics.fmean(nvals_f)
                    rng = random.Random(42)
                    diffs = []
                    for _ in range(1000):
                        sample_p = [pvals_f[rng.randrange(len(pvals_f))] for _ in range(len(pvals_f))]
                        sample_n = [nvals_f[rng.randrange(len(nvals_f))] for _ in range(len(nvals_f))]
                        diffs.append(statistics.fmean(sample_p) - statistics.fmean(sample_n))
                    results.append(
                        {
                            **base,
                            "mean_positive": statistics.fmean(pvals_f),
                            "mean_other": statistics.fmean(nvals_f),
                            "difference": observed,
                            "cohens_d": _cohens_d(pvals_f, nvals_f),
                            "ci_low": percentile(diffs, 0.025),
                            "ci_high": percentile(diffs, 0.975),
                        }
                    )
    results.sort(key=lambda item: (item["backend"], item["target"], abs(item["cohens_d"] or 0.0)), reverse=True)
    return results


def propose_backend_gate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Candidate thresholds from calibration only. Do not apply to sealed_test."""

    proposals: dict[str, Any] = {}
    eligible = [row for row in rows if row.get("used_for_threshold_proposal")]
    groups = sorted({(str(row["backend"]), str(row.get("snapshot_id") or "")) for row in eligible})
    for backend, snapshot in groups:
        subset = [
            row
            for row in eligible
            if row["backend"] == backend and str(row.get("snapshot_id") or "") == snapshot
        ]
        key = f"{backend}|{snapshot}" if snapshot else backend
        rescue = [row for row in subset if row["four_way_class"] == "RESCUE"]
        over = [row for row in subset if row["four_way_class"] == "OVERTHINKING"]
        easy = [row for row in subset if row["four_way_class"] == "BOTH_CORRECT"]

        def _median(group: Sequence[Mapping[str, Any]], field: str) -> float | None:
            values = [parse_float(row.get(field)) for row in group]
            values_f = [value for value in values if value is not None]
            if not values_f:
                return None
            return float(statistics.median(values_f))

        proposals[key] = {
            "n_calibration": len(subset),
            "n_rescue": len(rescue),
            "n_overthinking": len(over),
            "n_both_correct": len(easy),
            "suggested_fast_if": {
                "ambiguity_score_max": _median(easy, "ambiguity_score"),
                "complexity_score_max": _median(easy, "complexity_score"),
                "missingness_max": _median(easy, "missingness"),
                "note": "Escalate toward QUASAR when ambiguity/complexity exceed BOTH_CORRECT medians.",
            },
            "suggested_quasar_if": {
                "ambiguity_score_min": _median(rescue, "ambiguity_score"),
                "unknown_score_min": _median(rescue, "unknown_score"),
                "missingness_min": _median(rescue, "missingness"),
            },
            "overthinking_profile": {
                "ambiguity_median": _median(over, "ambiguity_score"),
                "complexity_median": _median(over, "complexity_score"),
                "unknown_median": _median(over, "unknown_score"),
            },
            "model_family_next": ["logistic_regression", "decision_tree"],
            "do_not_fit_on": list(SEALED_SPLITS),
            "status": "EXPLORATORY_CANDIDATE",
            "claim": "Not a fitted gate. Calibration-only descriptive thresholds for PHASE A2.",
        }
    return proposals


def split_manifest(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    families: dict[str, dict[str, Any]] = {}
    for row in rows:
        family = str(row["split_family_id"])
        bucket = families.setdefault(
            family,
            {"split": row["split"], "query_ids": [], "backend": row["backend"]},
        )
        if bucket["split"] != row["split"]:
            bucket["conflict"] = True
        bucket["query_ids"].append(row["query_id"])
    by_split: dict[str, int] = defaultdict(int)
    for row in rows:
        by_split[str(row["split"])] += 1
    return {
        "grouping": "canonical_intent_id (aliases/paraphrases share a family)",
        "n_families": len(families),
        "rows_by_split": dict(by_split),
        "sealed_test_used_for_fitting": False,
        "families": {
            key: {
                "split": value["split"],
                "n_queries": len(value["query_ids"]),
                "conflict": bool(value.get("conflict")),
            }
            for key, value in sorted(families.items())
        },
    }


def rates_by_backend_and_split(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    keys = sorted({(str(row["backend"]), str(row.get("snapshot_id") or ""), str(row["split"])) for row in rows})
    for backend, snapshot, split in keys:
        subset = [
            row
            for row in rows
            if row["backend"] == backend
            and str(row.get("snapshot_id") or "") == snapshot
            and row["split"] == split
        ]
        out[f"{backend}|{snapshot}|{split}"] = summarize_rows(subset)
    backends = sorted({str(row["backend"]) for row in rows})
    snapshots = sorted({(str(row["backend"]), str(row.get("snapshot_id") or "")) for row in rows})
    for backend, snapshot in snapshots:
        subset = [
            row
            for row in rows
            if row["backend"] == backend and str(row.get("snapshot_id") or "") == snapshot
        ]
        block = summarize_rows(subset)
        block["snapshots"] = [snapshot]
        block["pooled_snapshots"] = False
        out[f"{backend}|{snapshot}|ALL"] = block
    for backend in backends:
        subset = [row for row in rows if row["backend"] == backend]
        snaps = sorted({str(row.get("snapshot_id") or "") for row in subset})
        block = summarize_rows(subset)
        block["snapshots"] = snaps
        block["pooled_snapshots"] = len(snaps) > 1
        out[f"{backend}|ALL"] = block
    return out
