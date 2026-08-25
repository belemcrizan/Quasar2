"""Reproducible benchmark runner and metric aggregation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
import math
from pathlib import Path
import random
import statistics
import time
from typing import Any, Iterable, Mapping, Sequence

from quasar2.baselines import DirectRetrievalBaseline, RewriteHybridBaseline
from quasar2.config import ProjectConfig, load_structured
from quasar2.hypotheses.catalog import CatalogHypothesisGenerator, HypothesisCatalog
from quasar2.models.decision import Action
from quasar2.pipeline import QuasarPipeline, VALID_ABLATIONS
from quasar2.retrieval import BM25Retriever, HashingDenseRetriever, HybridRetriever, SearchHit, load_corpus
from quasar2.signals.extractor import SignalExtractor


@dataclass(frozen=True, slots=True)
class Intent:
    intent_id: str
    domain: str
    q0: str
    q1: str
    q2: str
    correct_hypothesis: str


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    method: str
    intent_id: str
    domain: str
    condition: str
    query: str
    correct_hypothesis: str
    predicted_hypothesis: str | None
    correct: bool
    action: str
    recall_at_10: float
    reciprocal_rank: float
    ndcg_at_10: float
    retrieval_calls: int
    explore_rounds: int
    latency_ms: float


def load_intents(path: str | Path) -> tuple[Intent, ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    records = raw.get("intents", raw) if isinstance(raw, dict) else raw
    if not isinstance(records, list):
        raise ValueError("Intent file must contain a list")
    intents = tuple(
        Intent(
            intent_id=str(item["id"]),
            domain=str(item["domain"]),
            q0=str(item["q0"]),
            q1=str(item["q1"]),
            q2=str(item["q2"]),
            correct_hypothesis=str(item["correct_hypothesis"]),
        )
        for item in records
    )
    if len({intent.intent_id for intent in intents}) != len(intents):
        raise ValueError("Intent ids must be unique")
    return intents


def retrieval_metrics(
    hits: Sequence[SearchHit],
    correct_hypothesis: str,
    *,
    cutoff: int = 10,
    relevant_total: int | None = None,
) -> tuple[float, float, float]:
    relevance = [
        1.0 if correct_hypothesis in hit.document.hypothesis_ids else 0.0
        for hit in hits[:cutoff]
    ]
    known_relevant = relevant_total if relevant_total is not None else sum(relevance)
    recall = sum(relevance) / max(1, known_relevant)
    first_rank = next((index for index, value in enumerate(relevance, start=1) if value), None)
    reciprocal_rank = 1.0 / first_rank if first_rank else 0.0
    dcg = sum(value / math.log2(index + 1) for index, value in enumerate(relevance, start=1))
    ideal_count = min(cutoff, max(1, known_relevant))
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_count + 1))
    ndcg = dcg / idcg if any(relevance) else 0.0
    return recall, reciprocal_rank, ndcg


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def summarize(records: Sequence[BenchmarkRecord]) -> dict[str, float]:
    size = len(records)
    if size == 0:
        return {}
    return {
        "n": float(size),
        "intent_recovery_rate": statistics.fmean(float(record.correct) for record in records),
        "recall_at_10": statistics.fmean(record.recall_at_10 for record in records),
        "mrr": statistics.fmean(record.reciprocal_rank for record in records),
        "ndcg_at_10": statistics.fmean(record.ndcg_at_10 for record in records),
        "autonomous_resolution_rate": statistics.fmean(
            float(record.action == Action.ANSWER.value) for record in records
        ),
        "correct_autonomous_resolution_rate": statistics.fmean(
            float(record.action == Action.ANSWER.value and record.correct) for record in records
        ),
        "ask_fraction": statistics.fmean(
            float(record.action == Action.ASK.value) for record in records
        ),
        "average_retrieval_calls": statistics.fmean(record.retrieval_calls for record in records),
        "average_explore_rounds": statistics.fmean(record.explore_rounds for record in records),
        "latency_p50_ms": _percentile([record.latency_ms for record in records], 0.50),
        "latency_p95_ms": _percentile([record.latency_ms for record in records], 0.95),
    }


def paired_bootstrap_difference(
    left: Sequence[BenchmarkRecord],
    right: Sequence[BenchmarkRecord],
    *,
    samples: int,
    seed: int,
    outcome: str = "intent_recovery",
) -> dict[str, float]:
    def value(record: BenchmarkRecord) -> float:
        if outcome == "intent_recovery":
            return float(record.correct)
        if outcome == "correct_autonomous_resolution":
            return float(record.correct and record.action == Action.ANSWER.value)
        if outcome == "wrong_autonomous_resolution":
            return float(not record.correct and record.action == Action.ANSWER.value)
        raise ValueError(f"Unknown paired outcome {outcome!r}")

    right_by_key = {(record.intent_id, record.condition): record for record in right}
    pairs = [
        (value(record), value(right_by_key[(record.intent_id, record.condition)]))
        for record in left
        if (record.intent_id, record.condition) in right_by_key
    ]
    if not pairs:
        return {"difference": 0.0, "ci_low": 0.0, "ci_high": 0.0, "pairs": 0.0}
    observed = statistics.fmean(left_value - right_value for left_value, right_value in pairs)
    rng = random.Random(seed)
    differences: list[float] = []
    for _ in range(samples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        differences.append(
            statistics.fmean(left_value - right_value for left_value, right_value in sample)
        )
    return {
        "difference": observed,
        "ci_low": _percentile(differences, 0.025),
        "ci_high": _percentile(differences, 0.975),
        "pairs": float(len(pairs)),
    }


class BenchmarkRunner:
    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        paths = config.section("paths")
        self.intents = load_intents(config.resolve(str(paths["intents"])))
        self.documents = load_corpus(config.resolve(str(paths["corpus"])))
        self.catalog = HypothesisCatalog.from_directory(config.resolve(str(paths["catalog"])))
        retrieval = config.section("retrieval")
        self.bm25 = BM25Retriever(self.documents)
        self.dense = HashingDenseRetriever(
            self.documents, dimensions=int(retrieval.get("dense_dimensions", 384))
        )
        self.hybrid = HybridRetriever(
            self.bm25,
            self.dense,
            sparse_weight=float(retrieval.get("bm25_weight", 0.6)),
            dense_weight=float(retrieval.get("dense_weight", 0.4)),
            rrf_k=int(retrieval.get("rrf_k", 20)),
        )
        self.pipeline = QuasarPipeline.from_config(config)
        domain_values = load_structured(config.resolve(str(paths["domains"])))
        self.extractor = SignalExtractor(
            {domain: values.get("domain_cues", ()) for domain, values in domain_values.items()}
        )
        self.generator = CatalogHypothesisGenerator(self.catalog)

    def _baseline(self, method: str) -> DirectRetrievalBaseline | RewriteHybridBaseline:
        if method == "bm25":
            return DirectRetrievalBaseline("bm25", self.bm25)
        if method == "dense":
            return DirectRetrievalBaseline("dense", self.dense)
        if method == "hybrid":
            return DirectRetrievalBaseline("hybrid", self.hybrid)
        if method == "rewrite_hybrid":
            return RewriteHybridBaseline(self.hybrid, self.extractor, self.generator)
        raise KeyError(method)

    @staticmethod
    def _evidence_hits(result: Any, documents_by_id: Mapping[str, Any]) -> tuple[SearchHit, ...]:
        best_by_document: dict[str, Any] = {}
        for item in result.evidence:
            current = best_by_document.get(item.document_id)
            if current is None or item.support_score > current.support_score:
                best_by_document[item.document_id] = item
        ranked = sorted(
            best_by_document.values(), key=lambda item: (-item.support_score, item.document_id)
        )
        return tuple(
            SearchHit(
                document=documents_by_id[item.document_id],
                score=item.support_score,
                rank=rank,
                components={"evidence": item.support_score},
            )
            for rank, item in enumerate(ranked, start=1)
        )

    def run(
        self,
        *,
        methods: Sequence[str] | None = None,
        conditions: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        benchmark = self.config.section("benchmark")
        selected_methods = tuple(methods or benchmark.get("methods", ()))
        selected_conditions = tuple(conditions or benchmark.get("conditions", ("q0", "q1", "q2")))
        invalid_conditions = set(selected_conditions) - {"q0", "q1", "q2"}
        if invalid_conditions:
            raise ValueError(f"Invalid query conditions: {sorted(invalid_conditions)}")
        intents = self.intents[:limit] if limit else self.intents
        cutoff = int(benchmark.get("cutoff", 10))
        documents_by_id = {document.document_id: document for document in self.documents}
        relevant_count = {
            hypothesis.hypothesis_id: sum(
                1
                for document in self.documents
                if hypothesis.hypothesis_id in document.hypothesis_ids
            )
            for hypothesis in self.catalog
        }
        records: list[BenchmarkRecord] = []
        started = time.time()

        for method in selected_methods:
            baseline = self._baseline(method) if method not in VALID_ABLATIONS else None
            for intent in intents:
                for condition in selected_conditions:
                    query = getattr(intent, condition)
                    if baseline is not None:
                        result = baseline.run(query, intent.domain, top_k=cutoff)
                        hits = result.hits
                        predicted = result.predicted_hypothesis_id
                        action = Action.ANSWER.value
                        calls = result.retrieval_calls
                        rounds = 0
                        latency = result.elapsed_ms
                    else:
                        pipeline_result = self.pipeline.run(
                            query,
                            intent.domain,
                            ablation=method,
                            observation_id=f"{intent.intent_id}:{condition}",
                        )
                        hits = self._evidence_hits(pipeline_result, documents_by_id)
                        predicted = pipeline_result.predicted_hypothesis_id
                        action = pipeline_result.decision.action.value
                        calls = pipeline_result.retrieval_calls
                        rounds = pipeline_result.explore_rounds
                        latency = pipeline_result.elapsed_ms
                    recall, reciprocal_rank, ndcg = retrieval_metrics(
                        hits,
                        intent.correct_hypothesis,
                        cutoff=cutoff,
                        relevant_total=relevant_count[intent.correct_hypothesis],
                    )
                    records.append(
                        BenchmarkRecord(
                            method=method,
                            intent_id=intent.intent_id,
                            domain=intent.domain,
                            condition=condition,
                            query=query,
                            correct_hypothesis=intent.correct_hypothesis,
                            predicted_hypothesis=predicted,
                            correct=predicted == intent.correct_hypothesis,
                            action=action,
                            recall_at_10=recall,
                            reciprocal_rank=reciprocal_rank,
                            ndcg_at_10=ndcg,
                            retrieval_calls=calls,
                            explore_rounds=rounds,
                            latency_ms=latency,
                        )
                    )

        summaries: dict[str, Any] = {}
        for method in selected_methods:
            method_records = [record for record in records if record.method == method]
            by_condition = {
                condition: summarize(
                    [record for record in method_records if record.condition == condition]
                )
                for condition in selected_conditions
            }
            q0 = by_condition.get("q0", {}).get("intent_recovery_rate", 0.0)
            for condition, values in by_condition.items():
                values["robustness_ratio_vs_q0"] = (
                    values.get("intent_recovery_rate", 0.0) / q0 if q0 else 0.0
                )
            summaries[method] = {"overall": summarize(method_records), "by_condition": by_condition}

        comparison: dict[str, Any] = {}
        if "full" in selected_methods and "hybrid" in selected_methods:
            comparison["full_minus_hybrid_intent_recovery"] = paired_bootstrap_difference(
                [record for record in records if record.method == "full"],
                [record for record in records if record.method == "hybrid"],
                samples=int(benchmark.get("bootstrap_samples", 1000)),
                seed=int(self.config.values.get("seed", 42)),
            )
        if "full" in selected_methods and "noHyp" in selected_methods:
            comparison["full_minus_noHyp_intent_recovery"] = paired_bootstrap_difference(
                [record for record in records if record.method == "full"],
                [record for record in records if record.method == "noHyp"],
                samples=int(benchmark.get("bootstrap_samples", 1000)),
                seed=int(self.config.values.get("seed", 42)) + 1,
            )
        if "full" in selected_methods and "noExplore" in selected_methods:
            comparison["full_minus_noExplore_correct_arr"] = paired_bootstrap_difference(
                [record for record in records if record.method == "full"],
                [record for record in records if record.method == "noExplore"],
                samples=int(benchmark.get("bootstrap_samples", 1000)),
                seed=int(self.config.values.get("seed", 42)) + 2,
                outcome="correct_autonomous_resolution",
            )
        return {
            "schema_version": "1.0",
            "poc_status": "mechanism test; not evidence of general superiority",
            "started_unix": started,
            "seed": int(self.config.values.get("seed", 42)),
            "dataset": {
                "intents": len(intents),
                "queries": len(intents) * len(selected_conditions),
                "documents": len(self.documents),
                "domains": sorted({intent.domain for intent in intents}),
                "conditions": list(selected_conditions),
            },
            "methods": list(selected_methods),
            "summaries": summaries,
            "paired_comparisons": comparison,
            "records": [asdict(record) for record in records],
        }


def write_results(results: Mapping[str, Any], output_path: str | Path) -> tuple[Path, Path]:
    json_path = Path(output_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_path = json_path.with_suffix(".csv")
    records = list(results.get("records", ()))
    if records:
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    else:
        csv_path.write_text("", encoding="utf-8")
    return json_path, csv_path


def format_summary_table(results: Mapping[str, Any]) -> str:
    header = "method             IRR    R@10   MRR    nDCG   ARR    cARR   ASK    calls  p95ms"
    lines = [header, "-" * len(header)]
    for method in results.get("methods", ()):
        values = results["summaries"][method]["overall"]
        lines.append(
            f"{method:<18} "
            f"{values['intent_recovery_rate']:.3f}  {values['recall_at_10']:.3f}  "
            f"{values['mrr']:.3f}  {values['ndcg_at_10']:.3f}  "
            f"{values['autonomous_resolution_rate']:.3f}  "
            f"{values['correct_autonomous_resolution_rate']:.3f}  "
            f"{values['ask_fraction']:.3f}  {values['average_retrieval_calls']:.2f}  "
            f"{values['latency_p95_ms']:.2f}"
        )
    return "\n".join(lines)
