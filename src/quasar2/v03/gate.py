"""Train-only R* estimation; development threshold and calibration roles are explicit."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Sequence

from quasar2.v03.contracts import Case, IntegrityError, RuntimeState
from quasar2.v03.registry import digest
from quasar2.v03.utility import Utility

FEATURE_SETS = {
    "full": (
        "entropy",
        "margin",
        "confidence",
        "recoverability",
        "decision_relevance",
        "estimated_cost",
        "novelty",
        "unknown_mass",
    ),
    "no_uncertainty": (
        "recoverability",
        "decision_relevance",
        "estimated_cost",
        "novelty",
        "unknown_mass",
    ),
    "no_recoverability": (
        "entropy",
        "margin",
        "confidence",
        "decision_relevance",
        "estimated_cost",
        "novelty",
        "unknown_mass",
    ),
    "no_relevance": (
        "entropy",
        "margin",
        "confidence",
        "recoverability",
        "estimated_cost",
        "novelty",
        "unknown_mass",
    ),
    "no_cost": (
        "entropy",
        "margin",
        "confidence",
        "recoverability",
        "decision_relevance",
        "novelty",
        "unknown_mass",
    ),
    "no_novelty": (
        "entropy",
        "margin",
        "confidence",
        "recoverability",
        "decision_relevance",
        "estimated_cost",
        "unknown_mass",
    ),
    "no_open_set": (
        "entropy",
        "margin",
        "confidence",
        "recoverability",
        "decision_relevance",
        "estimated_cost",
        "novelty",
    ),
    "cost_only": ("estimated_cost",),
    "uncertainty_recoverability": ("entropy", "recoverability"),
    "uncertainty_recoverability_cost": ("entropy", "recoverability", "estimated_cost"),
}


def sigmoid(value):
    value = max(-35, min(35, value))
    return 1 / (1 + math.exp(-value))


def require_split(cases, split):
    if not cases or any(case.split != split for case in cases):
        raise IntegrityError(f"This operation requires a nonempty {split}-only partition")


@dataclass
class RStarEstimator:
    feature_set: str = "full"
    steps: int = 250
    weights: list[float] = field(default_factory=list)
    means: list[float] = field(default_factory=list)
    scales: list[float] = field(default_factory=list)
    threshold: float = 0.5
    temperature: float = 1.0
    training_ids: tuple[str, ...] = ()
    development_ids: tuple[str, ...] = ()
    calibration_ids: tuple[str, ...] = ()
    training_domains: tuple[str, ...] = ()

    def fit(self, cases: Sequence[Case], utility: Utility):
        require_split(cases, "train")
        if self.feature_set not in FEATURE_SETS:
            raise IntegrityError("Unknown feature set")
        if isinstance(self.steps, bool) or not isinstance(self.steps, int) or self.steps < 1:
            raise IntegrityError("Training steps must be a positive integer")
        self.threshold, self.temperature = 0.5, 1.0
        self.development_ids = self.calibration_ids = ()
        names = FEATURE_SETS[self.feature_set]
        raw = [[case.state.features[name] for name in names] for case in cases]
        self.means = [sum(row[j] for row in raw) / len(raw) for j in range(len(names))]
        self.scales = [
            max(1e-6, math.sqrt(sum((row[j] - self.means[j]) ** 2 for row in raw) / len(raw)))
            for j in range(len(names))
        ]
        xs = [[1.0] + [(v - m) / s for v, m, s in zip(row, self.means, self.scales)] for row in raw]
        labels = [int(utility.delta(case.stop, case.additional) > 0) for case in cases]
        self.weights = [0.0] * (len(names) + 1)
        for _ in range(self.steps):
            residuals = [
                sigmoid(sum(w * v for w, v in zip(self.weights, row))) - label
                for row, label in zip(xs, labels)
            ]
            gradients = [
                sum(error * row[j] for error, row in zip(residuals, xs)) / len(xs)
                for j in range(len(self.weights))
            ]
            self.weights = [
                w - 0.1 * (grad + (0.01 * w if j else 0))
                for j, (w, grad) in enumerate(zip(self.weights, gradients))
            ]
        self.training_ids = tuple(case.query_id for case in cases)
        self.training_domains = tuple(sorted({case.domain for case in cases}))
        return self

    def raw(self, state: RuntimeState):
        if not self.weights:
            raise IntegrityError("Estimator is not fitted")
        row = [1.0] + [
            (state.features[name] - mean) / scale
            for name, mean, scale in zip(FEATURE_SETS[self.feature_set], self.means, self.scales)
        ]
        return sum(w * v for w, v in zip(self.weights, row))

    def probability(self, state: RuntimeState):
        return sigmoid(self.raw(state) / self.temperature)

    def calibrate(self, cases, utility):
        require_split(cases, "calibration")
        labels = [int(utility.delta(c.stop, c.additional) > 0) for c in cases]
        self.temperature = min(
            (0.5, 1.0, 2.0, 4.0),
            key=lambda t: sum(
                (sigmoid(self.raw(c.state) / t) - y) ** 2 for c, y in zip(cases, labels)
            ),
        )
        self.calibration_ids = tuple(c.query_id for c in cases)
        return self

    def tune(self, cases, utility, thresholds=(0, 0.25, 0.5, 0.75, 1.01)):
        require_split(cases, "development")
        self.threshold = max(
            thresholds,
            key=lambda t: (
                sum(
                    utility.delta(c.stop, c.additional)
                    for c in cases
                    if self.probability(c.state) >= t
                ),
                t,
            ),
        )
        self.development_ids = tuple(c.query_id for c in cases)
        return self

    def selected(self, state):
        return self.probability(state) >= self.threshold

    def to_dict(self):
        from dataclasses import asdict

        payload = asdict(self)
        payload["schema_version"] = "v03.1"
        payload["model_hash"] = digest(payload)
        return payload

    @classmethod
    def from_dict(cls, payload):
        value = dict(payload)
        expected = value.pop("model_hash")
        if digest(value) != expected:
            raise IntegrityError("Model hash mismatch")
        if value.pop("schema_version") != "v03.1":
            raise IntegrityError("Model schema mismatch")
        model = cls(**value)
        if (
            model.feature_set not in FEATURE_SETS
            or len(model.weights) != len(FEATURE_SETS[model.feature_set]) + 1
        ):
            raise IntegrityError("Invalid model shape")
        if (
            len(model.means) != len(model.scales)
            or len(model.means) + 1 != len(model.weights)
            or any(s <= 0 for s in model.scales)
        ):
            raise IntegrityError("Invalid model normalization")
        if (
            any(
                not math.isfinite(v)
                for v in [
                    *model.weights,
                    *model.means,
                    *model.scales,
                    model.temperature,
                    model.threshold,
                ]
            )
            or model.temperature <= 0
        ):
            raise IntegrityError("Invalid model numeric fields")
        return model


def simple_score(state, name):
    f = state.features
    if name == "confidence":
        return 1 - f["confidence"]
    if name == "margin":
        return 1 - f["margin"]
    if name == "uncertainty_recoverability":
        return (f["entropy"] + f["recoverability"]) / 2
    return f[name]


def tune_simple(cases, utility, name):
    require_split(cases, "development")
    return max(
        (0, 0.25, 0.5, 0.75, 1.01),
        key=lambda t: (
            sum(
                utility.delta(c.stop, c.additional)
                for c in cases
                if simple_score(c.state, name) >= t
            ),
            t,
        ),
    )


@dataclass
class Stump:
    feature: str = "entropy"
    cut: float = 0.5
    low: float = 0.5
    high: float = 0.5

    def fit(self, cases, utility):
        require_split(cases, "train")
        labels = [int(utility.delta(c.stop, c.additional) > 0) for c in cases]
        best = None
        for feature in FEATURE_SETS["full"]:
            for cut in (0.25, 0.5, 0.75):
                buckets = [
                    [y for c, y in zip(cases, labels) if (c.state.features[feature] >= cut) == side]
                    for side in (False, True)
                ]
                probs = [(sum(bucket) + 1) / (len(bucket) + 2) for bucket in buckets]
                loss = sum(
                    (probs[int(c.state.features[feature] >= cut)] - y) ** 2
                    for c, y in zip(cases, labels)
                )
                if best is None or loss < best[0]:
                    best = (loss, feature, cut, *probs)
        _, self.feature, self.cut, self.low, self.high = best
        return self

    def probability(self, state):
        return self.high if state.features[self.feature] >= self.cut else self.low
