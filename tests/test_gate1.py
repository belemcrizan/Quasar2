from __future__ import annotations

import json
import unittest
from pathlib import Path

from quasar2.eval.gate1 import (
    ALL_PREDICTORS,
    analysis_plan_hash,
    classify_delta,
    leakage_audit,
    load_analysis_plan,
    realized_utility,
    run_gate1_audit,
    synthesize_gate1_rows,
)
from quasar2.eval.stress_regimes import REGIME_SPECS, generate_regime_states, split_counts
from quasar2.math.bootstrap import cluster_bootstrap_mean
from quasar2.recoverability import DEPLOYMENT_FEATURE_NAMES, deployment_features


class StressRegimeTests(unittest.TestCase):
    def test_regimes_are_frozen_and_include_anti_quasar(self) -> None:
        ids = {spec["regime_id"] for spec in REGIME_SPECS}
        self.assertIn("high_H_high_R", ids)
        self.assertIn("high_H_low_R", ids)
        self.assertIn("false_recoverability", ids)
        self.assertIn("hidden_recoverability", ids)
        self.assertIn("misspecified_observation", ids)
        self.assertIn("sealed_pro", ids)
        roles = {spec["split_role"] for spec in REGIME_SPECS}
        self.assertEqual(
            roles,
            {"development", "model_selection", "registered_test", "sealed_replication"},
        )

    def test_generator_is_deterministic(self) -> None:
        first = generate_regime_states()
        second = generate_regime_states()
        self.assertEqual([row["state_id"] for row in first], [row["state_id"] for row in second])
        counts = split_counts(first)
        self.assertGreater(counts["registered_test"], 0)
        self.assertGreater(counts["sealed_replication"], 0)


class AnalysisPlanTests(unittest.TestCase):
    def test_hash_stable(self) -> None:
        plan = load_analysis_plan()
        self.assertEqual(analysis_plan_hash(plan), analysis_plan_hash(plan))
        self.assertEqual(len(analysis_plan_hash(plan)), 64)
        self.assertIn("pass_rule", plan)


class LeakageTests(unittest.TestCase):
    def test_feature_names_exclude_gold_and_outcomes(self) -> None:
        joined = " ".join(DEPLOYMENT_FEATURE_NAMES).lower()
        for token in ("gold", "correct_hypothesis", "oracle_q", "delta_u"):
            self.assertNotIn(token, joined)

    def test_extra_gold_key_does_not_change_features(self) -> None:
        belief = {"H1": 0.55, "H2": 0.45}
        kernels = {"H1": {"0": 0.2, "1": 0.8}, "H2": {"0": 0.8, "1": 0.2}}
        base = deployment_features(belief, ("H1", "H2"), kernels)
        poisoned = dict(belief)
        poisoned["gold"] = 1.0
        shifted = deployment_features(poisoned, ("H1", "H2"), kernels)
        self.assertEqual(base, shifted)


class UtilityLabelTests(unittest.TestCase):
    def test_margin_labels(self) -> None:
        self.assertEqual(classify_delta(0.2, 0.05), "BENEFICIAL")
        self.assertEqual(classify_delta(-0.2, 0.05), "HARMFUL")
        self.assertEqual(classify_delta(0.01, 0.05), "NEAR_ZERO")

    def test_wrong_answer_is_penalized_only_on_answer(self) -> None:
        wrong_answer = realized_utility(
            correct=False, action="ANSWER", retrieval_calls=1, u_correct=1.0, u_wrong=1.4, c_call=0.1, ask_cost=0.28
        )
        wrong_ask = realized_utility(
            correct=False, action="ASK", retrieval_calls=1, u_correct=1.0, u_wrong=1.4, c_call=0.1, ask_cost=0.28
        )
        self.assertLess(wrong_answer, wrong_ask)


class Gate1SyntheticTests(unittest.TestCase):
    def test_bound_is_not_used_as_q(self) -> None:
        plan = load_analysis_plan()
        rows, _ = synthesize_gate1_rows(plan)
        self.assertTrue(all(row["voi_bound_is_not_q"] for row in rows))
        self.assertTrue(all(row["identification"] == "SIMULATOR_CAUSAL_WITHIN_MODEL" for row in rows))

    def test_predictors_ignore_true_kernels_when_proxy_differs(self) -> None:
        plan = load_analysis_plan()
        rows, _ = synthesize_gate1_rows(plan)
        hidden = next(row for row in rows if row["regime_id"] == "hidden_recoverability")
        false = next(row for row in rows if row["regime_id"] == "false_recoverability")
        self.assertLess(hidden["predictors"]["decision_recoverability"], false["predictors"]["decision_recoverability"])
        self.assertGreater(hidden["voi_oracle_raw"], false["voi_oracle_raw"])

    def test_leakage_audit_passes(self) -> None:
        plan = load_analysis_plan()
        rows, _ = synthesize_gate1_rows(plan)
        audit = leakage_audit(rows)
        self.assertTrue(audit["pass"])

    def test_registered_eval_does_not_use_sealed(self) -> None:
        payload = run_gate1_audit(include_fixture=False)
        self.assertTrue(payload["synthetic"]["sealed_unused_for_decision"])
        self.assertIn(payload["synthetic"]["gate"]["gate1"], {"PASS", "PARTIAL", "FAIL", "INCONCLUSIVE"})
        self.assertGreater(payload["synthetic"]["n_registered_test"], 0)
        methods = {row["method"] for row in payload["synthetic"]["method_table_registered_test"]}
        self.assertIn("decision_recoverability", methods)
        self.assertIn("entropy", methods)
        sealed_events = [event for event in payload["synthetic"]["test_access_log"] if "sealed" in event["event"]]
        self.assertTrue(all(event["used_for_gate"] is False for event in sealed_events))
        for predictor in ALL_PREDICTORS:
            if predictor in ("learned",):
                continue
            self.assertTrue(any(row["method"] == predictor for row in payload["synthetic"]["method_table_registered_test"]))

    def test_plan_file_matches_loaded_plan(self) -> None:
        path = Path(__file__).resolve().parents[1] / "experiments" / "analysis_plans" / "gate1.json"
        disk = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(analysis_plan_hash(disk), analysis_plan_hash(load_analysis_plan()))


class BootstrapTests(unittest.TestCase):
    def test_cluster_bootstrap_mean_recovers_constant(self) -> None:
        values = [1.0, 1.0, 1.0, 1.0]
        result = cluster_bootstrap_mean(values, ["a", "a", "b", "b"], samples=50, seed=0)
        self.assertAlmostEqual(result["point"], 1.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
