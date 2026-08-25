"""The observed query, treated as a noisy view of a latent intent."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    raw_query: str
    domain: str
    normalized_query: str
    tokens: tuple[str, ...]
    entities: tuple[str, ...] = ()
    bigrams: tuple[str, ...] = ()
    signal_quality: float = 0.0
    estimated_degradation: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.raw_query.strip():
            raise ValueError("Observation query cannot be empty")
        if not 0.0 <= self.signal_quality <= 1.0:
            raise ValueError("signal_quality must be in [0, 1]")
        if not 0.0 <= self.estimated_degradation <= 1.0:
            raise ValueError("estimated_degradation must be in [0, 1]")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

