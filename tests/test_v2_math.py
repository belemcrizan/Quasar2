from __future__ import annotations

import math
import random
import unittest

from quasar2.math.conventions import LipschitzNorm, MeasureConventions
from quasar2.math.divergences import entropy, kl_divergence, prior_dispersion_binary, total_variation, weighted_jsd
from quasar2.math.information import information_difference, surprisal
from quasar2.math.numerical import normalize_mass
from quasar2.math.voi import expected_binary_belief_movement, voi_bound_binary, voi_bound_general
from quasar2.recoverability import ESTIMATORS


class DivergenceTests(unittest.TestCase):
    def test_probabilities_normalize(self) -> None:
        mass = normalize_mass({"a": 2.0, "b": 2.0})
        self.assertAlmostEqual(sum(mass.values()), 1.0)

    def test_kl_direction_and_zeros(self) -> None:
        p = {"0": 1.0, "1": 0.0}
        q = {"0": 0.5, "1": 0.5}
        forward = kl_divergence(p, q)
        reverse = kl_divergence(q, p)
        self.assertGreater(forward, 0.0)
        self.assertTrue(math.isinf(reverse))
        self.assertNotAlmostEqual(forward, reverse)

    def test_kl_smoothing_finite(self) -> None:
        p = {"0": 1.0, "1": 0.0}
        q = {"0": 0.5, "1": 0.5}
        value = kl_divergence(p, q, smooth=1e-6)
        reverse = kl_divergence(q, p, smooth=1e-6)
        self.assertTrue(math.isfinite(value))
        self.assertTrue(math.isfinite(reverse))

    def test_tv_is_half_l1_not_l1(self) -> None:
        p = {"0": 1.0, "1": 0.0}
        q = {"0": 0.0, "1": 1.0}
        self.assertAlmostEqual(total_variation(p, q), 1.0)
        self.assertAlmostEqual(total_variation(p, p), 0.0)

    def test_entropy_uniform(self) -> None:
        self.assertAlmostEqual(entropy({"a": 0.5, "b": 0.5}), math.log(2.0))

    def test_jsd_equals_zero_when_kernels_equal(self) -> None:
        kernels = {"h1": {"x": 0.4, "y": 0.6}, "h2": {"x": 0.4, "y": 0.6}}
        weights = {"h1": 0.3, "h2": 0.7}
        self.assertAlmostEqual(weighted_jsd(kernels, weights), 0.0, places=12)


class VoIBoundTests(unittest.TestCase):
    def test_extreme_priors_zero_movement(self) -> None:
        p1 = {"0": 0.9, "1": 0.1}
        p2 = {"0": 0.1, "1": 0.9}
        self.assertAlmostEqual(expected_binary_belief_movement(0.0, p1, p2), 0.0)
        self.assertAlmostEqual(expected_binary_belief_movement(1.0, p1, p2), 0.0)

    def test_identical_kernels_zero_tv_and_voi_bound(self) -> None:
        p = {"0": 0.2, "1": 0.8}
        bound = voi_bound_binary(0.4, p, p)
        self.assertAlmostEqual(bound.recoverability_tv, 0.0)
        self.assertAlmostEqual(bound.voi_bound_tv, 0.0)
        self.assertTrue(bound.identity_holds)

    def test_disjoint_support_tv_one(self) -> None:
        p1 = {"0": 1.0, "1": 0.0}
        p2 = {"0": 0.0, "1": 1.0}
        bound = voi_bound_binary(0.5, p1, p2)
        self.assertAlmostEqual(bound.recoverability_tv, 1.0)
        self.assertAlmostEqual(bound.expected_belief_movement, 2 * 0.5 * 0.5 * 1.0)

    def test_lipschitz_factor_two(self) -> None:
        p1 = {"0": 0.8, "1": 0.2}
        p2 = {"0": 0.3, "1": 0.7}
        scalar = voi_bound_binary(
            0.4,
            p1,
            p2,
            conventions=MeasureConventions(lipschitz_norm=LipschitzNorm.SCALAR_BINARY, lipschitz_constant=1.0),
        )
        vector = voi_bound_binary(
            0.4,
            p1,
            p2,
            conventions=MeasureConventions(lipschitz_norm=LipschitzNorm.BELIEF_L1, lipschitz_constant=1.0),
        )
        self.assertAlmostEqual(vector.voi_bound_tv, 2.0 * scalar.voi_bound_tv)

    def test_property_identity_random_kernels(self) -> None:
        rng = random.Random(0)
        for _ in range(40):
            p1 = normalize_mass({"0": rng.random(), "1": rng.random(), "2": rng.random()})
            p2 = normalize_mass({"0": rng.random(), "1": rng.random(), "2": rng.random()})
            b = rng.random()
            bound = voi_bound_binary(b, p1, p2)
            self.assertTrue(bound.identity_holds)
            self.assertAlmostEqual(bound.prior_dispersion, prior_dispersion_binary(b))

    def test_general_bound_nonnegative(self) -> None:
        kernels = {
            "h1": {"x": 1.0, "y": 0.0},
            "h2": {"x": 0.0, "y": 1.0},
            "h3": {"x": 0.5, "y": 0.5},
        }
        weights = {"h1": 0.2, "h2": 0.3, "h3": 0.5}
        general = voi_bound_general(kernels, weights)
        self.assertGreater(general.voi_bound_general, 0.0)
        self.assertAlmostEqual(general.recoverability_jsd, general.conditional_mutual_information)


class InformationLossTests(unittest.TestCase):
    def test_markov_degradation_nonnegative(self) -> None:
        joint_clean = {("0", "0"): 50.0, ("1", "1"): 50.0}
        joint_obs = {("0", "0"): 40.0, ("0", "1"): 10.0, ("1", "1"): 40.0, ("1", "0"): 10.0}
        result = information_difference(
            joint_clean,
            joint_obs,
            degradation_markov=True,
            degradation_process_id="bsc",
        )
        self.assertGreaterEqual(result.information_difference, -1e-12)
        self.assertIsNotNone(result.information_loss_estimate)

    def test_side_information_negative_difference(self) -> None:
        joint_clean = {("0", "a"): 25.0, ("0", "b"): 25.0, ("1", "a"): 25.0, ("1", "b"): 25.0}
        joint_obs = {("0", "0"): 50.0, ("1", "1"): 50.0}
        result = information_difference(
            joint_clean,
            joint_obs,
            degradation_markov=False,
            degradation_process_id="side_channel",
        )
        self.assertLess(result.information_difference, 0.0)
        self.assertIsNone(result.information_loss_estimate)
        self.assertFalse(result.information_loss_is_exact)

    def test_surprisal_is_not_a_distance(self) -> None:
        self.assertGreater(surprisal(0.1), surprisal(0.9))


class RecoverabilityTests(unittest.TestCase):
    def test_estimators_agree_on_identical_kernels(self) -> None:
        kernels = {"h1": {"x": 0.5, "y": 0.5}, "h2": {"x": 0.5, "y": 0.5}}
        belief = {"h1": 0.4, "h2": 0.6}
        for name, estimator in ESTIMATORS.items():
            result = estimator.estimate(belief, ("h1", "h2"), "EXPLORE", kernels)
            if math.isfinite(result.score):
                self.assertAlmostEqual(result.score, 0.0, places=10, msg=name)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
