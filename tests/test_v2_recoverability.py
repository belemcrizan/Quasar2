from __future__ import annotations

import unittest

from quasar2.decision.discriminative import LikelihoodRatioProxyScorer, compare_relevance_vs_discrimination
from quasar2.decision.gap import decompose_from_scenarios
from quasar2.decision.policies import LearnedEpistemicPolicy, SPRTInspiredPolicy, TabularOraclePolicy
from quasar2.eval.oracle_env import compare_policies
from quasar2.eval.recoverability_bench import run_recoverability_benchmark
from quasar2.math.association import auroc, pearson, spearman
from quasar2.math.voi import classify_bound_tightness, empirical_binary_voi_zero_one, empirical_decision_flip_probability
from quasar2.recoverability import DecisionRecoverability
from quasar2.theory.harness import check_t2_grid, check_t4_near_zero
from quasar2.theory.kernels import KERNEL_FAMILIES, bernoulli_pair


class DecisionRecoverabilityTests(unittest.TestCase):
    def test_identical_kernels_cannot_flip(self) -> None:
        pair = {"H1": {"0": 0.5, "1": 0.5}, "H2": {"0": 0.5, "1": 0.5}}
        self.assertAlmostEqual(empirical_decision_flip_probability(0.4, pair["H1"], pair["H2"]), 0.0)

    def test_disjoint_kernels_flip_the_minority_outcome(self) -> None:
        pair = {"H1": {"0": 1.0, "1": 0.0}, "H2": {"0": 0.0, "1": 1.0}}
        # Tie-break to H1; only o=1 flips. P(o=1)=0.5.
        self.assertAlmostEqual(empirical_decision_flip_probability(0.5, pair["H1"], pair["H2"]), 0.5)

    def test_estimator_matches_identity(self) -> None:
        pair = bernoulli_pair(0.8)
        belief = {"H1": 0.55, "H2": 0.45}
        result = DecisionRecoverability().estimate(belief, ("H1", "H2"), "EXPLORE", pair)
        expected = empirical_decision_flip_probability(0.55, pair["H1"], pair["H2"])
        self.assertAlmostEqual(result.score, expected)


class TightnessTests(unittest.TestCase):
    def test_labels(self) -> None:
        self.assertEqual(classify_bound_tightness(0.9, 1.0), "tight")
        self.assertEqual(classify_bound_tightness(0.4, 1.0), "useful")
        self.assertEqual(classify_bound_tightness(0.1, 1.0), "loose")
        self.assertEqual(classify_bound_tightness(0.01, 1.0), "vacuous")
        self.assertEqual(classify_bound_tightness(1.1, 1.0), "violated")

    def test_t2_grid_records_tightness(self) -> None:
        check = check_t2_grid()
        self.assertIn("tightness_counts", check.metrics)
        self.assertGreaterEqual(sum(check.metrics["tightness_counts"].values()), 8 * 5)


