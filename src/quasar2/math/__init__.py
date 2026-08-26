"""V2 mathematical primitives. Legacy pipeline entropy/TV calculations are unchanged."""

from quasar2.math.bellman import TabularMDP, bellman_backup, exact_error_bound, residual_error_bound
from quasar2.math.conventions import LipschitzNorm, MeasureConventions
from quasar2.math.divergences import (
    entropy,
    kl_divergence,
    prior_dispersion_binary,
    total_variation,
    weighted_jsd,
)
from quasar2.math.information import information_difference, surprisal
from quasar2.math.voi import voi_bound_binary, voi_bound_general, empirical_binary_voi_zero_one

__all__ = [
    "LipschitzNorm",
    "MeasureConventions",
    "TabularMDP",
    "bellman_backup",
    "entropy",
    "exact_error_bound",
    "information_difference",
    "kl_divergence",
    "prior_dispersion_binary",
    "residual_error_bound",
    "surprisal",
    "total_variation",
    "voi_bound_binary",
    "voi_bound_general",
    "empirical_binary_voi_zero_one",
    "weighted_jsd",
]
