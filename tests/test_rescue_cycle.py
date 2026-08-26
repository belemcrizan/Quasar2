from __future__ import annotations

from pathlib import Path
import inspect
import tempfile
import unittest

from quasar2.belief.updater import BeliefUpdater
from quasar2.models.belief import BeliefState
from quasar2.models.evidence import EvidenceBundle, EvidenceItem
from quasar2.models.hypothesis import Hypothesis, HypothesisCandidate
from quasar2.models.observation import Observation
from quasar2.rescue.belief import DiscriminativeBeliefUpdater, odds
from quasar2.rescue.evidence_oracle import evaluate_case, sufficient_evidence
from quasar2.rescue.leakage import LeakageError, SealedGold, assert_no_gold_fields
from quasar2.rescue.metrics import realized_utility, rescue_metrics, wilson_interval
from quasar2.rescue.queries import build_discriminative_queries
from quasar2.rescue.taxonomy import classify_primary
from quasar2.retrieval.base import Document


def _hyp(hid: str, label: str, discs: tuple[str, ...]) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=hid,
        domain="astronomy",
        label=label,
        description=label,
        anchors=(label,),
        discriminators=discs,
    )


def _item(hid: str, doc: str, support: float, *, foreign: bool = False) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"{hid}:{doc}",
        hypothesis_id=hid,
        document_id=doc,
        title=doc,
        snippet="x",
        retrieval_score=support,
        observation_coverage=support,
        anchor_coverage=support,
        discriminator_coverage=support,
        foreign_hypothesis=foreign,
        support_score=support,
        retrieval_rank=1,
        round_index=0,
        query="q",
    )


