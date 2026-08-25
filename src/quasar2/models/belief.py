"""Normalized posterior-like belief state over current hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class BeliefState:
    probabilities: Mapping[str, float]
    logits: Mapping[str, float]
    entropy: float
    normalized_entropy: float
    top_hypothesis_id: str
    top_probability: float
    margin: float
    round_index: int

    def __post_init__(self) -> None:
        total = sum(self.probabilities.values())
        if self.probabilities and abs(total - 1.0) > 1e-6:
            raise ValueError(f"Belief probabilities must sum to 1, got {total}")
        object.__setattr__(self, "probabilities", MappingProxyType(dict(self.probabilities)))
        object.__setattr__(self, "logits", MappingProxyType(dict(self.logits)))

