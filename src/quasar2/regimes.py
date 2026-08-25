"""Factorial query-uncertainty regimes for the v0.2 evidence experiment.

Q = (A, L, P, U, D) with integer levels 0..3.  The full Cartesian product is
not required; ``sample_design`` returns a frozen, seed-stable subset.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Sequence

from quasar2.signals.extractor import tokenize


FACTORS = ("ambiguity", "lexical", "paraphrase", "underspecification", "distractor")


@dataclass(frozen=True, slots=True)
class RegimeCell:
    cell_id: str
    ambiguity: int
    lexical: int
    paraphrase: int
    underspecification: int
    distractor: int

    def __post_init__(self) -> None:
        for name in FACTORS:
            value = getattr(self, name)
            if value not in {0, 1, 2, 3}:
                raise ValueError(f"{name} level must be 0..3, got {value}")

    @property
    def severity(self) -> float:
        return (self.ambiguity + self.lexical + self.paraphrase + self.underspecification + self.distractor) / 15.0

    def as_dict(self) -> dict[str, int | str | float]:
        return {
            "cell_id": self.cell_id,
            "ambiguity": self.ambiguity,
            "lexical": self.lexical,
            "paraphrase": self.paraphrase,
            "underspecification": self.underspecification,
            "distractor": self.distractor,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class RegimeObservation:
    query: str
    cell: RegimeCell
    seed: int
    notes: tuple[str, ...]


DEFAULT_DESIGN: tuple[RegimeCell, ...] = (
    RegimeCell("clean", 0, 0, 0, 0, 0),
    RegimeCell("A3", 3, 0, 0, 0, 0),
    RegimeCell("L3", 0, 3, 0, 0, 0),
    RegimeCell("P3", 0, 0, 3, 0, 0),
    RegimeCell("U3", 0, 0, 0, 3, 0),
    RegimeCell("D3", 0, 0, 0, 0, 3),
    RegimeCell("mid_mix", 2, 1, 2, 1, 0),
    RegimeCell("hard_mix", 1, 2, 1, 2, 2),
    RegimeCell("severe", 3, 3, 2, 2, 3),
)


def sample_design(*, extra: Sequence[RegimeCell] = ()) -> tuple[RegimeCell, ...]:
    seen: dict[str, RegimeCell] = {cell.cell_id: cell for cell in DEFAULT_DESIGN}
    for cell in extra:
        seen[cell.cell_id] = cell
    return tuple(seen.values())


class FactorialDegrader:
    """Apply independent uncertainty factors without consulting intent labels."""

    def __init__(
        self,
        *,
        competitor_terms: Sequence[str] = (),
        distractors: Sequence[str] = ("yesterday", "mobile", "dashboard", "random"),
        paraphrases: Sequence[tuple[str, str]] = (
            ("started", "began"),
            ("failing", "breaking"),
            ("after", "following"),
            ("only", "just"),
            ("pods", "instances"),
            ("deploy", "release"),
        ),
    ) -> None:
        self.competitor_terms = tuple(competitor_terms)
        self.distractors = tuple(distractors)
        self.paraphrases = tuple(paraphrases)

    def apply(self, query: str, cell: RegimeCell, *, seed: int) -> RegimeObservation:
        rng = random.Random(f"{seed}:{cell.cell_id}:{query}")
        tokens = list(tokenize(query, remove_stopwords=False))
        notes: list[str] = []
        if cell.paraphrase:
            swapped = 0
            mapping = dict(self.paraphrases)
            for index, token in enumerate(tokens):
                if token in mapping and rng.random() < 0.25 * cell.paraphrase:
                    tokens[index] = mapping[token]
                    swapped += 1
            if cell.paraphrase >= 2 and len(tokens) > 3:
                left, right = 1, len(tokens) - 1
                tokens[left:right] = list(reversed(tokens[left:right]))
                notes.append("reversed_inner_span")
            notes.append(f"paraphrase_swaps={swapped}")
        if cell.lexical:
            mutated = 0
            for index, token in enumerate(tokens):
                if len(token) < 4 or rng.random() >= 0.18 * cell.lexical:
                    continue
                chars = list(token)
                position = rng.randrange(1, len(chars) - 1)
                chars[position] = rng.choice("aeiou")
                tokens[index] = "".join(chars)
                mutated += 1
            notes.append(f"lexical_mutations={mutated}")
        if cell.underspecification and len(tokens) > 3:
            drop = min(len(tokens) - 2, cell.underspecification + 1)
            indices = list(range(len(tokens)))
            rng.shuffle(indices)
            remove = set(indices[:drop])
            tokens = [token for index, token in enumerate(tokens) if index not in remove]
            notes.append(f"dropped={drop}")
        if cell.ambiguity and self.competitor_terms:
            count = min(len(self.competitor_terms), cell.ambiguity)
            injected = rng.sample(list(self.competitor_terms), k=count)
            for term in injected:
                tokens.insert(rng.randrange(len(tokens) + 1), term)
            notes.append("ambiguity=" + ",".join(injected))
        if cell.distractor and self.distractors:
            count = min(len(self.distractors), cell.distractor)
            injected = rng.sample(list(self.distractors), k=count)
            for term in injected:
                tokens.insert(rng.randrange(len(tokens) + 1), term)
            notes.append("distractors=" + ",".join(injected))
        if len(tokens) < 2:
            tokens = list(tokenize(query, remove_stopwords=False))[:2]
        return RegimeObservation(query=" ".join(tokens), cell=cell, seed=seed, notes=tuple(notes))


def competitor_terms_for(labels: Iterable[str], *, exclude: str, limit: int = 8) -> tuple[str, ...]:
    terms: list[str] = []
    for label in labels:
        if label == exclude:
            continue
        pieces = [piece for piece in label.replace("_", " ").replace(".", " ").split() if len(piece) > 3]
        terms.extend(pieces[:1])
        if len(terms) >= limit:
            break
    return tuple(terms[:limit])
