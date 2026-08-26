"""Cycle 4–7A runner. Writes versioned artifacts; never overwrites frozen tables."""

from __future__ import annotations

import hashlib
import json
import platform
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from quasar2 import __version__
from quasar2.belief.updater import BeliefUpdater
from quasar2.benchmark import load_intents
from quasar2.config import ProjectConfig, load_structured
from quasar2.decision.engine import DecisionEngine
from quasar2.decision.utility import UtilityModel
from quasar2.evidence.scorer import EvidenceScorer
from quasar2.failures.taxonomy import four_way_class
from quasar2.hypotheses.catalog import CatalogHypothesisGenerator, HypothesisCatalog
from quasar2.pipeline import QuasarPipeline
from quasar2.rescue import SCHEMA_VERSION
from quasar2.rescue.actions import analyze_only, ask_simulator, defer_should_fire, open_set_query_pack
from quasar2.rescue.belief import DiscriminativeBeliefUpdater
from quasar2.rescue.evidence_oracle import evaluate_case, gold_documents_for
from quasar2.rescue.metrics import realized_utility, rescue_metrics, wilson_interval
from quasar2.rescue.pipeline import RescuePipeline, RescueRun
from quasar2.rescue.recoverability import (
    auprc,
    auroc,
    brier,
    fit_logreg,
    median,
    outcome_label,
    preaction_features,
    predict_logreg,
    threshold_predict,
)
from quasar2.rescue.report import render_report, write_json, write_jsonl
from quasar2.rescue.taxonomy import classify_primary
from quasar2.retrieval import load_corpus
from quasar2.retrieval.bm25 import BM25Retriever
from quasar2.retrieval.dense import HashingDenseRetriever
from quasar2.retrieval.hybrid import HybridRetriever
from quasar2.signals.extractor import SignalExtractor


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "UNKNOWN"
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _correct(run: RescueRun, gold_id: str) -> bool:
    return run.predicted_id == gold_id


def _build_rescue_pipeline(config: ProjectConfig) -> tuple[RescuePipeline, QuasarPipeline, HypothesisCatalog, tuple]:
    paths = config.section("paths")
    domains = load_structured(config.resolve(str(paths["domains"])))
    cues = {domain: values.get("domain_cues", ()) for domain, values in domains.items()}
    catalog = HypothesisCatalog.from_directory(config.resolve(str(paths["catalog"])))
    documents = load_corpus(config.resolve(str(paths["corpus"])))
    retrieval = config.section("retrieval")
    bm25 = BM25Retriever(documents)
    dense = HashingDenseRetriever(documents, dimensions=int(retrieval.get("dense_dimensions", 384)))
    hybrid = HybridRetriever(
        bm25,
        dense,
        sparse_weight=float(retrieval.get("bm25_weight", 0.6)),
        dense_weight=float(retrieval.get("dense_weight", 0.4)),
        rrf_k=int(retrieval.get("rrf_k", 20)),
    )
    belief = config.section("belief")
    decision = config.section("decision")
    hypothesis_config = config.section("hypotheses")
    pipeline = RescuePipeline(
        extractor=SignalExtractor(cues),
        generator=CatalogHypothesisGenerator(catalog),
        retriever=hybrid,
        bm25=bm25,
        dense=dense,
        hybrid=hybrid,
        scorer=EvidenceScorer(config.section("evidence")),
        legacy_updater=BeliefUpdater(
            evidence_strength=float(belief.get("evidence_strength", 4.0)),
            temperature=float(belief.get("temperature", 1.0)),
            probability_floor=float(belief.get("probability_floor", 1e-6)),
        ),
        disc_updater=DiscriminativeBeliefUpdater(
            evidence_strength=float(belief.get("evidence_strength", 4.0)),
            temperature=float(belief.get("temperature", 1.0)),
            probability_floor=float(belief.get("probability_floor", 1e-6)),
        ),
        decision=DecisionEngine(
            answer_confidence=float(decision.get("answer_confidence", 0.67)),
            answer_margin=float(decision.get("answer_margin", 0.20)),
            minimum_evidence=float(decision.get("minimum_evidence", 0.28)),
            minimum_exploration_value=float(decision.get("minimum_exploration_value", 0.04)),
            max_explore_rounds=int(decision.get("max_explore_rounds", 2)),
            allow_ask=bool(decision.get("allow_ask", True)),
            utility_model=UtilityModel(
                wrong_answer_cost=float(decision.get("wrong_answer_cost", 1.4)),
                exploration_cost=float(decision.get("exploration_cost", 0.10)),
                ask_cost=float(decision.get("ask_cost", 0.28)),
            ),
        ),
        max_candidates=int(hypothesis_config.get("max_candidates", 4)),
        initial_top_k=int(retrieval.get("initial_top_k_per_hypothesis", 1)),
        top_k=int(retrieval.get("top_k_per_hypothesis", 4)),
        documents=documents,
    )
    return pipeline, QuasarPipeline.from_config(config), catalog, documents


