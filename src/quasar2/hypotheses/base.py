"""Stable protocol shared by catalog and dynamic generators."""

from __future__ import annotations

from typing import Protocol

from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.models.observation import Observation


class HypothesisGenerator(Protocol):
    def generate(
        self, observation: Observation, *, max_candidates: int
    ) -> tuple[HypothesisCandidate, ...]:
        """Return ranked, competing interpretations of an observation."""
        ...

