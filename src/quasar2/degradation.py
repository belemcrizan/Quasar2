"""Controlled query-degradation generator for stress experiments."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Mapping

from quasar2.signals.extractor import tokenize


DEFAULT_SUBSTITUTIONS: Mapping[str, str] = {
    "brightness": "light",
    "stellar": "star",
    "periodic": "repeating",
    "retrieval": "search",
    "model": "system",
    "adversarial": "hostile",
    "galaxy": "object",
    "training": "learning",
    "evidence": "clue",
    "prediction": "guess",
}


@dataclass(frozen=True, slots=True)
class DegradedQuery:
    original: str
    query: str
    level: float
    seed: int
    removed_tokens: tuple[str, ...]
    substitutions: tuple[tuple[str, str], ...]
    distractors: tuple[str, ...]


class QueryDegrader:
    """Remove, substitute, and contaminate terms at a requested severity.

    The generator is deterministic for ``(query, level, seed)`` and always
    preserves at least two original tokens.  It does not use intent labels.
    """

    def __init__(
        self,
        substitutions: Mapping[str, str] | None = None,
        distractors: tuple[str, ...] = ("pipeline", "signal", "system", "random"),
    ) -> None:
        self.substitutions = dict(substitutions or DEFAULT_SUBSTITUTIONS)
        self.distractors = distractors

    def degrade(self, query: str, *, level: float, seed: int) -> DegradedQuery:
        if not 0.0 <= level <= 1.0:
            raise ValueError("level must be in [0, 1]")
        tokens = list(tokenize(query, remove_stopwords=False))
        if len(tokens) < 2:
            raise ValueError("query must contain at least two tokens")
        rng = random.Random(f"{seed}:{level:.4f}:{query}")
        substitution_records: list[tuple[str, str]] = []
        for index, token in enumerate(tokens):
            if token in self.substitutions and rng.random() < level * 0.55:
                replacement = self.substitutions[token]
                tokens[index] = replacement
                substitution_records.append((token, replacement))

        removable = list(range(len(tokens)))
        rng.shuffle(removable)
        remove_count = min(len(tokens) - 2, int(round(len(tokens) * level * 0.55)))
        remove_indices = set(removable[:remove_count])
        removed = tuple(token for index, token in enumerate(tokens) if index in remove_indices)
        kept = [token for index, token in enumerate(tokens) if index not in remove_indices]

        distractor_records: list[str] = []
        if level >= 0.5 and self.distractors:
            count = 1 if level < 0.85 else 2
            distractor_records = rng.sample(self.distractors, k=min(count, len(self.distractors)))
            for distractor in distractor_records:
                kept.insert(rng.randrange(len(kept) + 1), distractor)
        return DegradedQuery(
            original=query,
            query=" ".join(kept),
            level=level,
            seed=seed,
            removed_tokens=removed,
            substitutions=tuple(substitution_records),
            distractors=tuple(distractor_records),
        )

