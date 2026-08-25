"""Numerically stable posterior-like update over candidate hypotheses."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from quasar2.models.belief import BeliefState
from quasar2.models.evidence import EvidenceBundle
from quasar2.models.hypothesis import HypothesisCandidate


class BeliefUpdater:
    def __init__(
        self,
        *,
        evidence_strength: float = 4.0,
        temperature: float = 1.0,
        probability_floor: float = 1e-6,
    ) -> None:
        if evidence_strength <= 0 or temperature <= 0 or probability_floor <= 0:
            raise ValueError("Belief parameters must be positive")
        self.evidence_strength = evidence_strength
        self.temperature = temperature
        self.probability_floor = probability_floor

    def initialize(self, candidates: Sequence[HypothesisCandidate]) -> BeliefState:
        if not candidates:
            raise ValueError("Cannot initialize belief without candidates")
        raw = {
            candidate.hypothesis.hypothesis_id: max(
                self.probability_floor,
                candidate.hypothesis.prior * max(candidate.generation_score, self.probability_floor),
            )
            for candidate in candidates
        }
        logits = {key: math.log(value) for key, value in raw.items()}
        return self._state(logits, round_index=-1)

    def update(
        self,
        previous: BeliefState,
        evidence: Sequence[EvidenceBundle],
        *,
        round_index: int,
    ) -> BeliefState:
        support = {bundle.hypothesis_id: bundle.aggregate_support for bundle in evidence}
        novel = {bundle.hypothesis_id: bundle.novel_item_count for bundle in evidence}
        informative = [value for key, value in support.items() if novel.get(key, 0) > 0]
        if not informative:
            return self._state(dict(previous.logits), round_index=round_index)
        center = sum(informative) / len(informative)
        logits = dict(previous.logits)
        for hypothesis_id in logits:
            if novel.get(hypothesis_id, 0) > 0:
                relative_support = support[hypothesis_id] - center
                novelty_scale = min(1.0, 0.55 + 0.15 * novel[hypothesis_id])
                logits[hypothesis_id] += self.evidence_strength * relative_support * novelty_scale
        return self._state(logits, round_index=round_index)

    def _state(self, logits: Mapping[str, float], *, round_index: int) -> BeliefState:
        maximum = max(logits.values())
        exponentials = {
            key: math.exp((value - maximum) / self.temperature) for key, value in logits.items()
        }
        denominator = sum(exponentials.values())
        probabilities = {key: value / denominator for key, value in exponentials.items()}
        ordered = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))
        entropy = -sum(value * math.log(max(value, self.probability_floor)) for value in probabilities.values())
        max_entropy = math.log(len(probabilities)) if len(probabilities) > 1 else 1.0
        return BeliefState(
            probabilities=probabilities,
            logits=dict(logits),
            entropy=entropy,
            normalized_entropy=entropy / max_entropy if len(probabilities) > 1 else 0.0,
            top_hypothesis_id=ordered[0][0],
            top_probability=ordered[0][1],
            margin=ordered[0][1] - ordered[1][1] if len(ordered) > 1 else 1.0,
            round_index=round_index,
        )

