"""Hypotheses are explicit, inspectable candidate interpretations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Hypothesis:
    hypothesis_id: str
    domain: str
    label: str
    description: str
    anchors: tuple[str, ...]
    discriminators: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    prior: float = 1.0

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.label:
            raise ValueError("A hypothesis requires an id and label")
        if self.prior <= 0:
            raise ValueError("Hypothesis prior must be positive")

    @property
    def vocabulary(self) -> tuple[str, ...]:
        return self.anchors + self.discriminators + self.aliases


@dataclass(frozen=True, slots=True)
class HypothesisCandidate:
    hypothesis: Hypothesis
    generation_score: float
    rank: int
    rationale: str

