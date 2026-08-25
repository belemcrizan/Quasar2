from __future__ import annotations

from pathlib import Path
import unittest

from quasar2.benchmark import BenchmarkRunner
from quasar2.config import ProjectConfig
from quasar2.pipeline import QuasarPipeline


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.project_config = ProjectConfig.load(root / "configs/poc.yaml")
        cls.pipeline = QuasarPipeline.from_config(cls.project_config)

    def test_pipeline_emits_complete_scientific_trace(self) -> None:
        result = self.pipeline.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        stages = {event.stage for event in result.trace}
        self.assertTrue(
            {
                "OBSERVATION",
                "HYPOTHESES",
                "RETRIEVAL",
                "EVIDENCE",
                "BELIEF",
                "DECISION",
                "RESULT",
            }
            <= stages
        )
        self.assertEqual(result.predicted_hypothesis_id, "astro.exoplanet_transit")
        self.assertGreaterEqual(result.retrieval_calls, len(result.candidates))
        self.assertIn(result.to_dict()["decision"]["action"], {"ANSWER", "ASK"})

    def test_no_hypothesis_ablation_commits_to_one_candidate(self) -> None:
        result = self.pipeline.run(
            "Retrieval augmented generation grounds an answer in external passages and citations",
            "ai",
            ablation="noHyp",
        )
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.explore_rounds, 0)
        self.assertEqual(result.predicted_hypothesis_id, "ai.rag_grounding")

    def test_no_ask_never_returns_ask(self) -> None:
        result = self.pipeline.run(
            "light signal changes somehow", "astronomy", ablation="noAsk"
        )
        self.assertNotEqual(result.decision.action.value, "ASK")

    def test_duplicate_explore_round_does_not_add_evidence(self) -> None:
        result = self.pipeline.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        pairs = [(item.hypothesis_id, item.document_id) for item in result.evidence]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_repeated_exploration_queries_are_pruned_before_retrieval(self) -> None:
        result = self.pipeline.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        retrieval_hashes = [
            event.payload["query_hash"]
            for event in result.trace
            if event.stage == "RETRIEVAL"
        ]
        self.assertEqual(len(retrieval_hashes), len(set(retrieval_hashes)))
        self.assertTrue(all(len(query_hash) == 64 for query_hash in retrieval_hashes))
        self.assertEqual(result.retrieval_calls, 5)
        self.assertEqual(result.explore_rounds, 1)
        self.assertEqual(result.retrieval_calls_avoided, 2)
        self.assertEqual(result.pruned_explorations, 1)
        self.assertEqual(result.termination_reason, "repeated_query")
        self.assertEqual(result.decision.action.value, "ASK")
        self.assertEqual(result.predicted_hypothesis_id, "astro.exoplanet_transit")
        self.assertIn("EXPLORATION_PRUNED", {event.stage for event in result.trace})

    def test_novelty_and_belief_metrics_are_exposed_in_trace_and_result(self) -> None:
        result = self.pipeline.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        retrieval_events = [event for event in result.trace if event.stage == "RETRIEVAL"]
        belief_events = [event for event in result.trace if event.stage == "BELIEF"]
        self.assertTrue(retrieval_events)
        self.assertTrue(belief_events)
        self.assertTrue(
            all(0.0 <= event.payload["document_novelty"] <= 1.0 for event in retrieval_events)
        )
        self.assertTrue(
            all(event.payload["total_variation"] >= 0.0 for event in belief_events)
        )
        self.assertTrue(
            all("observed_entropy_reduction" in event.payload for event in belief_events)
        )
        self.assertGreaterEqual(result.mean_document_novelty, 0.0)
        self.assertLessEqual(result.mean_document_novelty, 1.0)
        self.assertGreaterEqual(result.total_belief_variation, 0.0)

    def test_zero_novelty_gate_stops_a_distinct_future_round(self) -> None:
        pipeline = QuasarPipeline.from_config(self.project_config)
        pipeline.deduplicate_queries = False
        pipeline.decision_engine.max_explore_rounds = 3
        result = pipeline.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        self.assertEqual(result.retrieval_calls, 7)
        self.assertEqual(result.explore_rounds, 2)
        self.assertEqual(result.retrieval_calls_avoided, 2)
        self.assertEqual(result.termination_reason, "zero_novel_evidence")
        self.assertEqual(result.decision.action.value, "ASK")
        self.assertIn("ACQUISITION_STOP", {event.stage for event in result.trace})

    def test_benchmark_smoke_is_reproducible(self) -> None:
        runner = BenchmarkRunner(self.project_config)
        first = runner.run(methods=("hybrid", "full"), conditions=("q2",), limit=3)
        second = runner.run(methods=("hybrid", "full"), conditions=("q2",), limit=3)
        self.assertEqual(first["dataset"], second["dataset"])
        for method in ("hybrid", "full"):
            self.assertEqual(
                first["summaries"][method]["overall"]["intent_recovery_rate"],
                second["summaries"][method]["overall"]["intent_recovery_rate"],
            )
        self.assertIn(
            "average_retrieval_calls_avoided",
            first["summaries"]["full"]["overall"],
        )
        self.assertEqual(
            first["paired_comparisons"]["full_minus_hybrid_intent_recovery"]["pairs"],
            3.0,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
