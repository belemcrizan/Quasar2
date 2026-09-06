import math
import unittest

from quasar2.decision.conformal import split_conformal_set
from quasar2.math.bootstrap import (
    cluster_bootstrap_mean,
    cluster_bootstrap_mean_difference,
    cluster_bootstrap_stat,
)
from quasar2.math.information import mutual_information_from_joint
from quasar2.math.numerical import normalize_mass, within_tolerance
from quasar2.wdi.normalize import normalize_observation


class NumericalContracts(unittest.TestCase):
    def test_mass_rejects_invalid_values(self):
        for value in (-1, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_mass({"a": value, "b": 2})

    def test_mass_rejects_invalid_floor(self):
        for floor in (-1, float("nan"), float("inf")):
            with self.subTest(floor=floor), self.assertRaises(ValueError):
                normalize_mass({"a": 1}, floor=floor)

    def test_mass_normalizes_without_overflow(self):
        self.assertEqual(normalize_mass({"a": 1e308, "b": 1e308}), {"a": 0.5, "b": 0.5})

    def test_infinite_value_is_not_close_to_finite(self):
        self.assertFalse(within_tolerance(float("inf"), 1))
        self.assertTrue(within_tolerance(float("inf"), float("inf")))
        self.assertFalse(within_tolerance(float("nan"), float("nan")))

    def test_information_ignores_zero_mass_rows(self):
        self.assertAlmostEqual(mutual_information_from_joint({("a", "a"): 1, ("b", "b"): 0}), 0)
        with self.assertRaises(ValueError):
            mutual_information_from_joint({("a", "a"): 2, ("b", "b"): -1})

    def test_bootstrap_rejects_misaligned_samples(self):
        with self.assertRaises(ValueError):
            cluster_bootstrap_mean([1, 2, 3], ["a", "b"])
        with self.assertRaises(ValueError):
            cluster_bootstrap_mean_difference([1, 2], [1], ["a", "b"])

    def test_bootstrap_rejects_invalid_values_and_draw_counts(self):
        with self.assertRaises(ValueError):
            cluster_bootstrap_mean([float("nan")], ["a"])
        for count in (-1, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                cluster_bootstrap_mean([1], ["a"], samples=count)

    def test_bootstrap_never_reports_nonfinite_statistics(self):
        result = cluster_bootstrap_stat(lambda _: float("inf"), ["a"], samples=4, seed=0)
        self.assertIsNone(result["point"])
        self.assertIsNone(result["ci_high"])
        self.assertEqual(result["n_successful_draws"], 0)

    def test_cluster_resampling_and_paired_difference(self):
        result = cluster_bootstrap_mean_difference(
            [3, 4, 7], [1, 2, 5], ["a", "a", "b"], samples=50
        )
        for key in ("point", "ci_low", "ci_high"):
            self.assertAlmostEqual(result[key], 2)

    def test_wdi_nonfinite_and_boolean_values_are_malformed(self):
        for value in ("NaN", "Infinity", float("inf"), True, False, "broken"):
            with self.subTest(value=value):
                row = normalize_observation({"value": value})
                self.assertEqual(row["observation_status"], "MALFORMED_SOURCE_RECORD")
                self.assertIsNone(row["value_numeric"])
        self.assertEqual(normalize_observation({"value": 0})["observation_status"], "OBSERVED")


class ConformalCoverage(unittest.TestCase):
    def test_finite_sample_rank_uses_ceiling(self):
        result = split_conformal_set({"inside": 9, "outside": 10}, list(range(10)), alpha=0.1)
        self.assertEqual(result.members, ("inside",))
        self.assertEqual(result.nonconformity_score, 9)

    def test_insufficient_calibration_returns_full_set(self):
        result = split_conformal_set({"a": 100, "b": 200}, [0.1, 0.2], alpha=0.1)
        self.assertEqual(result.members, ("a", "b"))
        self.assertEqual(result.nonconformity_score, math.inf)

    def test_exchangeable_leave_one_out_coverage(self):
        # Each score is equally likely to be the test point under exchangeability.
        scores = list(range(11))
        covered = sum(
            bool(
                split_conformal_set(
                    {"test": value}, scores[:i] + scores[i + 1 :], alpha=0.1
                ).members
            )
            for i, value in enumerate(scores)
        )
        self.assertGreaterEqual(covered / len(scores), 0.9)

    def test_nonfinite_scores_rejected(self):
        for bad in (float("nan"), float("inf")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                split_conformal_set({"a": 0.5}, [bad])
