"""Discriminative belief update used only on the rescue experimental path."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from quasar2.belief.updater import BeliefUpdater
from quasar2.models.belief import BeliefState
from quasar2.models.evidence import EvidenceBundle
from quasar2.models.hypothesis import HypothesisCandidate


class DiscriminativeBeliefUpdater(BeliefUpdater):
    """Log-odds update with document-id dedup and signed support.

    This does not replace the frozen v0.1.1 BeliefUpdater used by QuasarPipeline.
    Absence of novel evidence is a no-op. Symmetric evidence does not invent a
    preference. Duplicate document ids are not treated as independent.
    """

    def update(
        self,
        previous: BeliefState,
        evidence: Sequence[EvidenceBundle],
        *,
        round_index: int,
    ) -> BeliefState:
        seen: set[tuple[str, str]] = set()
        signed: dict[str, list[float]] = {key: [] for key in previous.logits}
        for bundle in evidence:
            for item in bundle.items:
                key = (item.hypothesis_id, item.document_id)
                if key in seen:
                    continue
                seen.add(key)
                if item.hypothesis_id in signed:
                    weight = item.support_score
                    if item.foreign_hypothesis:
                        weight = -abs(weight)
                    signed[item.hypothesis_id].append(weight)
        informative = {hid: values for hid, values in signed.items() if values}
        if not informative:
            return self._state(dict(previous.logits), round_index=round_index)
        means = {
            hid: (sum(values) / len(values) if values else 0.0) for hid, values in signed.items()
        }
        center = sum(means.values()) / len(means)
        logits = dict(previous.logits)
        for hypothesis_id, mean in means.items():
            relative = mean - center
            n_items = len(signed.get(hypothesis_id) or ())
            if n_items == 0 and abs(relative) < 1e-12:
                continue
            novelty_scale = min(1.0, 0.55 + 0.15 * max(1, n_items))
            logits[hypothesis_id] += self.evidence_strength * relative * novelty_scale
            if hypothesis_id == "H_unknown" and relative <= 0 and "H_unknown" in previous.logits:
                logits[hypothesis_id] = previous.logits[hypothesis_id]
        return self._state(logits, round_index=round_index)

    def from_ranking(
        self,
        candidates: Sequence[HypothesisCandidate],
        ordered_ids: Sequence[str],
        *,
        round_index: int,
        mass: float = 0.85,
    ) -> BeliefState:
        """Oracle-belief helper: inject a correct ranking without answering."""

        ids = [candidate.hypothesis.hypothesis_id for candidate in candidates]
        logits = {hid: math.log(self.probability_floor) for hid in ids}
        remaining = 1.0
        for index, hid in enumerate(ordered_ids):
            if hid not in logits:
                continue
            share = mass if index == 0 else (1.0 - mass) / max(1, len(ordered_ids) - 1)
            remaining -= share
            logits[hid] = math.log(max(self.probability_floor, share))
        return self._state(logits, round_index=round_index)


def odds(probabilities: Mapping[str, float], hypothesis_id: str) -> float:
    p = max(1e-12, min(1.0 - 1e-12, float(probabilities.get(hypothesis_id, 0.0))))
    return p / (1.0 - p)