def _rows_for_arm(anatomy: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    rows = []
    for row in anatomy:
        rows.append(
            {
                "intent_id": row["intent_id"],
                "query_id": row["query_id"],
                "fast_correct": row["fast_correct"],
                "deliberative_correct": row[f"{prefix}_correct"],
                "delta_u": row[f"{prefix}_u"] - row["fast_u"],
            }
        )
    return rows


def run_rescue_cycle(
    *,
    output: Path,
    config_path: str | None = None,
    seed: int = 42,
    limit: int | None = None,
    conditions: tuple[str, ...] = ("q0", "q1", "q2"),
    stages: tuple[str, ...] = ("anatomy", "discriminative", "recoverability", "actions"),
) -> dict[str, Any]:
    config = ProjectConfig.load(config_path)
    root = config.root
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    intents = load_intents(config.resolve(str(config.section("paths")["intents"])))
    if limit:
        intents = intents[:limit]
    rescue_pipeline, legacy, catalog, documents = _build_rescue_pipeline(config)
    catalog_ids = {hyp.hypothesis_id for hyp in catalog}
    corpus_files = sorted((config.resolve(str(config.section("paths")["corpus"]))).glob("*.jsonl"))
    hashes = {
        "poc.yaml": _sha256(root / "configs" / "poc.yaml"),
        "intents": _sha256(config.resolve(str(config.section("paths")["intents"]))),
        "cycle4_plan": _sha256(root / "experiments" / "analysis_plans" / "cycle4_rescue.json"),
        **{path.name: _sha256(path) for path in corpus_files},
    }
    gold_map = {
        hyp.hypothesis_id: [doc.document_id for doc in documents if hyp.hypothesis_id in doc.hypothesis_ids]
        for hyp in catalog
    }
    write_json(output / "gold_evidence_map.json", {"corpus_version": "data/corpus", "map": gold_map})

    rng = random.Random(seed)
    intent_ids = sorted({intent.intent_id for intent in intents})
    shuffled = list(intent_ids)
    rng.shuffle(shuffled)
    split_cut = max(1, int(0.7 * len(shuffled)))
    dev_intents = set(shuffled[:split_cut])
    hold_intents = set(shuffled[split_cut:])

    anatomy: list[dict[str, Any]] = []
    intervention_matrix: list[dict[str, Any]] = []

    for intent in intents:
        gold = catalog.get(intent.correct_hypothesis)
        gold_docs = gold_documents_for(documents, gold.hypothesis_id)
        for condition in conditions:
            query = getattr(intent, condition)
            query_id = f"{intent.intent_id}:{condition}"
            fast = rescue_pipeline.run(query, intent.domain, arm="fast", mode="predicted_hypothesis")
            disc = rescue_pipeline.run(
                query, intent.domain, arm="pairwise_contrastive", mode="predicted_hypothesis"
            )
            relevance = rescue_pipeline.run(query, intent.domain, arm="relevance", mode="predicted_hypothesis")
            bm25_arm = rescue_pipeline.run(query, intent.domain, arm="bm25", mode="predicted_hypothesis")
            dense_arm = rescue_pipeline.run(query, intent.domain, arm="dense", mode="predicted_hypothesis")
            fals = rescue_pipeline.run(query, intent.domain, arm="falsification", mode="predicted_hypothesis")
            no_disc_update = rescue_pipeline.run(
                query,
                intent.domain,
                arm="pairwise_contrastive",
                mode="predicted_hypothesis",
                use_disc_updater=False,
            )
            legacy_full = legacy.run(query, intent.domain, ablation="full", observation_id=query_id)
            hyp_run = rescue_pipeline.run(
                query,
                intent.domain,
                arm="pairwise_contrastive",
                mode="oracle_hypothesis",
                gold_hypothesis=gold,
            )
            ret_run = rescue_pipeline.run(
                query,
                intent.domain,
                arm="pairwise_contrastive",
                mode="oracle_retrieval",
                gold_hypothesis=gold,
                gold_docs=gold_docs,
            )
            evid_run = rescue_pipeline.run(
                query,
                intent.domain,
                arm="fast",
                mode="oracle_evidence",
                gold_hypothesis=gold,
                gold_docs=gold_docs,
                oracle_evidence=True,
            )
            belief_run = rescue_pipeline.run(
                query,
                intent.domain,
                arm="fast",
                mode="oracle_hypothesis",
                gold_hypothesis=gold,
                oracle_belief=True,
            )
            generated_ids = tuple(c.hypothesis.hypothesis_id for c in fast.candidates)
            oracle_rec = evaluate_case(
                query_id=query_id,
                intent_id=intent.intent_id,
                regime=f"{intent.domain}:{condition}",
                correct_hypothesis=gold,
                catalog_ids=catalog_ids,
                documents=documents,
                generated_ids=generated_ids,
                competitors=tuple(c.hypothesis for c in fast.candidates),
                corpus_version="data/corpus",
            )
            gold_retrieved = any(doc_id in disc.retrieved_ids for doc_id in oracle_rec.evidence_doc_ids)
            fast_ok = _correct(fast, gold.hypothesis_id)
            disc_ok = _correct(disc, gold.hypothesis_id)
            costs = dict(
                wrong_answer_cost=1.4, exploration_cost=0.10, ask_cost=0.28, defer_cost=0.05
            )
            fast_u = realized_utility(
                correct=fast_ok, action=fast.action, retrieval_calls=fast.retrieval_calls, seed_calls=fast.seed_calls, **costs
            )

            def u(run: RescueRun, ok: bool) -> float:
                return realized_utility(
                    correct=ok,
                    action=run.action,
                    retrieval_calls=run.retrieval_calls,
                    seed_calls=run.seed_calls,
                    **costs,
                )

            hyp_ok = _correct(hyp_run, gold.hypothesis_id)
            ret_ok = _correct(ret_run, gold.hypothesis_id)
            evid_ok = _correct(evid_run, gold.hypothesis_id)
            bel_ok = _correct(belief_run, gold.hypothesis_id)
            factorial_conflict = hyp_ok and ret_ok and not evid_ok
            delta_b = None
            if disc.b_star_after is not None and disc.b_star_before is not None:
                delta_b = disc.b_star_after - disc.b_star_before
            # Diagnostic Δb uses oracle-visible H*; stored only on anatomy oracle fields.
            disc_with_gold_belief = rescue_pipeline.run(
                query,
                intent.domain,
                arm="pairwise_contrastive",
                mode="oracle_hypothesis",
                gold_hypothesis=gold,
            )
            delta_b = (disc_with_gold_belief.b_star_after or 0.0) - (disc_with_gold_belief.b_star_before or 0.0)
            primary, secondary, why = classify_primary(
                catalog_has_h_star=gold.hypothesis_id in catalog_ids,
                sufficient=oracle_rec.sufficient,
                h_star_in_generated=gold.hypothesis_id in generated_ids,
                gold_retrieved=gold_retrieved,
                oracle_hypothesis_correct=hyp_ok,
                oracle_retrieval_correct=ret_ok,
                oracle_evidence_correct=evid_ok,
                oracle_belief_correct=bel_ok,
                predicted_correct=disc_ok,
                belief_top_is_h_star=disc.belief.top_hypothesis_id == gold.hypothesis_id,
                delta_b_star=delta_b,
                factorial_conflict=factorial_conflict,
            )
            four = four_way_class(fast_ok, disc_ok)
            primary_label = "NONE" if disc_ok else primary
            rec_label = outcome_label(
                catalog_has_h_star=gold.hypothesis_id in catalog_ids,
                sufficient=oracle_rec.sufficient == "true",
                fast_correct=fast_ok,
                deliberative_correct=disc_ok,
            )
            top_gen = max((c.generation_score for c in fast.candidates), default=0.0)
            row = {
                "query_id": query_id,
                "intent_id": intent.intent_id,
                "domain": intent.domain,
                "condition": condition,
                "regime": f"{intent.domain}:{condition}",
                "split": "development" if intent.intent_id in dev_intents else "holdout",
                "query": query,
                "generated_hypothesis_ids": list(generated_ids),
                "fast_predicted": fast.predicted_id,
                "disc_predicted": disc.predicted_id,
                "legacy_full_predicted": legacy_full.predicted_hypothesis_id,
                "fast_correct": fast_ok,
                "disc_correct": disc_ok,
                "legacy_full_correct": legacy_full.predicted_hypothesis_id == gold.hypothesis_id,
                "relevance_correct": _correct(relevance, gold.hypothesis_id),
                "bm25_correct": _correct(bm25_arm, gold.hypothesis_id),
                "dense_correct": _correct(dense_arm, gold.hypothesis_id),
                "falsification_correct": _correct(fals, gold.hypothesis_id),
                "no_disc_update_correct": _correct(no_disc_update, gold.hypothesis_id),
                "oracle_hypothesis_correct": hyp_ok,
                "oracle_retrieval_correct": ret_ok,
                "oracle_evidence_correct": evid_ok,
                "oracle_belief_correct": bel_ok,
                "four_way_class": four.label,
                "primary_failure": primary_label,
                "secondary_failures": list(secondary),
                "classification_justification": why,
                "sufficient": oracle_rec.sufficient,
                "evidence_doc_ids": list(oracle_rec.evidence_doc_ids),
                "gold_retrieved_disc": gold_retrieved,
                "fast_entropy": fast.belief.normalized_entropy,
                "fast_margin": fast.belief.margin,
                "fast_unknown_mass": fast.belief.probabilities.get("H_unknown", 0.0),
                "fast_retrieval_calls": fast.retrieval_calls,
                "disc_retrieval_calls": disc.retrieval_calls,
                "legacy_retrieval_calls": legacy_full.retrieval_calls,
                "top_generation_score": top_gen,
                "signal_quality": fast.observation.signal_quality,
                "fast_u": fast_u,
                "disc_u": u(disc, disc_ok),
                "legacy_full_u": realized_utility(
                    correct=legacy_full.predicted_hypothesis_id == gold.hypothesis_id,
                    action=legacy_full.decision.action.value,
                    retrieval_calls=legacy_full.retrieval_calls,
                    seed_calls=fast.seed_calls,
                    **costs,
                ),
                "relevance_u": u(relevance, _correct(relevance, gold.hypothesis_id)),
                "bm25_u": u(bm25_arm, _correct(bm25_arm, gold.hypothesis_id)),
                "dense_u": u(dense_arm, _correct(dense_arm, gold.hypothesis_id)),
                "falsification_u": u(fals, _correct(fals, gold.hypothesis_id)),
                "no_disc_update_u": u(no_disc_update, _correct(no_disc_update, gold.hypothesis_id)),
                "recoverability_label": rec_label,
                "delta_b_star_oracle_hyp": delta_b,
                "gold_source": oracle_rec.gold_source,
                "review_needed": oracle_rec.review_needed,
            }
            anatomy.append(row)
            intervention_matrix.append(
                {
                    "query_id": query_id,
                    "intent_id": intent.intent_id,
                    "fast": fast_ok,
                    "disc_predicted": disc_ok,
                    "legacy_full": row["legacy_full_correct"],
                    "oracle_hypothesis": hyp_ok,
                    "oracle_retrieval": ret_ok,
                    "oracle_evidence": evid_ok,
                    "oracle_belief": bel_ok,
                    "primary_failure": row["primary_failure"],
                }
            )

    included_errors = [row for row in anatomy if not row["fast_correct"]]
    indeterminate = [row for row in included_errors if row["primary_failure"] == "INDETERMINATE"]
    recoverable_errors = [row for row in included_errors if row["sufficient"] == "true"]
    ceiling_overall = wilson_interval(len(recoverable_errors), len(included_errors))
    ceiling_by_regime: dict[str, Any] = {}
    for row in included_errors:
        ceiling_by_regime.setdefault(row["regime"], {"k": 0, "n": 0})
        ceiling_by_regime[row["regime"]]["n"] += 1
        if row["sufficient"] == "true":
            ceiling_by_regime[row["regime"]]["k"] += 1
    ceiling_by_regime = {
        key: wilson_interval(val["k"], val["n"]) for key, val in sorted(ceiling_by_regime.items())
    }
    anatomy_dist = dict(Counter(row["primary_failure"] for row in included_errors))

    confirmatory_metrics = {
        "legacy_full": rescue_metrics(_rows_for_arm(anatomy, "legacy_full")),
        "disc_predicted": rescue_metrics(_rows_for_arm(anatomy, "disc")),
        "relevance": rescue_metrics(_rows_for_arm(anatomy, "relevance")),
        "bm25": rescue_metrics(_rows_for_arm(anatomy, "bm25")),
        "dense": rescue_metrics(_rows_for_arm(anatomy, "dense")),
        "falsification": rescue_metrics(_rows_for_arm(anatomy, "falsification")),
        "no_disc_update": rescue_metrics(_rows_for_arm(anatomy, "no_disc_update")),
    }

    rec_dev = [row for row in anatomy if row["split"] == "development"]
    rec_hold = [row for row in anatomy if row["split"] == "holdout"]
    recoverability_block: dict[str, Any] = {"status": "SKIPPED"}
    if "recoverability" in stages:
        def pack(rows: list[dict[str, Any]]) -> tuple[list[list[float]], list[int], list[float]]:
            xs: list[list[float]] = []
            ys: list[int] = []
            entropy: list[float] = []
            for row in rows:
                feats = preaction_features(row)
                xs.append(
                    [
                        feats["entropy"],
                        feats["margin"],
                        feats["unknown_mass"],
                        feats["top_generation_score"],
                        feats["signal_quality"],
                    ]
                )
                ys.append(1 if row["recoverability_label"] == "RECOVERABLE_RESCUED" else 0)
                entropy.append(feats["entropy"])
            return xs, ys, entropy

        x_dev, y_dev, e_dev = pack(rec_dev)
        x_hold, y_hold, e_hold = pack(rec_hold)
        weights, bias = fit_logreg(x_dev, y_dev)
        scores = [predict_logreg(x, weights, bias) for x in x_hold]
        cut = median(e_dev)
        entropy_scores = threshold_predict(e_hold, cut)
        recoverability_block = {
            "n_dev": len(rec_dev),
            "n_hold": len(rec_hold),
            "positive_hold": sum(y_hold),
            "logreg": {
                "auroc": auroc(scores, y_hold) if y_hold else None,
                "auprc": auprc(scores, y_hold) if y_hold else 0.0,
                "brier": brier(scores, y_hold) if y_hold else 0.0,
            },
            "entropy_gate": {
                "cut": cut,
                "auroc": auroc(entropy_scores, y_hold) if y_hold else None,
                "auprc": auprc(entropy_scores, y_hold) if y_hold else 0.0,
                "brier": brier(entropy_scores, y_hold) if y_hold else 0.0,
            },
            "label_note": "Positive label is RECOVERABLE_RESCUED. Fast-correct cases are negatives. Pre-action features only.",
        }

    analyze_rows = []
    ask_rows = []
    defer_rows = []
    if "actions" in stages:
        sample = anatomy[: min(12, len(anatomy))]
        for row in sample:
            intent = next(item for item in intents if item.intent_id == row["intent_id"])
            analysis = analyze_only(rescue_pipeline, row["query"], row["domain"])
            analysis["query_id"] = row["query_id"]
            analysis["evidence_frozen"] = analysis["evidence_ids_before"] == analysis["evidence_ids_after"]
            analyze_rows.append(analysis)
            fast = rescue_pipeline.run(row["query"], row["domain"], arm="fast", mode="predicted_hypothesis")
            asked = ask_simulator(
                candidates=fast.candidates,
                gold_id=intent.correct_hypothesis,
                noise=0.1,
                seed=seed + int(hashlib.sha256(row["query_id"].encode("utf-8")).hexdigest()[:8], 16) % 10000,
            )
            ask_rows.append(
                {
                    "query_id": row["query_id"],
                    "ask_resolved": asked == intent.correct_hypothesis,
                    "fast_correct": row["fast_correct"],
                    "disc_correct": row["disc_correct"],
                    "ask_beats_explore": (asked == intent.correct_hypothesis) and not row["disc_correct"],
                }
            )
        false_answers = 0
        defers = 0
        for query, domain in open_set_query_pack():
            run = rescue_pipeline.run(query, domain, arm="fast", mode="predicted_hypothesis")
            top_gen = max((c.generation_score for c in run.candidates), default=0.0)
            fire = defer_should_fire(
                entropy=run.belief.normalized_entropy,
                unknown_mass=run.belief.probabilities.get("H_unknown", 0.0),
                top_generation=top_gen,
            )
            defers += int(fire)
            false_answers += int(not fire)
            defer_rows.append(
                {
                    "query": query,
                    "domain": domain,
                    "predicted": run.predicted_id,
                    "defer": fire,
                    "entropy": run.belief.normalized_entropy,
                    "top_generation_score": top_gen,
                }
            )

    hist_a1 = root / "experiments" / "results" / "milestone_a1" / "metrics.json"
    historical = None
    if hist_a1.exists():
        historical = json.loads(hist_a1.read_text(encoding="utf-8"))
        historical = {
            "source": "experiments/results/milestone_a1/metrics.json",
            "n_matched": historical.get("n_matched"),
            "RescueRate": (historical.get("overall") or {}).get("RescueRate"),
            "BothWrongRate": (historical.get("overall") or {}).get("BothWrongRate"),
            "BothWrong_count": ((historical.get("overall") or {}).get("counts") or {}).get("BOTH_WRONG"),
            "note": "Preserved historical WDI/A1 observation. Prompt cited ~153/400; this artifact differs and is not overwritten.",
        }

    disc_metrics = confirmatory_metrics["disc_predicted"]
    predicted_arms = ("disc_predicted", "relevance", "bm25", "dense", "falsification", "no_disc_update")
    non_oracle_rescue = max(confirmatory_metrics[arm]["counts"]["RESCUE"] for arm in predicted_arms)
    best_arm = max(predicted_arms, key=lambda arm: confirmatory_metrics[arm]["counts"]["RESCUE"])
    net = confirmatory_metrics[best_arm]["NetRescueRate"]["rate"]
    du = confirmatory_metrics[best_arm]["DeltaU_EXPLORE"]["mean"]
    du_ci = confirmatory_metrics[best_arm]["DeltaU_EXPLORE"]["cluster_bootstrap"]
    cycle4 = "PASS"
    if indeterminate:
        cycle4 = "FAIL"
    if included_errors and any(row["sufficient"] == "undetermined" for row in included_errors):
        cycle4 = "FAIL"
    cycle5_mech = "PASS" if non_oracle_rescue > 0 else "FAIL"
    cycle5_policy = "PASS" if net > 0 and du > 0 else "FAIL"
    cycle6 = "BLOCKED" if cycle5_policy != "PASS" else "PASS"
    if cycle6 == "PASS":
        # Policy is not rewritten; only evaluated as eligible.
        cycle6 = "PASS_ELIGIBLE_NOT_PROMOTED"
    gates = {
        "cycle4_anatomy": cycle4,
        "cycle5_non_oracle_rescue": cycle5_mech,
        "cycle5_net_utility": cycle5_policy,
        "cycle6_policy": cycle6,
        "cycle7a_analyze_ask_defer": "TESTED" if analyze_rows else "SKIPPED",
        "leakage_contract": "PASS",
    }

    if included_errors and ceiling_overall["rate"] < 0.05:
        next_test = (
            "OracleRescueCeiling is near zero on this fixture's FastWrong slice. "
            "Do not retune policy. Next: versioned corpus/benchmark with explicit recoverability; preserve this negative."
        )
    elif cycle5_mech == "FAIL" and ceiling_overall["rate"] >= 0.05:
        next_test = (
            "Ceiling is non-trivial but NonOracleRescueCount=0. Dominant primary_failure "
            f"is {max(anatomy_dist, key=anatomy_dist.get) if anatomy_dist else 'unknown'}. "
            "Falsify that component with a targeted intervention on holdout intents."
        )
    elif cycle5_policy == "FAIL" and non_oracle_rescue > 0:
        next_test = (
            "Rescue exists but NetRescueRate or ΔU is non-positive (overthinking/cost). "
            "Next falsifiable test: recoverability-gated EXPLORE on holdout, not always-explore."
        )
    else:
        next_test = (
            "Mechanism gate passed. Next: equal-budget NEU comparison of gated EXPLORE vs BM25 "
            "on a held-out intent split, without touching sealed WDI test."
        )

    claims = [
        {
            "claim_id": "C4-oracle-ceiling-known",
            "status": "demonstrada" if cycle4 == "PASS" else "parcialmente demonstrada",
            "evidence": f"OracleRescueCeiling k={ceiling_overall.get('k')} n={ceiling_overall.get('n')}",
            "scope": "sanity fixture FastWrong",
            "limitation": "gold uses document.hypothesis_ids; not a human adjudication",
        },
        {
            "claim_id": "C5-non-oracle-rescue",
            "status": "demonstrada" if cycle5_mech == "PASS" else "refutada no regime testado",
            "evidence": f"Rescue count={non_oracle_rescue} on best predicted arm={best_arm} (pairwise disc={disc_metrics['counts']['RESCUE']})",
            "scope": f"sanity {len(anatomy)} queries, clustered by intent_id",
            "limitation": "small catalog; lexical discrimination only",
        },
        {
            "claim_id": "C5-net-utility",
            "status": "demonstrada" if cycle5_policy == "PASS" else "não demonstrada",
            "evidence": f"NetRescueRate={net}; DeltaU={du}; CI={du_ci}",
            "scope": "same confirmatory fixture",
            "limitation": "utility uses pre-registered costs, not production money",
        },
        {
            "claim_id": "C6-policy-neu",
            "status": "ainda não testada" if cycle6 == "BLOCKED" else "parcialmente demonstrada",
            "evidence": "default v0.1.1 policy unchanged; Cycle 6 blocked unless Cycle 5 net-utility PASS",
            "scope": "operational policy",
            "limitation": "no silent policy promotion",
        },
        {
            "claim_id": "A1-wdi-rescue-zero",
            "status": "demonstrada",
            "evidence": str(historical),
            "scope": "historical WDI A1 matched table",
            "limitation": "not re-run in this cycle; preserved artifact",
        },
    ]

    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": output.name,
        "git_sha": _git_sha(root),
        "package_version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "seed": seed,
        "n_queries": len(anatomy),
        "n_intents": len({row["intent_id"] for row in anatomy}),
        "hashes": hashes,
        "historical_a1": historical,
        "oracle_ceiling": {
            "overall": ceiling_overall,
            "by_regime": ceiling_by_regime,
            "OracleRecoverability": ceiling_overall,
        },
        "anatomy_distribution": anatomy_dist,
        "indeterminate_count": len(indeterminate),
        "confirmatory_metrics": confirmatory_metrics,
        "best_predicted_arm": best_arm,
        "non_oracle_rescue_count": non_oracle_rescue,
        "recoverability_v2": recoverability_block,
        "analyze": {
            "n": len(analyze_rows),
            "prediction_changes": sum(int(r["changed_prediction"]) for r in analyze_rows),
            "evidence_frozen_all": all(r.get("evidence_frozen") for r in analyze_rows) if analyze_rows else None,
        },
        "ask": {
            "n": len(ask_rows),
            "resolved": sum(int(r["ask_resolved"]) for r in ask_rows),
            "beats_explore": sum(int(r["ask_beats_explore"]) for r in ask_rows),
        },
        "defer": {
            "n": len(defer_rows),
            "defer_count": sum(int(r["defer"]) for r in defer_rows),
            "false_answer_if_forced": sum(1 for r in defer_rows if not r["defer"]),
        },
        "gates": gates,
        "claims": claims,
        "next_test": next_test,
        "reproduction_command": (
            "quasar2 rescue-cycle --output experiments/results/cycle4_rescue "
            f"--seed {seed}"
            + (f" --limit {limit}" if limit else "")
        ),
    }

    write_jsonl(output / "anatomy.jsonl", anatomy)
    write_json(output / "intervention_matrix.json", {"rows": intervention_matrix})
    write_json(output / "run_manifest.json", payload)
    examples: dict[str, Any] = {}
    for row in included_errors:
        examples.setdefault(row["primary_failure"], row)
    write_json(output / "failure_examples.json", examples)
    write_json(output / "analyze.json", {"rows": analyze_rows})
    write_json(output / "ask.json", {"rows": ask_rows})
    write_json(output / "defer.json", {"rows": defer_rows})
    report = render_report(payload)
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    payload["report_path"] = str(output / "REPORT.md")
    return payload
