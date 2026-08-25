from __future__ import annotations

from pathlib import Path
import unittest

from quasar2.config import ProjectConfig
from quasar2.datasets.ops_runbook import documents, write_fixture
from quasar2.experiment import RegimeExperiment
from quasar2.pipeline import QuasarPipeline
from quasar2.regimes import FactorialDegrader, RegimeCell, sample_design
from quasar2.retrieval.factory import build_retriever


class RegimeTests(unittest.TestCase):
    def test_design_is_not_the_full_cartesian_product(self) -> None:
        design = sample_design()
        self.assertEqual(len(design), 9)
        self.assertEqual(design[0].cell_id, "clean")
        self.assertLess(len(design), 4 ** 5)

    def test_factorial_degrader_is_seed_stable(self) -> None:
        cell = RegimeCell("severe", 3, 3, 2, 2, 3)
        degrader = FactorialDegrader(competitor_terms=("dns", "tls", "queue"))
        first = degrader.apply("prod started returning 401 after we rotated keys", cell, seed=42)
        second = degrader.apply("prod started returning 401 after we rotated keys", cell, seed=42)
        self.assertEqual(first, second)
        self.assertNotEqual(first.query, first.query.upper())

    def test_ops_fixture_is_harder_than_a_lexical_copy(self) -> None:
        corpus = documents()
        self.assertGreaterEqual(len(corpus), 30)
        secret_query = "prod started returning 401 after we rotated keys and only some pods fail"
        core = next(document for document in corpus if document.document_id == "ops-sec-core")
        overlap = set(secret_query.lower().split()) & set(core.text.lower().split())
        self.assertLess(len(overlap), 8)

    def test_build_retriever_names_are_matched(self) -> None:
        corpus = documents()
        bm25 = build_retriever(corpus, "bm25")
        hashing = build_retriever(corpus, "dense_hash")
        hybrid = build_retriever(corpus, "hybrid")
        hits = bm25.search("vault lease generation csi volume", top_k=3, domain="ops")
        self.assertTrue(hits)
        self.assertTrue(hashing.search("vault lease generation", top_k=3, domain="ops"))
        self.assertTrue(hybrid.search("vault lease generation", top_k=3, domain="ops"))

    def test_pipeline_accepts_a_non_hybrid_backend(self) -> None:
        root = Path(__file__).resolve().parents[1]
        write_fixture(root)
        config = ProjectConfig.load(root / "configs/v02_regime.yaml")
        pipeline = QuasarPipeline.from_config(
            config, retriever=build_retriever(documents(), "bm25")
        )
        result = pipeline.run(
            "prod started returning 401 after we rotated keys and only some pods fail",
            "ops",
        )
        self.assertTrue(result.retrieval_hits)
        self.assertIn(result.decision.action.value, {"ANSWER", "ASK", "EXPLORE"})

    def test_regime_experiment_smoke_is_paired_and_reports_crossover(self) -> None:
        root = Path(__file__).resolve().parents[1]
        write_fixture(root)
        config = ProjectConfig.load(root / "configs/v02_regime.yaml")
        runner = RegimeExperiment(config)
        results = runner.run(
            methods=("bm25", "full+bm25"),
            seeds=(42,),
            limit=3,
            cells=(RegimeCell("clean", 0, 0, 0, 0, 0), RegimeCell("U3", 0, 0, 0, 3, 0)),
        )
        self.assertEqual(results["schema_version"], "2.0")
        self.assertEqual(results["dataset"]["observations"], 6)
        self.assertIn("full+bm25_minus_bm25_arr", results["paired_comparisons"])
        self.assertIn("bm25", results["interpretation_retrieval_tradeoff"])
        self.assertIn("full+bm25", results["interpretation_retrieval_tradeoff"])
        self.assertEqual(len(results["crossover"]["full+bm25_vs_bm25"]), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
