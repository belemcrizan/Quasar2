"""Mode A: reproducible hypothesis generation from a frozen domain catalog."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping

from quasar2.models.hypothesis import Hypothesis, HypothesisCandidate
from quasar2.models.observation import Observation
from quasar2.signals.extractor import tokenize


@dataclass(frozen=True, slots=True)
class HypothesisCatalog:
    hypotheses_by_domain: Mapping[str, tuple[Hypothesis, ...]]

    @classmethod
    def from_directory(cls, directory: str | Path) -> "HypothesisCatalog":
        root = Path(directory)
        by_domain: dict[str, tuple[Hypothesis, ...]] = {}
        for path in sorted(root.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            records = raw.get("hypotheses", raw) if isinstance(raw, dict) else raw
            if not isinstance(records, list):
                raise ValueError(f"Catalog {path} must contain a list of hypotheses")
            hypotheses = tuple(
                Hypothesis(
                    hypothesis_id=str(item["id"]),
                    domain=str(item["domain"]),
                    label=str(item["label"]),
                    description=str(item["description"]),
                    anchors=tuple(item.get("anchors", ())),
                    discriminators=tuple(item.get("discriminators", ())),
                    aliases=tuple(item.get("aliases", ())),
                    prior=float(item.get("prior", 1.0)),
                )
                for item in records
            )
            if hypotheses:
                domain = hypotheses[0].domain
                if any(hypothesis.domain != domain for hypothesis in hypotheses):
                    raise ValueError(f"Catalog {path} mixes domains")
                by_domain[domain] = hypotheses
        if not by_domain:
            raise ValueError(f"No hypothesis catalogs found in {root}")
        return cls(by_domain)

    def for_domain(self, domain: str) -> tuple[Hypothesis, ...]:
        try:
            return self.hypotheses_by_domain[domain]
        except KeyError as error:
            known = ", ".join(sorted(self.hypotheses_by_domain))
            raise KeyError(f"Unknown domain {domain!r}; expected one of: {known}") from error

    def get(self, hypothesis_id: str) -> Hypothesis:
        for hypotheses in self.hypotheses_by_domain.values():
            for hypothesis in hypotheses:
                if hypothesis.hypothesis_id == hypothesis_id:
                    return hypothesis
        raise KeyError(hypothesis_id)

    def __iter__(self) -> Iterable[Hypothesis]:
        for domain in sorted(self.hypotheses_by_domain):
            yield from self.hypotheses_by_domain[domain]


class CatalogHypothesisGenerator:
    """Rank catalog entries using several weak lexical views.

    No ground-truth intent or corpus label is consulted.  The scorer combines
    query overlap with anchors, aliases, discriminators, labels, and description
    tokens; ties are stable by hypothesis id.
    """

    def __init__(self, catalog: HypothesisCatalog) -> None:
        self.catalog = catalog

    @staticmethod
    def _score(observation: Observation, hypothesis: Hypothesis) -> tuple[float, str]:
        observed = set(observation.tokens)
        label = set(tokenize(hypothesis.label))
        description = set(tokenize(hypothesis.description))
        anchors = set(tokenize(" ".join(hypothesis.anchors)))
        discriminators = set(tokenize(" ".join(hypothesis.discriminators)))
        aliases = set(tokenize(" ".join(hypothesis.aliases)))

        def coverage(vocabulary: set[str]) -> float:
            return len(observed & vocabulary) / max(1, len(observed))

        score = (
            0.26 * coverage(label)
            + 0.24 * coverage(anchors)
            + 0.20 * coverage(aliases)
            + 0.18 * coverage(discriminators)
            + 0.12 * coverage(description)
        )
        matched = sorted(observed & (label | anchors | aliases | discriminators | description))
        rationale = "matched: " + ", ".join(matched[:8]) if matched else "catalog prior only"
        # A tiny prior term makes empty/ambiguous-query ordering explicit and stable.
        return score + 1e-6 * hypothesis.prior, rationale

    def generate(
        self, observation: Observation, *, max_candidates: int
    ) -> tuple[HypothesisCandidate, ...]:
        if max_candidates < 1:
            raise ValueError("max_candidates must be at least 1")
        ranked = sorted(
            (
                (*self._score(observation, hypothesis), hypothesis)
                for hypothesis in self.catalog.for_domain(observation.domain)
            ),
            key=lambda item: (-item[0], item[2].hypothesis_id),
        )[:max_candidates]
        return tuple(
            HypothesisCandidate(
                hypothesis=hypothesis,
                generation_score=score,
                rank=index,
                rationale=rationale,
            )
            for index, (score, rationale, hypothesis) in enumerate(ranked, start=1)
        )

