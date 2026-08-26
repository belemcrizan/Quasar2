"""Canonical units and Lipschitz/TV conventions for v2 theory metrics.

Legacy entropy in BeliefState remains natural-log nats and is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DivergenceUnits(str, Enum):
    NATS = "nats"
    BITS = "bits"


class LipschitzNorm(str, Enum):
    SCALAR_BINARY = "scalar_binary"
    BELIEF_L1 = "belief_l1"


class TVConvention(str, Enum):
    HALF_L1 = "half_l1"


DEFAULT_DIVERGENCE_UNITS = DivergenceUnits.NATS
DEFAULT_TV_CONVENTION = TVConvention.HALF_L1
DEFAULT_LIPSCHITZ_NORM = LipschitzNorm.SCALAR_BINARY


@dataclass(frozen=True, slots=True)
class MeasureConventions:
    divergence_units: DivergenceUnits = DEFAULT_DIVERGENCE_UNITS
    tv_convention: TVConvention = DEFAULT_TV_CONVENTION
    lipschitz_norm: LipschitzNorm = DEFAULT_LIPSCHITZ_NORM
    lipschitz_constant: float = 1.0
    log_base: float = 2.718281828459045  # e; bits use 2

    def to_dict(self) -> dict[str, str | float]:
        return {
            "divergence_units": self.divergence_units.value,
            "tv_convention": self.tv_convention.value,
            "lipschitz_norm": self.lipschitz_norm.value,
            "lipschitz_constant": self.lipschitz_constant,
        }
