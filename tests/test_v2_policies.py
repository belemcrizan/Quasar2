from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from quasar2.decision.conformal import highest_mass_set, split_conformal_set
from quasar2.decision.kernels import bernoulli_support_kernels
from quasar2.decision.policies import MyopicVoIPolicy, ThresholdPolicy
from quasar2.decision.shadow import build_shadow_telemetry, recommended_action_v2_shadow
from quasar2.math.voi import empirical_binary_voi_zero_one, voi_bound_binary
from quasar2.models.belief import BeliefState
from quasar2.models.decision import Action, Decision
from quasar2.reporting.phase_diagram import build_diagram, write_diagrams
from quasar2.reporting.registry import allocate_run_dir
from quasar2.theory.harness import check_t2_grid, check_t4_families
from quasar2.theory.kernels import KERNEL_FAMILIES


class EmpiricalVoITests(unittest.TestCase):
    def test_zero_one_voi_respects_lipschitz_bound(self) -> None:
        for family, pair in KERNEL_FAMILIES.items():
            bound = voi_bound_binary(0.4, pair["H1"], pair["H2"])
            empirical = empirical_binary_voi_zero_one(0.4, pair["H1"], pair["H2"])
            self.assertLessEqual(empirical, bound.voi_bound_tv + 1e-9, family)
            self.assertGreaterEqual(empirical, -1e-12, family)


class QuadrantAndPolicyTests(unittest.TestCase):
    def test_low_uncertainty_low_recoverability_answers(self) -> None:
        self.assertEqual(
            recommended_action_v2_shadow(
                entropy=0.1, recoverability=0.05, inference_error=None, unknown_mass=0.0
            ),
            "ANSWER",
        )

    def test_high_uncertainty_high_recoverability_explores(self) -> None:
        self.assertEqual(
            recommended_action_v2_shadow(
                entropy=0.8, recoverability=0.6, inference_error=None, unknown_mass=0.0
            ),
            "EXPLORE",
        )

    def test_high_uncertainty_low_recoverability_asks(self) -> None:
        self.assertEqual(
            recommended_action_v2_shadow(
                entropy=0.8, recoverability=0.05, inference_error=None, unknown_mass=0.0
            ),
            "ASK",
        )

    def test_myopic_does_not_explore_when_kernels_identical(self) -> None:
        kernels = {
            "h1": {"hit": 0.5, "miss": 0.5},
            "h2": {"hit": 0.5, "miss": 0.5},
        }
        rec = MyopicVoIPolicy().recommend(
            belief={"h1": 0.55, "h2": 0.45},
            kernels=kernels,
            entropy=0.99,
            unknown_mass=0.0,
            inference_error=None,
            evidence_present=True,
        )
        self.assertAlmostEqual(rec.raw_voi or 0.0, 0.0, places=8)
        self.assertNotEqual(rec.selected_action, "EXPLORE")

    def test_no_explore_ablation_forbids_explore(self) -> None:
        kernels = bernoulli_support_kernels({"h1": 0.9, "h2": 0.1})
        rec = MyopicVoIPolicy(ablation="noExplore").recommend(
            belief={"h1": 0.5, "h2": 0.5},
            kernels=kernels,
            entropy=0.9,
            unknown_mass=0.0,
            inference_error=None,
            evidence_present=True,
        )
        self.assertNotEqual(rec.selected_action, "EXPLORE")

    def test_threshold_policy_defers_on_unknown(self) -> None:
        rec = ThresholdPolicy().recommend(
            top_probability=0.9,
            margin=0.5,
            unknown_mass=0.7,
            entropy=0.1,
        )
        self.assertEqual(rec.selected_action, "DEFER")


class ConformalTests(unittest.TestCase):
    def test_highest_mass_is_heuristic(self) -> None:
        result = highest_mass_set({"a": 0.8, "b": 0.15, "c": 0.05}, alpha=0.25)
        self.assertEqual(result.members, ("a",))
        self.assertFalse(result.coverage_guaranteed)

    def test_split_conformal_includes_below_quantile(self) -> None:
        calibration = [0.1, 0.2, 0.3, 0.4, 0.9]
        result = split_conformal_set({"h1": 0.15, "h2": 0.95}, calibration, alpha=0.2)
        self.assertIn("h1", result.members)
        self.assertEqual(result.method, "split_conformal")


class ShadowTelemetryTests(unittest.TestCase):
    def test_shadow_records_proxy_recoverability(self) -> None:
        belief = BeliefState(
            probabilities={"h1": 0.7, "h2": 0.3},
            logits={"h1": 0.0, "h2": 0.0},
            entropy=math.log(2.0) * 0.88,
            normalized_entropy=0.88,
            top_hypothesis_id="h1",
            top_probability=0.7,
            margin=0.4,
            round_index=0,
        )
        decision = Decision(
            action=Action.ASK,
            selected_hypothesis_id=None,
            utilities={"ANSWER": 0.1, "EXPLORE": 0.2, "ASK": 0.3},
            rationale="test",
            confidence=0.7,
            margin=0.4,
            expected_information_gain=0.0,
        )
        telemetry = build_shadow_telemetry(
            belief,
            decision,
            supports={"h1": 0.8, "h2": 0.2},
        )
        self.assertEqual(telemetry.executed_action_legacy, "ASK")
        self.assertIsNotNone(telemetry.recommended_action_v2)
        self.assertIsNotNone(telemetry.recoverability)
        self.assertEqual(telemetry.kernel_source, "bernoulli_support_proxy")
        self.assertGreaterEqual(telemetry.conformal_set_size or 0, 1)


class RegistryAndPhaseTests(unittest.TestCase):
    def test_registry_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = allocate_run_dir(tmp, run_id="fixed")
            self.assertTrue(first.exists())
            with self.assertRaises(FileExistsError):
                allocate_run_dir(tmp, run_id="fixed")

    def test_phase_diagram_writes_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = write_diagrams(dest, axes=("ambiguity_recoverability",), step=0.5)
            self.assertTrue(path.exists())
            self.assertTrue((dest / "phase_diagrams.csv").exists())
            self.assertTrue((dest / "phase_diagrams.md").exists())
            self.assertTrue((dest / "phase_diagrams.html").exists())
            diagram = build_diagram("ambiguity_recoverability", step=0.5)
            self.assertIn("ANSWER", diagram["action_counts"])


class TheoremGridTests(unittest.TestCase):
    def test_t2_grid_identity(self) -> None:
        check = check_t2_grid()
        self.assertEqual(check.execution_state, "PASS_WITHIN_ASSUMPTIONS")
        self.assertGreaterEqual(len(check.metrics["families"]), 6)

    def test_t4_families_records_breakdown(self) -> None:
        check = check_t4_families(n_trials=12, n_samples=20, seed=2)
        self.assertEqual(check.card_id, "T4_families")
        self.assertIn("breakdown", check.metrics)

    def test_t2_grid_tightness_present(self) -> None:
        check = check_t2_grid()
        self.assertIn("tightness_counts", check.metrics)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
