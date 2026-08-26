"""Typed recoverability and action-value objects. Unknown is explicit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from quasar2.cycle2 import UNCERTAINTY_UNKNOWN


@dataclass(frozen=True, slots=True)
class RecoverabilityEstimate:
    point_estimate: float
    uncertainty: float | None
    calibration: float | None
    misspecification_risk: float | None
    estimator_family: str
    provenance: str
    components: Mapping[str, float | None] = field(default_factory=dict)

    @property
    def r_hat(self) -> float:
        return self.point_estimate

    @property
    def sigma_r(self) -> float | None:
        return self.uncertainty

    @property
    def m_r(self) -> float | None:
        return self.misspecification_risk

    def to_dict(self) -> dict[str, object]:
        return {
            "R_hat": self.point_estimate,
            "sigma_R": self.uncertainty if self.uncertainty is not None else UNCERTAINTY_UNKNOWN,
            "M_R": self.misspecification_risk if self.misspecification_risk is not None else UNCERTAINTY_UNKNOWN,
            "calibration": self.calibration if self.calibration is not None else UNCERTAINTY_UNKNOWN,
            "estimator_family": self.estimator_family,
            "provenance": self.provenance,
            "components": dict(self.components),
        }


@dataclass(frozen=True, slots=True)
class ActionValueEstimate:
    action: str
    mean: float
    lower_bound: float | None
    upper_bound: float | None
    uncertainty: float | None
    cost: float
    risk: float
    provenance: str
    gross_gain: float
    action_cost: float
    risk_penalty: float
    t2_bound: float | None = None
    t2_is_not_q: bool = True

    @property
    def net_value(self) -> float:
        return self.gross_gain - self.action_cost - self.risk_penalty

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "mean": self.mean,
            "lower_bound": self.lower_bound if self.lower_bound is not None else UNCERTAINTY_UNKNOWN,
            "upper_bound": self.upper_bound if self.upper_bound is not None else UNCERTAINTY_UNKNOWN,
            "uncertainty": self.uncertainty if self.uncertainty is not None else UNCERTAINTY_UNKNOWN,
            "cost": self.cost,
            "risk": self.risk,
            "provenance": self.provenance,
            "gross_gain": self.gross_gain,
            "action_cost": self.action_cost,
            "risk_penalty": self.risk_penalty,
            "Q_net": self.net_value,
            "t2_bound": self.t2_bound,
            "t2_is_not_q": self.t2_is_not_q,
        }
