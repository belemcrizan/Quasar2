from __future__ import annotations

import math
from pathlib import Path
import unittest

from quasar2.belief.updater import BeliefUpdater
from quasar2.config import ProjectConfig
from quasar2.decision.engine import DecisionEngine
from quasar2.decision.utility import UtilityModel
from quasar2.degradation import QueryDegrader
from quasar2.evidence.scorer import EvidenceScorer
from quasar2.hypotheses.catalog import CatalogHypothesisGenerator, HypothesisCatalog
from quasar2.models.evidence import EvidenceBundle
from quasar2.models.hypothesis import Hypothesis, HypothesisCandidate
from quasar2.retrieval import BM25Retriever, HashingDenseRetriever, HybridRetriever, load_corpus
from quasar2.signals.extractor import SignalExtractor, normalize_text, tokenize


class ComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.project_config = ProjectConfig.load(cls.project_root / "configs/poc.yaml")

    def test_normalization_is_accent_and_case_stable(self) -> None:
        self.assertEqual(normalize_text("Órbita, IA & AÇÃO!"), "orbita ia acao")
        self.assertEqual(
            tokenize("The model retrieves useful evidence"),
            ("model", "retrieves", "useful", "evidence"),
        )

    def test_signal_extractor_reports_bounded_quality(self) -> None:
        observation = SignalExtractor({"ai": ("model", "retrieval")}).extract(
            "Model retrieval fails after deployment", "ai"
        )
        self.assertTrue(observation.tokens)
        self.assertLessEqual(observation.signal_quality, 1.0)
        self.assertGreaterEqual(observation.signal_quality, 0.0)
        self.assertTrue(
            math.isclose(observation.signal_quality + observation.estimated_degradation, 1.0)
        )

    def test_degradation_is_deterministic_and_preserves_two_tokens(self) -> None:
        degrader = QueryDegrader()
        first = degrader.degrade(
            "periodic stellar brightness signal from a planet", level=0.9, seed=17
        )
        second = degrader.degrade(
            "periodic stellar brightness signal from a planet", level=0.9, seed=17
        )
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(tokenize(first.query, remove_stopwords=False)), 2)
        self.assertTrue(first.removed_tokens or first.substitutions)

    def test_catalog_ranks_transit_first(self) -> None:
        catalog = HypothesisCatalog.from_directory(
            self.project_config.resolve(str(self.project_config.section("paths")["catalog"]))
        )
        observation = SignalExtractor().extract(
            "starlight dips when something crosses the disk", "astronomy"
        )
        candidates = CatalogHypothesisGenerator(catalog).generate(
            observation, max_candidates=4
        )
        self.assertEqual(candidates[0].hypothesis.hypothesis_id, "astro.exoplanet_transit")
        self.assertGreaterEqual(len(candidates), 2)

    def test_retrievers_return_relevant_grounding_document(self) -> None:
        documents = load_corpus(
            self.project_config.resolve(str(self.project_config.section("paths")["corpus"]))
        )
        bm25 = BM25Retriever(documents)
        dense = HashingDenseRetriever(documents, dimensions=128)
        hybrid = HybridRetriever(bm25, dense)
        query = "retrieval augmented generation grounded answer citation"
        for retriever in (bm25, dense, hybrid):
            hits = retriever.search(query, top_k=5, domain="ai")
            self.assertTrue(hits)
            self.assertTrue(
                any("ai.rag_grounding" in hit.document.hypothesis_ids for hit in hits)
            )

    @staticmethod
    def _candidates() -> tuple[HypothesisCandidate, HypothesisCandidate]:
        left = Hypothesis(
            "left", "test", "Left", "Left hypothesis", ("alpha",), ("red",)
        )
        right = Hypothesis(
            "right", "test", "Right", "Right hypothesis", ("beta",), ("blue",)
        )
        return (
            HypothesisCandidate(left, 0.5, 1, "test"),
            HypothesisCandidate(right, 0.5, 2, "test"),
        )

    def test_belief_update_is_normalized_and_moves_toward_evidence(self) -> None:
        updater = BeliefUpdater(evidence_strength=4.0)
        initial = updater.initialize(self._candidates())
        updated = updater.update(
            initial,
            (
                EvidenceBundle("left", (), 0.8, 2),
                EvidenceBundle("right", (), 0.2, 2),
            ),
            round_index=0,
        )
        self.assertTrue(math.isclose(sum(updated.probabilities.values()), 1.0))
        self.assertGreater(updated.probabilities["left"], initial.probabilities["left"])
        self.assertEqual(updated.top_hypothesis_id, "left")

    def test_evidence_scorer_deduplicates_document_pairs(self) -> None:
        documents = load_corpus(
            self.project_config.resolve(str(self.project_config.section("paths")["corpus"]))
        )
        retriever = BM25Retriever(documents)
        catalog = HypothesisCatalog.from_directory(
            self.project_config.resolve(str(self.project_config.section("paths")["catalog"]))
        )
        candidate = HypothesisCandidate(catalog.get("ai.rag_grounding"), 1.0, 1, "test")
        observation = SignalExtractor().extract("grounded answer from documents", "ai")
        hits = retriever.search("retrieval grounded answer", top_k=2, domain="ai")
        scorer = EvidenceScorer()
        first = scorer.score(observation, candidate, hits, round_index=0, query="initial")
        seen = {(item.hypothesis_id, item.document_id) for item in first.items}
        second = scorer.score(
            observation,
            candidate,
            hits,
            round_index=1,
            query="follow-up",
            seen_pairs=seen,
        )
        self.assertGreater(first.novel_item_count, 0)
        self.assertEqual(second.novel_item_count, 0)
        self.assertEqual(second.aggregate_support, 0.0)

    def test_decision_explores_when_uncertain(self) -> None:
        updater = BeliefUpdater()
        belief = updater.initialize(self._candidates())
        engine = DecisionEngine(
            answer_confidence=0.7,
            answer_margin=0.2,
            minimum_evidence=0.3,
            minimum_exploration_value=0.04,
            max_explore_rounds=2,
            allow_ask=True,
            utility_model=UtilityModel(),
        )
        decision = engine.decide(
            belief,
            {"left": 0.2, "right": 0.2},
            explore_rounds=0,
            discriminative_power=0.8,
        )
        self.assertEqual(decision.action.value, "EXPLORE")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

