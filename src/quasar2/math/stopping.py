"""NetVoI UCB estimators and false-stop accounting (C6).

Normal, percentile bootstrap, and BCa are approximate. Empirical Bernstein
requires bounded observations. Bonferroni controls a single fixed stage with
m information actions; it does not automatically cover sequential looks.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence


class NetVoIConfidenceEstimator(Protocol):
    name: str

    def upper_bound(self, samples: Sequence[float], alpha: float, n_actions: int) -> float:
        ...


def _mean(samples: Sequence[float]) -> float:
    return sum(samples) / len(samples) if samples else 0.0


def _variance(samples: Sequence[float]) -> float:
    if len(samples) < 2:
        return 0.0
    mu = _mean(samples)
    return sum((value - mu) ** 2 for value in samples) / (len(samples) - 1)


class NormalUCB:
    name = "normal_ucb"

    def upper_bound(self, samples: Sequence[float], alpha: float, n_actions: int) -> float:
        if not samples:
            return math.inf
        per_action = alpha / max(1, n_actions)
        z = _normal_ppf(1.0 - per_action)
        se = math.sqrt(_variance(samples) / len(samples)) if len(samples) > 1 else 0.0
        return _mean(samples) + z * se


class EmpiricalBernsteinUCB:
    name = "empirical_bernstein_ucb"

    def __init__(self, bound_range: float = 1.0) -> None:
        if bound_range <= 0.0:
            raise ValueError("bound_range must be positive")
        self.bound_range = bound_range

    def upper_bound(self, samples: Sequence[float], alpha: float, n_actions: int) -> float:
        n = len(samples)
        if n == 0:
            return math.inf
        per_action = alpha / max(1, n_actions)
        log_term = math.log(3.0 / per_action)
        emp_var = _variance(samples)
        width = math.sqrt(2.0 * emp_var * log_term / n) + 3.0 * self.bound_range * log_term / n
        return _mean(samples) + width


class PercentileBootstrapUCB:
    name = "percentile_bootstrap_ucb"

    def __init__(self, n_bootstrap: int = 400, seed: int = 0) -> None:
        self.n_bootstrap = n_bootstrap
        self.seed = seed

    def upper_bound(self, samples: Sequence[float], alpha: float, n_actions: int) -> float:
        if not samples:
            return math.inf
        rng = random.Random(self.seed)
        per_action = alpha / max(1, n_actions)
        means = []
        n = len(samples)
        for _ in range(self.n_bootstrap):
            draw = [samples[rng.randrange(n)] for _ in range(n)]
            means.append(_mean(draw))
        means.sort()
        index = min(n - 1, max(0, int(math.ceil((1.0 - per_action) * len(means)) - 1)))
        return means[index]


class BCaBootstrapUCB:
    name = "bca_bootstrap_ucb"

    def __init__(self, n_bootstrap: int = 400, seed: int = 0) -> None:
        self.n_bootstrap = n_bootstrap
        self.seed = seed

    def upper_bound(self, samples: Sequence[float], alpha: float, n_actions: int) -> float:
        if len(samples) < 2:
            return PercentileBootstrapUCB(self.n_bootstrap, self.seed).upper_bound(
                samples, alpha, n_actions
            )
        rng = random.Random(self.seed)
        n = len(samples)
        theta = _mean(samples)
        boots = []
        for _ in range(self.n_bootstrap):
            draw = [samples[rng.randrange(n)] for _ in range(n)]
            boots.append(_mean(draw))
        boots.sort()
        proportion_less = sum(1 for value in boots if value < theta) / len(boots)
        z0 = _normal_ppf(min(1.0 - 1e-9, max(1e-9, proportion_less)))
        jack = []
        for i in range(n):
            leave = [samples[j] for j in range(n) if j != i]
            jack.append(_mean(leave))
        jack_mean = _mean(jack)
        num = sum((jack_mean - value) ** 3 for value in jack)
        den = sum((jack_mean - value) ** 2 for value in jack)
        accel = num / (6.0 * (den ** 1.5)) if den > 0.0 else 0.0
        per_action = alpha / max(1, n_actions)
        z_alpha = _normal_ppf(1.0 - per_action)
        adjusted = z0 + (z0 + z_alpha) / (1.0 - accel * (z0 + z_alpha))
        q = _normal_cdf(adjusted)
        index = min(len(boots) - 1, max(0, int(math.floor(q * len(boots)))))
        return boots[index]


class BootstrapUCB(PercentileBootstrapUCB):
    name = "bootstrap_ucb"


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _normal_ppf(p: float) -> float:
    """Acklam approximation of the standard-normal quantile."""

    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577509590705e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)


@dataclass(frozen=True, slots=True)
class StopDecision:
    stop_decision: bool
    stop_reason: str
    best_info_action: str | None
    best_net_voi: float
    best_net_voi_ucb: float
    alpha: float
    multiple_comparison_method: str
    coverage_scope: str
    look_index: int
    false_stop: bool | None
    near_zero: bool


def stop_if_all_ucb_nonpositive(
    ucbs: Mapping[str, float],
    estimates: Mapping[str, float],
    *,
    alpha: float,
    coverage_scope: str = "fixed_stage",
    look_index: int = 1,
    oracle_best_net_voi: float | None = None,
    delta_positive: float = 0.0,
    method: str = "bonferroni",
) -> StopDecision:
    if not ucbs:
        raise ValueError("ucbs must be non-empty")
    best_action = max(ucbs, key=lambda name: (ucbs[name], name))
    best_ucb = ucbs[best_action]
    stop = best_ucb <= 0.0
    false_stop = None
    near_zero = False
    if oracle_best_net_voi is not None:
        near_zero = abs(oracle_best_net_voi) <= delta_positive
        false_stop = bool(stop and oracle_best_net_voi > delta_positive)
    return StopDecision(
        stop_decision=stop,
        stop_reason="max_ucb_nonpositive" if stop else "positive_ucb_remains",
        best_info_action=best_action,
        best_net_voi=float(estimates.get(best_action, 0.0)),
        best_net_voi_ucb=best_ucb,
        alpha=alpha,
        multiple_comparison_method=method,
        coverage_scope=coverage_scope,
        look_index=look_index,
        false_stop=false_stop,
        near_zero=near_zero,
    )


def wilson_upper(successes: int, n: int, *, confidence: float = 0.95) -> float:
    if n <= 0:
        return 1.0
    z = _normal_ppf(1.0 - (1.0 - confidence) / 2.0)
    phat = successes / n
    denom = 1.0 + z * z / n
    center = phat + z * z / (2.0 * n)
    spread = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n)
    return min(1.0, (center + spread) / denom)


def wilson_lower(successes: int, n: int, *, confidence: float = 0.95) -> float:
    if n <= 0:
        return 0.0
    z = _normal_ppf(1.0 - (1.0 - confidence) / 2.0)
    phat = successes / n
    denom = 1.0 + z * z / n
    center = phat + z * z / (2.0 * n)
    spread = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n)
    return max(0.0, (center - spread) / denom)

