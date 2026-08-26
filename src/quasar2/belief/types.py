"""Ideal posterior vs computational belief. Production code must not require b*."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from quasar2.math.divergences import entropy, kl_divergence
from quasar2.math.numerical import normalize_mass
from quasar2.models.belief import BeliefState


@dataclass(frozen=True, slots=True)
class EstimatedBelief:
    """Computational belief hat b_t = B(z_t) used by the live system."""

    probabilities: Mapping[str, float]
    source: str = "computational"
    round_index: int = -1

    def __post_init__(self) -> None:
        normalized = normalize_mass(self.probabilities)
        object.__setattr__(self, "probabilities", MappingProxyType(normalized))

    @classmethod
    def from_belief_state(cls, state: BeliefState) -> "EstimatedBelief":
        return cls(dict(state.probabilities), source="belief_state", round_index=state.round_index)


@dataclass(frozen=True, slots=True)
class IdealBelief:
    """Ideal posterior b*_t = P(I | h_t). Oracle/synthetic only."""

    probabilities: Mapping[str, float]
    available: bool = True
    source: str = "oracle"

    def __post_init__(self) -> None:
        normalized = normalize_mass(self.probabilities)
        object.__setattr__(self, "probabilities", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class BeliefDiagnostics:
    inference_error_kl: float | None
    belief_entropy: float
    belief_top1: str
    belief_top1_mass: float
    belief_top2: str | None
    belief_top2_mass: float | None
    belief_margin: float
    belief_calibration: float | None
    prior_dispersion: float


@dataclass(frozen=True, slots=True)
class BeliefSnapshot:
    estimated: EstimatedBelief
    ideal: IdealBelief | None
    diagnostics: BeliefDiagnostics


def diagnose(
    estimated: EstimatedBelief,
    ideal: IdealBelief | None = None,
    *,
    binary_focus_id: str | None = None,
    smooth: float = 0.0,
) -> BeliefDiagnostics:
    probs = dict(estimated.probabilities)
    ordered = sorted(probs.items(), key=lambda item: (-item[1], item[0]))
    top1, top1_mass = ordered[0]
    top2 = ordered[1][0] if len(ordered) > 1 else None
    top2_mass = ordered[1][1] if len(ordered) > 1 else None
    margin = top1_mass - (top2_mass or 0.0)
    if binary_focus_id is not None:
        mass = probs.get(binary_focus_id, 0.0)
        dispersion = mass * (1.0 - mass)
    else:
        dispersion = top1_mass * (1.0 - top1_mass)
    inference_error = None
    calibration = None
    if ideal is not None and ideal.available:
        inference_error = kl_divergence(dict(estimated.probabilities), dict(ideal.probabilities), smooth=smooth)
        calibration = kl_divergence(dict(ideal.probabilities), dict(estimated.probabilities), smooth=smooth)
    return BeliefDiagnostics(
        inference_error_kl=inference_error,
        belief_entropy=entropy(probs),
        belief_top1=top1,
        belief_top1_mass=top1_mass,
        belief_top2=top2,
        belief_top2_mass=top2_mass,
        belief_margin=margin,
        belief_calibration=calibration,
        prior_dispersion=dispersion,
    )