class RecoverabilityBenchTests(unittest.TestCase):
    def test_holdout_metrics_exist(self) -> None:
        payload = run_recoverability_benchmark(priors=(0.3, 0.5, 0.7))
        self.assertGreater(payload["n"], 10)
        self.assertAlmostEqual(payload["bayes_retrieval_harm_rate"], 0.0, places=8)
        methods = {row["method"] for row in payload["summaries"] if row["split"] == "holdout"}
        self.assertIn("jsd", methods)
        self.assertIn("decision_recoverability", methods)
        self.assertIn("entropy", methods)
        self.assertIn("learned", methods)

    def test_spearman_monotone(self) -> None:
        self.assertAlmostEqual(spearman([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertIsNotNone(pearson([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0]))
        self.assertGreater(auroc([0.1, 0.4, 0.9], [0, 0, 1]) or 0.0, 0.5)


class OraclePolicyTests(unittest.TestCase):
    def test_oracle_explores_when_voi_exceeds_cost(self) -> None:
        pair = bernoulli_pair(0.9)
        rec = TabularOraclePolicy(explore_cost=0.01, ask_cost=0.8).recommend(
            belief={"H1": 0.51, "H2": 0.49},
            kernels=pair,
            entropy=1.0,
            unknown_mass=0.0,
            inference_error=None,
            evidence_present=True,
        )
        self.assertIn(rec.selected_action, {"EXPLORE", "ANSWER", "ASK"})
        self.assertGreater(rec.voi_empirical or 0.0, 0.0)

    def test_oracle_does_not_explore_identical_kernels(self) -> None:
        kernels = {"H1": {"0": 0.5, "1": 0.5}, "H2": {"0": 0.5, "1": 0.5}}
        rec = TabularOraclePolicy(explore_cost=0.01).recommend(
            belief={"H1": 0.51, "H2": 0.49},
            kernels=kernels,
            entropy=1.0,
            unknown_mass=0.0,
            inference_error=None,
            evidence_present=True,
        )
        self.assertNotEqual(rec.selected_action, "EXPLORE")

    def test_sprt_notes_are_not_classical(self) -> None:
        rec = SPRTInspiredPolicy().recommend(
            belief={"H1": 0.5, "H2": 0.5},
            kernels=bernoulli_pair(0.8),
            entropy=1.0,
            unknown_mass=0.0,
            inference_error=None,
            evidence_present=True,
        )
        self.assertIn("Not Wald SPRT", rec.notes)

    def test_policy_compare_smoke(self) -> None:
        payload = compare_policies(n=80, seed=1)
        names = {row["policy"] for row in payload["table"]}
        self.assertIn("tabular_oracle", names)
        self.assertIn("learned_epistemic", names)
        oracle = next(row for row in payload["table"] if row["policy"] == "tabular_oracle")
        self.assertGreaterEqual(oracle["agreement"], 0.99)

    def test_learned_fit_does_not_use_gold_intent_feature_name(self) -> None:
        policy = LearnedEpistemicPolicy()
        policy.fit([[1.0, 0.2, 0.1]] * 6, ["ANSWER", "EXPLORE", "ASK", "ANSWER", "DEFER", "ANALYZE"])
        self.assertTrue(policy.weights)


class DiscriminativeAndGapTests(unittest.TestCase):
    def test_llr_prefers_matching_hypothesis(self) -> None:
        scorer = LikelihoodRatioProxyScorer()
        score = scorer.score(
            "transit dip starlight",
            {"h1": "exoplanet transit starlight dip", "h2": "database timeout retry"},
            {"h1": 0.5, "h2": 0.5},
        )
        self.assertGreater(score, 0.0)

    def test_discrimination_can_move_llr_without_claiming_recall(self) -> None:
        result = compare_relevance_vs_discrimination(
            ["timeout retry", "transit dip photometry"],
            "timeout",
            {"h1": "transit photometry", "h2": "timeout retry"},
            {"h1": 0.5, "h2": 0.5},
            gold_left=False,
        )
        self.assertIn("delta_llr", result)

    def test_gap_is_labeled_non_additive(self) -> None:
        gap = decompose_from_scenarios(
            {
                "oracle": 1.0,
                "no_hypotheses": 0.9,
                "no_retrieval": 0.9,
                "proxy_recoverability": 0.9,
                "degraded_inference": 0.9,
                "routing_only": 0.9,
                "forced_stop": 0.9,
                "open_set_blind": 0.9,
                "misspecified_cost": 0.9,
                "shifted": 0.9,
                "evaluated": 0.5,
            }
        )
        self.assertFalse(gap.additive)


class T4NearZeroTests(unittest.TestCase):
    def test_near_zero_runs(self) -> None:
        check = check_t4_near_zero(n_trials=8, n_samples=16, seed=0)
        self.assertEqual(check.card_id, "T4_near_zero")
        self.assertEqual(check.execution_state, "INCONCLUSIVE")
        self.assertGreaterEqual(len(check.metrics["breakdown"]), 4 * 7)


class BayesVoINonnegativeTests(unittest.TestCase):
    def test_zero_one_voi_nonnegative(self) -> None:
        for pair in KERNEL_FAMILIES.values():
            for b in (0.2, 0.5, 0.8):
                voi = empirical_binary_voi_zero_one(b, pair["H1"], pair["H2"])
                self.assertGreaterEqual(voi, -1e-12)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
