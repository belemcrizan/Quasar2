"""Generative abstractions for latent intent, expression, and degradation.

These types do not replace Observation. They sit beside the legacy observation
model so experiments can declare a generative story without rewriting the loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class LatentIntent:
    intent_id: str
    domain: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class ExpressedIntent:
    intent_id: str
    expression: str
    parent_intent_id: str


@dataclass(frozen=True, slots=True)
class ObservedQuery:
    text: str
    expressed_intent_id: str | None = None
    latent_intent_id: str | None = None


@dataclass(frozen=True, slots=True)
class DegradationProfile:
    lexical_noise: float = 0.0
    semantic_loss: float = 0.0
    temporal_loss: float = 0.0
    geographic_loss: float = 0.0
    population_loss: float = 0.0
    ambiguity: float = 0.0
    corruption: float = 0.0
    extra: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def intensity(self) -> float:
        named = (
            self.lexical_noise,
            self.semantic_loss,
            self.temporal_loss,
            self.geographic_loss,
            self.population_loss,
            self.ambiguity,
            self.corruption,
        )
        values = [*named, *self.extra.values()]
        return max(0.0, min(1.0, sum(values) / max(1, len(values))))


class ObservationModel(Protocol):
    def likelihood(self, query: ObservedQuery, intent: LatentIntent, eta: DegradationProfile) -> float:
        ...

    def kernels(self, action: str) -> Mapping[str, Mapping[str, float]]:
        """Optional P(O | H, a) kernels keyed by hypothesis id then outcome id."""
        ...
