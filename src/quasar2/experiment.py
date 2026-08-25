"""v0.2 regime experiment: matched backends, factorial Q, frozen v0.1.1 loop.

The inference loop is not modified here.  This module only changes how
observations, retrievers, and metrics are composed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from quasar2.baselines import DirectRetrievalBaseline, MultiQueryBaseline, RewriteHybridBaseline
from quasar2.benchmark import (
    BenchmarkRecord,
    Intent,
    paired_bootstrap_difference,
    retrieval_metrics,
)
from quasar2.config import ProjectConfig, load_structured
from quasar2.hypotheses.catalog import CatalogHypothesisGenerator, HypothesisCatalog
from quasar2.models.decision import Action
from quasar2.pipeline import QuasarPipeline, VALID_ABLATIONS
from quasar2.regimes import FactorialDegrader, RegimeCell, competitor_terms_for, sample_design
from quasar2.retrieval import SearchHit, load_corpus
from quasar2.retrieval.factory import build_retriever
from quasar2.signals.extractor import SignalExtractor


LOOP_METHODS = frozenset({"full", "noHyp", "noExplore", "noUpdate", "noAsk"}) | {
    "full+bm25",
    "full+dense_hash",
    "full+dense",
    "full+hybrid",
}


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    method: str
    backend: str
    intent_id: str
    domain: str
    cell_id: str
    seed: int
    query: str
    correct_hypothesis: str
    predicted_hypothesis: str | None
    interpretation_correct: bool
    action: str
    ranking_recall_at_10: float
    ranking_mrr: float
    ranking_ndcg_at_10: float
    evidence_recall_at_10: float
    retrieval_calls: int
    ask: bool
    wrong_answer: bool
    latency_ms: float
    ambiguity: int
    lexical: int
    paraphrase: int
    underspecification: int
    distractor: int
    severity: float


def _loop_backend(method: str, default: str) -> str:
    if method.startswith("full+"):
        alias = method.split("+", 1)[1]
        return "dense_hash" if alias == "dense" else alias
    if method in VALID_ABLATIONS:
        return default
    return default


def _baseline_backend(method: str) -> str:
    mapping = {
        "bm25": "bm25",
        "dense": "dense_hash",
        "dense_hash": "dense_hash",
        "hybrid": "hybrid",
        "neural": "neural",
        "hybrid_neural": "hybrid_neural",
        "rewrite_hybrid": "hybrid",
        "rewrite": "hybrid",
        "multi_query": "hybrid",
    }
    return mapping[method]


def summarize_experiment(records: Sequence[ExperimentRecord]) -> dict[str, float]:
    if not records:
        return {}
    n = len(records)
    return {
        "n": float(n),
        "intent_recovery_rate": sum(record.interpretation_correct for record in records) / n,
        "correct_autonomous_resolution_rate": sum(
            record.action == Action.ANSWER.value and record.interpretation_correct
            for record in records
        ) / n,
        "wrong_answer_rate": sum(record.wrong_answer for record in records) / n,
        "ask_fraction": sum(record.ask for record in records) / n,
        "coverage": sum(record.action == Action.ANSWER.value for record in records) / n,
        "ranking_recall_at_10": sum(record.ranking_recall_at_10 for record in records) / n,
        "ranking_mrr": sum(record.ranking_mrr for record in records) / n,
        "ranking_ndcg_at_10": sum(record.ranking_ndcg_at_10 for record in records) / n,
        "evidence_recall_at_10": sum(record.evidence_recall_at_10 for record in records) / n,
        "average_retrieval_calls": sum(record.retrieval_calls for record in records) / n,
        "latency_p50_ms": sorted(record.latency_ms for record in records)[n // 2],
        "mean_severity": sum(record.severity for record in records) / n,
    }


def crossover_table(
    records: Sequence[ExperimentRecord],
    *,
    treatment: str,
    control: str,
    bins: int = 5,
) -> list[dict[str, float | str]]:
    """Δ correct ARR by severity bin.  Positive means the loop helps."""

    def arr(record: ExperimentRecord) -> float:
        return float(record.action == Action.ANSWER.value and record.interpretation_correct)

    control_map = {
        (record.intent_id, record.cell_id, record.seed): record
        for record in records
        if record.method == control
    }
    buckets: dict[int, list[float]] = {index: [] for index in range(bins)}
    for record in records:
        if record.method != treatment:
            continue
        paired = control_map.get((record.intent_id, record.cell_id, record.seed))
        if paired is None:
            continue
        index = min(bins - 1, int(record.severity * bins))
        buckets[index].append(arr(record) - arr(paired))
    rows: list[dict[str, float | str]] = []
    for index in range(bins):
        values = buckets[index]
        if not values:
            continue
        mean = sum(values) / len(values)
        rows.append(
            {
                "bin": f"{index / bins:.2f}-{(index + 1) / bins:.2f}",
                "n": float(len(values)),
                "delta_correct_arr": mean,
                "treatment": treatment,
                "control": control,
            }
        )
    return rows


def interpretation_retrieval_tradeoff(records: Sequence[ExperimentRecord]) -> dict[str, dict[str, float]]:
    by_method: dict[str, dict[str, float]] = {}
    methods = sorted({record.method for record in records})
    for method in methods:
        subset = [record for record in records if record.method == method]
        by_method[method] = {
            "interpretation_irr": sum(record.interpretation_correct for record in subset) / len(subset),
            "ranking_recall_at_10": sum(record.ranking_recall_at_10 for record in subset) / len(subset),
            "evidence_recall_at_10": sum(record.evidence_recall_at_10 for record in subset) / len(subset),
        }
    return by_method


class RegimeExperiment:
    """Frozen-loop evaluation under factorial degradation and matched retrievers."""

    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        paths = config.section("paths")
        raw_intents = load_structured(config.resolve(str(paths["intents"])))
        records = raw_intents.get("intents", raw_intents)
        self.intents = tuple(
            Intent(
                intent_id=str(item["id"]),
                domain=str(item["domain"]),
                q0=str(item["q0"]),
                q1=str(item.get("q1", item["q0"])),
                q2=str(item.get("q2", item["q0"])),
                correct_hypothesis=str(item["correct_hypothesis"]),
            )
            for item in records
        )
        self.documents = load_corpus(config.resolve(str(paths["corpus"])))
        self.catalog = HypothesisCatalog.from_directory(config.resolve(str(paths["catalog"])))
        domain_values = load_structured(config.resolve(str(paths["domains"])))
        self.extractor = SignalExtractor(
            {domain: values.get("domain_cues", ()) for domain, values in domain_values.items()}
        )
        self.generator = CatalogHypothesisGenerator(self.catalog)
        self.retrieval = config.section("retrieval")
        self.loop_backend = str(self.retrieval.get("backend", "hybrid"))
        self._retrievers: dict[str, Any] = {}
        self._pipelines: dict[str, QuasarPipeline] = {}

    def retriever(self, backend: str) -> Any:
        if backend not in self._retrievers:
            self._retrievers[backend] = build_retriever(
                self.documents, backend=backend, retrieval=self.retrieval
            )
        return self._retrievers[backend]

    def pipeline_for(self, backend: str) -> QuasarPipeline:
        if backend not in self._pipelines:
            self._pipelines[backend] = QuasarPipeline.from_config(
                self.config, retriever=self.retriever(backend)
            )
        return self._pipelines[backend]

    def _baseline(self, method: str) -> DirectRetrievalBaseline | RewriteHybridBaseline | MultiQueryBaseline:
        backend = _baseline_backend(method)
        retriever = self.retriever(backend)
        if method in {"bm25", "dense", "dense_hash", "hybrid", "neural", "hybrid_neural"}:
            return DirectRetrievalBaseline(method, retriever)
        if method in {"rewrite_hybrid", "rewrite"}:
            return RewriteHybridBaseline(retriever, self.extractor, self.generator)
        if method == "multi_query":
            return MultiQueryBaseline(retriever, self.extractor, self.generator)
        raise KeyError(method)

    def run(
        self,
        *,
        methods: Sequence[str] | None = None,
        seeds: Sequence[int] | None = None,
        limit: int | None = None,
        cells: Sequence[RegimeCell] | None = None,
    ) -> dict[str, Any]:
        experiment = self.config.section("experiment")
        selected_methods = tuple(methods or experiment.get("methods", ("bm25", "hybrid", "full+hybrid")))
        selected_seeds = tuple(seeds or experiment.get("seeds", (int(self.config.values.get("seed", 42)),)))
        selected_cells = tuple(cells or sample_design())
        intents = self.intents[:limit] if limit else self.intents
        cutoff = int(experiment.get("cutoff", self.config.section("benchmark").get("cutoff", 10)))
        documents_by_id = {document.document_id: document for document in self.documents}
        relevant_count = {
            hypothesis.hypothesis_id: sum(
                1 for document in self.documents if hypothesis.hypothesis_id in document.hypothesis_ids
            )
            for hypothesis in self.catalog
        }
        labels = [hypothesis.label for hypothesis in self.catalog]
        records: list[ExperimentRecord] = []

        for method in selected_methods:
            is_loop = method in LOOP_METHODS or method in VALID_ABLATIONS or method.startswith("full")
            baseline = None if is_loop else self._baseline(method)
            loop_backend = _loop_backend(method, self.loop_backend) if is_loop else _baseline_backend(method)
            ablation = method.split("+")[0] if method.startswith("full+") else (
                method if method in VALID_ABLATIONS else "full"
            )
            for intent in intents:
                competitors = competitor_terms_for(labels, exclude=intent.correct_hypothesis)
                degrader = FactorialDegrader(competitor_terms=competitors)
                for cell in selected_cells:
                    for seed in selected_seeds:
                        observation = degrader.apply(intent.q0, cell, seed=seed)
                        if baseline is not None:
                            result = baseline.run(observation.query, intent.domain, top_k=cutoff)
                            ranking_hits = result.hits
                            evidence_hits = result.hits
                            predicted = result.predicted_hypothesis_id
                            action = Action.ANSWER.value
                            calls = result.retrieval_calls
                            latency = result.elapsed_ms
                        else:
                            pipeline_result = self.pipeline_for(loop_backend).run(
                                observation.query,
                                intent.domain,
                                ablation=ablation if ablation in VALID_ABLATIONS else "full",
                                observation_id=f"{intent.intent_id}:{cell.cell_id}:{seed}",
                            )
                            ranking_hits = pipeline_result.retrieval_hits
                            best_by_document = {}
                            for item in pipeline_result.evidence:
                                current = best_by_document.get(item.document_id)
                                if current is None or item.support_score > current.support_score:
                                    best_by_document[item.document_id] = item
                            ranked_evidence = sorted(
                                best_by_document.values(),
                                key=lambda item: (-item.support_score, item.document_id),
                            )
                            evidence_hits = tuple(
                                SearchHit(
                                    document=documents_by_id[item.document_id],
                                    score=item.support_score,
                                    rank=rank,
                                    components={"evidence": item.support_score},
                                )
                                for rank, item in enumerate(ranked_evidence, start=1)
                                if item.document_id in documents_by_id
                            )
                            predicted = pipeline_result.predicted_hypothesis_id
                            action = pipeline_result.decision.action.value
                            calls = pipeline_result.retrieval_calls
                            latency = pipeline_result.elapsed_ms
                        ranking = retrieval_metrics(
                            ranking_hits,
                            intent.correct_hypothesis,
                            cutoff=cutoff,
                            relevant_total=relevant_count[intent.correct_hypothesis],
                        )
                        evidence = retrieval_metrics(
                            evidence_hits,
                            intent.correct_hypothesis,
                            cutoff=cutoff,
                            relevant_total=relevant_count[intent.correct_hypothesis],
                        )
                        correct = predicted == intent.correct_hypothesis
                        records.append(
                            ExperimentRecord(
                                method=method,
                                backend=loop_backend,
                                intent_id=intent.intent_id,
                                domain=intent.domain,
                                cell_id=cell.cell_id,
                                seed=int(seed),
                                query=observation.query,
                                correct_hypothesis=intent.correct_hypothesis,
                                predicted_hypothesis=predicted,
                                interpretation_correct=correct,
                                action=action,
                                ranking_recall_at_10=ranking[0],
                                ranking_mrr=ranking[1],
                                ranking_ndcg_at_10=ranking[2],
                                evidence_recall_at_10=evidence[0],
                                retrieval_calls=calls,
                                ask=action == Action.ASK.value,
                                wrong_answer=action == Action.ANSWER.value and not correct,
                                latency_ms=latency,
                                ambiguity=cell.ambiguity,
                                lexical=cell.lexical,
                                paraphrase=cell.paraphrase,
                                underspecification=cell.underspecification,
                                distractor=cell.distractor,
                                severity=cell.severity,
                            )
                        )

        summaries = {
            method: {
                "overall": summarize_experiment([record for record in records if record.method == method]),
                "by_cell": {
                    cell.cell_id: summarize_experiment(
                        [
                            record
                            for record in records
                            if record.method == method and record.cell_id == cell.cell_id
                        ]
                    )
                    for cell in selected_cells
                },
            }
            for method in selected_methods
        }
        comparisons: dict[str, Any] = {}
        bootstrap_samples = int(experiment.get("bootstrap_samples", 1000))
        seed = int(self.config.values.get("seed", 42))

        def as_benchmark(method: str) -> list[BenchmarkRecord]:
            converted: list[BenchmarkRecord] = []
            for record in records:
                if record.method != method:
                    continue
                converted.append(
                    BenchmarkRecord(
                        method=record.method,
                        intent_id=record.intent_id,
                        domain=record.domain,
                        condition=f"{record.cell_id}:{record.seed}",
                        query=record.query,
                        correct_hypothesis=record.correct_hypothesis,
                        predicted_hypothesis=record.predicted_hypothesis,
                        correct=record.interpretation_correct,
                        action=record.action,
                        recall_at_10=record.ranking_recall_at_10,
                        reciprocal_rank=record.ranking_mrr,
                        ndcg_at_10=record.ranking_ndcg_at_10,
                        retrieval_calls=record.retrieval_calls,
                        retrieval_calls_avoided=0,
                        explore_rounds=0,
                        pruned_explorations=0,
                        mean_document_novelty=0.0,
                        total_belief_variation=0.0,
                        observed_entropy_reduction=0.0,
                        latency_ms=record.latency_ms,
                    )
                )
            return converted

        if "full+hybrid" in selected_methods and "hybrid" in selected_methods:
            comparisons["full+hybrid_minus_hybrid_arr"] = paired_bootstrap_difference(
                as_benchmark("full+hybrid"),
                as_benchmark("hybrid"),
                samples=bootstrap_samples,
                seed=seed,
                outcome="correct_autonomous_resolution",
            )
        if "full+bm25" in selected_methods and "bm25" in selected_methods:
            comparisons["full+bm25_minus_bm25_arr"] = paired_bootstrap_difference(
                as_benchmark("full+bm25"),
                as_benchmark("bm25"),
                samples=bootstrap_samples,
                seed=seed + 1,
                outcome="correct_autonomous_resolution",
            )
        return {
            "schema_version": "2.0",
            "role": "scientific_regime_experiment",
            "poc_status": "v0.1.1 loop frozen; this measures Δ_loop(Q), not SOTA retrieval",
            "seed": seed,
            "dataset": {
                "intents": len(intents),
                "documents": len(self.documents),
                "cells": [cell.as_dict() for cell in selected_cells],
                "seeds": list(selected_seeds),
                "observations": len(intents) * len(selected_cells) * len(selected_seeds),
            },
            "methods": list(selected_methods),
            "summaries": summaries,
            "paired_comparisons": comparisons,
            "crossover": {
                "full+hybrid_vs_hybrid": crossover_table(
                    records, treatment="full+hybrid", control="hybrid"
                )
                if "full+hybrid" in selected_methods and "hybrid" in selected_methods
                else [],
                "full+bm25_vs_bm25": crossover_table(
                    records, treatment="full+bm25", control="bm25"
                )
                if "full+bm25" in selected_methods and "bm25" in selected_methods
                else [],
            },
            "interpretation_retrieval_tradeoff": interpretation_retrieval_tradeoff(records),
            "records": [asdict(record) for record in records],
        }


def format_experiment_table(results: Mapping[str, Any]) -> str:
    header = "method                 IRR    cARR   wrong  ASK    R@10   eR@10  calls"
    lines = [header, "-" * len(header)]
    for method in results.get("methods", ()):
        values = results["summaries"][method]["overall"]
        if not values:
            continue
        lines.append(
            f"{method:<22} "
            f"{values['intent_recovery_rate']:.3f}  "
            f"{values['correct_autonomous_resolution_rate']:.3f}  "
            f"{values['wrong_answer_rate']:.3f}  "
            f"{values['ask_fraction']:.3f}  "
            f"{values['ranking_recall_at_10']:.3f}  "
            f"{values['evidence_recall_at_10']:.3f}  "
            f"{values['average_retrieval_calls']:.2f}"
        )
    trade = results.get("interpretation_retrieval_tradeoff", {})
    if trade:
        lines.append("")
        lines.append("Interpretation–retrieval trade-off (IRR vs ranking R@10 vs evidence R@10)")
        for method, values in trade.items():
            lines.append(
                f"  {method:<22} irr={values['interpretation_irr']:.3f}  "
                f"rank={values['ranking_recall_at_10']:.3f}  "
                f"evidence={values['evidence_recall_at_10']:.3f}"
            )
    crossover = results.get("crossover", {})
    for name, rows in crossover.items():
        if not rows:
            continue
        lines.append("")
        lines.append(f"Crossover Δ cARR ({name}) by severity bin")
        for row in rows:
            lines.append(
                f"  {row['bin']:<12} n={int(row['n']):3d}  delta={row['delta_correct_arr']:+.3f}"
            )
    return "\n".join(lines)
