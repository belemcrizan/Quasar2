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
        self.assertEqual(
            first["paired_comparisons"]["full_minus_hybrid_intent_recovery"]["pairs"],
            3.0,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
