"""Diagnostic policy-gap decomposition. Not claimed to be additive in general."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class PolicyGapDecomposition:
    """Oracle-controlled diagnostic. Components are exclusive scenario switches, not an identity.

    Regret ≈ R_hypothesis + R_retrieval + R_recoverability + R_inference + R_routing
    + R_stopping + R_open_set + R_cost_model + R_shift
    only under the experimental switches used to populate the fields.
    """

    total_regret: float
    r_hypothesis: float
    r_retrieval: float
    r_recoverability: float
    r_inference: float
    r_routing: float
    r_stopping: float
    r_open_set: float
    r_cost_model: float
    r_shift: float
    additive: bool
    residual: float
    notes: str

    def to_dict(self) -> dict[str, float | bool | str]:
        return asdict(self)


def decompose_from_scenarios(utilities: Mapping[str, float]) -> PolicyGapDecomposition:
    """Each key is a nested oracle-controlled scenario name.

    Required keys:
      oracle, no_hypotheses, no_retrieval, proxy_recoverability, degraded_inference,
      routing_only, forced_stop, open_set_blind, misspecified_cost, shifted
    """

    oracle = float(utilities["oracle"])
    def gap(name: str) -> float:
        return oracle - float(utilities[name])

    components = {
        "r_hypothesis": gap("no_hypotheses"),
        "r_retrieval": gap("no_retrieval"),
        "r_recoverability": gap("proxy_recoverability"),
        "r_inference": gap("degraded_inference"),
        "r_routing": gap("routing_only"),
        "r_stopping": gap("forced_stop"),
        "r_open_set": gap("open_set_blind"),
        "r_cost_model": gap("misspecified_cost"),
        "r_shift": gap("shifted"),
    }
    summed = sum(components.values())
    total = gap("evaluated")
    residual = total - summed
    return PolicyGapDecomposition(
        total_regret=total,
        additive=False,
        residual=residual,
        notes="Diagnostic nested gaps. Do not treat the sum as an accounting identity.",
        **components,
    )