class RescueUnitTests(unittest.TestCase):
    def test_wilson_and_rescue_denominators(self) -> None:
        interval = wilson_interval(0, 10)
        self.assertEqual(interval["k"], 0)
        self.assertEqual(interval["n"], 10)
        rows = [
            {"intent_id": "a", "fast_correct": False, "deliberative_correct": True, "delta_u": 0.5},
            {"intent_id": "a", "fast_correct": True, "deliberative_correct": False, "delta_u": -0.5},
            {"intent_id": "b", "fast_correct": True, "deliberative_correct": True, "delta_u": 0.0},
            {"intent_id": "c", "fast_correct": False, "deliberative_correct": False, "delta_u": 0.0},
        ]
        metrics = rescue_metrics(rows)
        self.assertEqual(metrics["counts"]["RESCUE"], 1)
        self.assertEqual(metrics["RescueRate_FW"]["n"], 2)
        self.assertEqual(metrics["OverthinkingRate_FC"]["n"], 2)
        self.assertEqual(metrics["NetRescueRate"]["numerator"], 0)

    def test_utility_penalizes_wrong_answer_and_extra_calls(self) -> None:
        good = realized_utility(correct=True, action="ANSWER", retrieval_calls=4, seed_calls=4)
        extra = realized_utility(correct=True, action="ANSWER", retrieval_calls=7, seed_calls=4)
        wrong = realized_utility(correct=False, action="ANSWER", retrieval_calls=4, seed_calls=4)
        self.assertGreater(good, extra)
        self.assertGreater(good, wrong)

    def test_leakage_guard(self) -> None:
        with self.assertRaises(LeakageError):
            assert_no_gold_fields({"correct_hypothesis": "x"}, context="test")
        sealed = SealedGold(correct_hypothesis="secret")
        with self.assertRaises(LeakageError):
            _ = sealed.correct_hypothesis

    def test_query_builder_signature_has_no_gold(self) -> None:
        names = inspect.signature(build_discriminative_queries).parameters
        self.assertNotIn("correct_hypothesis", names)
        self.assertNotIn("gold_doc_ids", names)
        obs = Observation(
            observation_id="1",
            raw_query="dip in starlight",
            domain="astronomy",
            normalized_query="dip in starlight",
            tokens=("dip", "starlight"),
        )
        left = _hyp("h1", "transit", ("flat", "bottom", "period"))
        right = _hyp("h2", "flare", ("fast", "rise", "xray"))
        belief = BeliefState(
            probabilities={"h1": 0.55, "h2": 0.45},
            logits={"h1": 0.1, "h2": 0.0},
            entropy=0.68,
            normalized_entropy=0.98,
            top_hypothesis_id="h1",
            top_probability=0.55,
            margin=0.10,
            round_index=0,
        )
        cands = (
            HypothesisCandidate(left, 0.4, 1, "x"),
            HypothesisCandidate(right, 0.3, 2, "y"),
        )
        queries = build_discriminative_queries(obs, cands, belief)
        blob = " ".join(queries.values())
        self.assertNotIn("secret_label", blob)
        with self.assertRaises(LeakageError):
            poisoned = Observation(
                observation_id="2",
                raw_query="dip",
                domain="astronomy",
                normalized_query="dip",
                tokens=("dip",),
                metadata={"correct_hypothesis": "h1"},
            )
            build_discriminative_queries(poisoned, cands, belief)

    def test_belief_properties(self) -> None:
        left = _hyp("h1", "transit", ("period",))
        right = _hyp("h2", "flare", ("xray",))
        cands = (
            HypothesisCandidate(left, 0.5, 1, "x"),
            HypothesisCandidate(right, 0.5, 2, "y"),
        )
        updater = DiscriminativeBeliefUpdater(evidence_strength=4.0)
        prior = updater.initialize(cands)
        self.assertAlmostEqual(sum(prior.probabilities.values()), 1.0, places=9)
        unchanged = updater.update(prior, (), round_index=0)
        self.assertEqual(dict(unchanged.probabilities), dict(prior.probabilities))
        pro = [
            EvidenceBundle("h1", (_item("h1", "d1", 0.9),), 0.9, 1),
            EvidenceBundle("h2", (), 0.0, 0),
        ]
        after_pro = updater.update(prior, pro, round_index=1)
        self.assertGreater(odds(after_pro.probabilities, "h1"), odds(prior.probabilities, "h1"))
        contra = [
            EvidenceBundle("h1", (_item("h1", "d2", 0.9, foreign=True),), 0.9, 1),
            EvidenceBundle("h2", (), 0.0, 0),
        ]
        after_contra = updater.update(prior, contra, round_index=1)
        self.assertLess(odds(after_contra.probabilities, "h1"), odds(prior.probabilities, "h1"))
        dup = [
            EvidenceBundle(
                "h1",
                (_item("h1", "d1", 0.9), _item("h1", "d1", 0.9)),
                0.9,
                2,
            ),
            EvidenceBundle("h2", (), 0.0, 0),
        ]
        once = updater.update(
            prior,
            [EvidenceBundle("h1", (_item("h1", "d1", 0.9),), 0.9, 1), EvidenceBundle("h2", (), 0.0, 0)],
            round_index=1,
        )
        twice = updater.update(prior, dup, round_index=1)
        self.assertAlmostEqual(once.probabilities["h1"], twice.probabilities["h1"], places=6)

    def test_legacy_updater_untouched_by_disc_class(self) -> None:
        self.assertTrue(issubclass(DiscriminativeBeliefUpdater, BeliefUpdater))
        self.assertIsNot(DiscriminativeBeliefUpdater.update, BeliefUpdater.update)

    def test_oracle_rejects_irrelevant_and_classifies(self) -> None:
        h_star = _hyp("h1", "transit", ("flat", "bottom"))
        other = _hyp("h2", "flare", ("xray",))
        gold = Document(
            "g1",
            "astronomy",
            "Transit disc",
            "flat bottom orbital period",
            ("h1",),
            (),
            {"kind": "discriminative"},
        )
        noise = Document("n1", "astronomy", "Unrelated", "pump espresso", (), (), {})
        flag, ids, _ = sufficient_evidence((gold, noise), h_star, (h_star, other))
        self.assertEqual(flag, "true")
        self.assertEqual(ids, ("g1",))
        rec = evaluate_case(
            query_id="q",
            intent_id="i",
            regime="astronomy:q0",
            correct_hypothesis=None,
            catalog_ids={"h1"},
            documents=(gold,),
            generated_ids=("h2",),
            competitors=(other,),
            corpus_version="test",
        )
        self.assertEqual(rec.required_intervention, "OPEN_SET")

    def test_taxonomy_order(self) -> None:
        label, _, _ = classify_primary(
            catalog_has_h_star=False,
            sufficient="true",
            h_star_in_generated=False,
            gold_retrieved=False,
            oracle_hypothesis_correct=True,
            oracle_retrieval_correct=True,
            oracle_evidence_correct=True,
            oracle_belief_correct=True,
            predicted_correct=False,
            belief_top_is_h_star=False,
            delta_b_star=0.0,
            factorial_conflict=False,
        )
        self.assertEqual(label, "OPEN_SET")
        label, _, _ = classify_primary(
            catalog_has_h_star=True,
            sufficient="false",
            h_star_in_generated=True,
            gold_retrieved=False,
            oracle_hypothesis_correct=False,
            oracle_retrieval_correct=False,
            oracle_evidence_correct=False,
            oracle_belief_correct=False,
            predicted_correct=False,
            belief_top_is_h_star=False,
            delta_b_star=0.0,
            factorial_conflict=False,
        )
        self.assertEqual(label, "MISSING_EVIDENCE")
        label, _, _ = classify_primary(
            catalog_has_h_star=True,
            sufficient="true",
            h_star_in_generated=False,
            gold_retrieved=False,
            oracle_hypothesis_correct=True,
            oracle_retrieval_correct=True,
            oracle_evidence_correct=True,
            oracle_belief_correct=True,
            predicted_correct=False,
            belief_top_is_h_star=False,
            delta_b_star=0.1,
            factorial_conflict=False,
        )
        self.assertEqual(label, "HYPOTHESIS_FAILURE")

    def test_removing_h_star_docs_drops_recoverability(self) -> None:
        h_star = _hyp("h1", "transit", ("flat",))
        other = _hyp("h2", "flare", ("xray",))
        gold = Document("g1", "astronomy", "t", "flat bottom", ("h1",), (), {"kind": "discriminative"})
        with_gold, _, _ = sufficient_evidence((gold,), h_star, (h_star, other))
        without, ids, _ = sufficient_evidence((), h_star, (h_star, other))
        self.assertEqual(with_gold, "true")
        self.assertEqual(without, "false")
        self.assertEqual(ids, ())

    def test_predicted_pipeline_rejects_gold(self) -> None:
        from quasar2.config import ProjectConfig
        from quasar2.rescue.runner import _build_rescue_pipeline

        root = Path(__file__).resolve().parents[1]
        pipeline, _, catalog, _ = _build_rescue_pipeline(ProjectConfig.load(root / "configs" / "poc.yaml"))
        gold = catalog.get("astro.exoplanet_transit")
        with self.assertRaises(LeakageError):
            pipeline.run(
                "starlight dip",
                "astronomy",
                arm="fast",
                mode="predicted_hypothesis",
                gold_hypothesis=gold,
            )


class RescueIntegrationTests(unittest.TestCase):
    def test_smoke_runner_and_cli_exist(self) -> None:
        from quasar2.cli import build_parser

        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        for name in (
            "error-anatomy",
            "oracle-evaluate",
            "discriminative-experiment",
            "recoverability-v2",
            "action-value-experiment",
            "cycle-report",
            "rescue-cycle",
        ):
            self.assertIn(name, choices)

    def test_smoke_cycle_limit_one_intent(self) -> None:
        from quasar2.rescue.runner import run_rescue_cycle

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "run"
            payload = run_rescue_cycle(
                output=dest,
                config_path=str(root / "configs" / "poc.yaml"),
                seed=42,
                limit=1,
                conditions=("q2",),
            )
            self.assertGreaterEqual(payload["n_queries"], 1)
            self.assertTrue((dest / "anatomy.jsonl").exists())
            self.assertTrue((dest / "REPORT.md").exists())
            self.assertEqual(payload["gates"]["leakage_contract"], "PASS")
            self.assertIn("cycle4_anatomy", payload["gates"])
            self.assertNotIn("optimal", (dest / "REPORT.md").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
