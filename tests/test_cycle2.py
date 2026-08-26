from __future__ import annotations

import json
import unittest
from pathlib import Path

from quasar2.cycle2.action_value import estimate_action_values, q_net_map, select_action
from quasar2.cycle2.observation import mix_kernels, mismatch_severity
from quasar2.cycle2.policies import FORBIDDEN_FEATURE_TOKENS, leakage_features
from quasar2.cycle2.recoverability_state import estimate_recoverability_state
from quasar2.cycle2.synthetic import generate_family_states, generate_mismatch_curve
from quasar2.cycle2.wdi_experiment import SEALED
from quasar2.math.voi import voi_bound_binary
from quasar2.theory.kernels import bernoulli_pair, near_identical_pair


class RecoverabilityStateTests(unittest.TestCase):
    def test_unknown_sigma_under_proxy(self) -> None:
        belief = {"H1": 0.5, "H2": 0.5}
        true = bernoulli_pair(0.9)
        proxy = near_identical_pair()
        est = estimate_recoverability_state(belief, proxy, oracle_run=False)
        self.assertIsNone(est.uncertainty)
        self.assertIsNone(est.misspecification_risk)
        self.assertIn("R_leverage", est.components)

    def test_oracle_records_mismatch(self) -> None:
        belief = {"H1": 0.5, "H2": 0.5}
        true = bernoulli_pair(0.9)
        proxy = near_identical_pair()
        est = estimate_recoverability_state(
            belief, proxy, true_kernels=true, oracle_run=True
        )
        self.assertEqual(est.uncertainty, 0.0)
        self.assertIsNotNone(est.misspecification_risk)
        self.assertGreater(float(est.misspecification_risk), 0.0)


class BoundIsNotQTests(unittest.TestCase):
    def test_explore_q_is_not_t2_bound(self) -> None:
        belief = {"H1": 0.5, "H2": 0.5}
        kernels = bernoulli_pair(0.9)
        estimates = estimate_action_values(belief, kernels, explore_cost=0.1, rho=1.4)
        bound = voi_bound_binary(0.5, kernels["H1"], kernels["H2"]).voi_bound_tv
        q_explore = estimates["EXPLORE"].net_value
        self.assertTrue(estimates["EXPLORE"].t2_is_not_q)
        self.assertNotAlmostEqual(q_explore, bound)

    def test_asymmetric_loss_changes_answer_value(self) -> None:
        belief = {"H1": 0.6, "H2": 0.4}
        kernels = bernoulli_pair(0.8)
        mild = q_net_map(estimate_action_values(belief, kernels, rho=0.5))
        harsh = q_net_map(estimate_action_values(belief, kernels, rho=4.0))
        self.assertGreater(mild["ANSWER"], harsh["ANSWER"])


class ActionMarginTests(unittest.TestCase):
    def test_defer_not_silently_answer_on_empty(self) -> None:
        choice = select_action({}, fallback="DEFER")
        self.assertEqual(choice["selected_action"], "DEFER")
        self.assertEqual(choice["fallback_reason"], "no_candidate_action")

    def test_noisy_ask_not_perfect(self) -> None:
        belief = {"H1": 0.5, "H2": 0.5}
        kernels = near_identical_pair()
        truthful = estimate_action_values(belief, kernels, ask_model="truthful")
        refusal = estimate_action_values(belief, kernels, ask_model="refusal")
        self.assertGreater(truthful["ASK"].net_value, refusal["ASK"].net_value)


class MismatchTests(unittest.TestCase):
    def test_mu_zero_is_matched(self) -> None:
        true = bernoulli_pair(0.9)
        mixed = mix_kernels(true, true, 0.0)
        self.assertEqual(mismatch_severity(mixed, true), 0.0)

    def test_constructed_mismatch_increases_with_mu(self) -> None:
        true = bernoulli_pair(0.9)
        other = {"H1": true["H2"], "H2": true["H1"]}
        m0 = mismatch_severity(mix_kernels(true, other, 0.0), true)
        m1 = mismatch_severity(mix_kernels(true, other, 1.0), true)
        self.assertLess(m0, m1)

    def test_mismatch_curve_has_all_mu(self) -> None:
        rows = generate_mismatch_curve()
        mus = sorted({row["mu"] for row in rows})
        self.assertEqual(mus, [0.0, 0.25, 0.5, 0.75, 1.0])


class FamilyHoldoutTests(unittest.TestCase):
    def test_holdout_families_exist_and_open_set(self) -> None:
        rows = generate_family_states()
        roles = {row["split_role"] for row in rows}
        self.assertIn("development", roles)
        self.assertIn("holdout", roles)
        self.assertTrue(any(row["open_set"] for row in rows))
        self.assertTrue(any(row["anti_quasar"] for row in rows))
        self.assertTrue(any(row["redundancy"] > 0 for row in rows))
        for row in rows:
            self.assertIn("oracle_q", row)
            self.assertEqual(set(row["oracle_q"]), {"ANSWER", "EXPLORE", "ASK", "ANALYZE", "DEFER"})


class LeakageTests(unittest.TestCase):
    def test_forbidden_tokens_caught(self) -> None:
        leaked = leakage_features(("entropy", "oracle_q", "R_star"))
        self.assertTrue(leaked)
        for token in FORBIDDEN_FEATURE_TOKENS:
            self.assertTrue(token)


class OpsCorpusTests(unittest.TestCase):
    def test_ops_bundle_loads_documents(self) -> None:
        from quasar2.cycle2.ops_sim import load_ops_bundle

        bundle = load_ops_bundle()
        self.assertGreater(len(bundle["documents"]), 5)
        self.assertGreater(len(bundle["intents"]), 5)


class WdiSealedTests(unittest.TestCase):
    def test_sealed_constant(self) -> None:
        self.assertEqual(SEALED, "sealed_test")

    def test_plan_exists(self) -> None:
        root = Path(__file__).resolve().parents[1]
        plan = json.loads(
            (root / "experiments" / "analysis_plans" / "wdi_controlled_degradation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("sealed_test", json.dumps(plan))
        self.assertTrue(plan["do_not_access_before_plan_hash"])


class Gate1NotOverwrittenTests(unittest.TestCase):
    def test_gate1_plan_still_fail_rule(self) -> None:
        root = Path(__file__).resolve().parents[1]
        plan = json.loads((root / "experiments" / "analysis_plans" / "gate1.json").read_text(encoding="utf-8"))
        self.assertIn("FAIL", plan["fail_rule"])
        frozen = json.loads(
            (root / "experiments" / "results" / "gate1_cycle1" / "gate1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(frozen["synthetic"]["gate"]["gate1"], "FAIL")
