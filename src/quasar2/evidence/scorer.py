"""Score how well retrieved documents support each explicit hypothesis."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Collection, Mapping, Sequence

from quasar2.models.evidence import EvidenceBundle, EvidenceItem
from quasar2.models.hypothesis import HypothesisCandidate
from quasar2.models.observation import Observation
from quasar2.retrieval.base import SearchHit
from quasar2.signals.extractor import tokenize


@dataclass(frozen=True, slots=True)
class EvidenceWeights:
    retrieval: float = 0.25
    observation: float = 0.40
    anchor: float = 0.20
    discriminator: float = 0.15
    foreign_penalty: float = 0.20


class EvidenceScorer:
    """Transparent feature-based scorer used for mechanism testing.

    Labels attached to corpus documents are used only for the foreign-document
    penalty and benchmark relevance.  They are never used to pick the correct
    hypothesis.  To remove even this weak supervision, set the penalty to zero.
    """

    def __init__(self, config: Mapping[str, float] | None = None) -> None:
        values = config or {}
        self.weights = EvidenceWeights(
            retrieval=float(values.get("retrieval_weight", 0.25)),
            observation=float(values.get("observation_weight", 0.40)),
            anchor=float(values.get("anchor_weight", 0.20)),
            discriminator=float(values.get("discriminator_weight", 0.15)),
            foreign_penalty=float(values.get("foreign_hypothesis_penalty", 0.20)),
        )

    @staticmethod
    def _coverage(needles: Collection[str], haystack: set[str]) -> float:
        vocabulary = set(needles)
        return len(vocabulary & haystack) / max(1, len(vocabulary))

    def score(
        self,
        observation: Observation,
        candidate: HypothesisCandidate,
        hits: Sequence[SearchHit],
        *,
        round_index: int,
        seen_pairs: Collection[tuple[str, str]] = (),
        query: str,
    ) -> EvidenceBundle:
        hypothesis = candidate.hypothesis
        seen = set(seen_pairs)
        anchor_tokens = tokenize(" ".join(hypothesis.anchors))
        discriminator_tokens = tokenize(" ".join(hypothesis.discriminators))
        items: list[EvidenceItem] = []
        for hit in hits:
            pair = (hypothesis.hypothesis_id, hit.document.document_id)
            if pair in seen:
                continue
            document_tokens = set(tokenize(hit.document.searchable_text))
            observation_coverage = self._coverage(observation.tokens, document_tokens)
            anchor_coverage = self._coverage(anchor_tokens, document_tokens)
            discriminator_coverage = self._coverage(discriminator_tokens, document_tokens)
            foreign = bool(hit.document.hypothesis_ids) and (
                hypothesis.hypothesis_id not in hit.document.hypothesis_ids
            )
            support = (
                self.weights.retrieval * max(0.0, min(1.0, hit.score))
                + self.weights.observation * observation_coverage
                + self.weights.anchor * anchor_coverage
                + self.weights.discriminator * discriminator_coverage
                - self.weights.foreign_penalty * float(foreign)
            )
            support = max(0.0, min(1.0, support))
            evidence_id = hashlib.sha1(
                f"{hypothesis.hypothesis_id}\0{hit.document.document_id}".encode("utf-8")
            ).hexdigest()[:16]
            snippet = hit.document.text[:280].rsplit(" ", 1)[0]
            items.append(
                EvidenceItem(
                    evidence_id=evidence_id,
                    hypothesis_id=hypothesis.hypothesis_id,
                    document_id=hit.document.document_id,
                    title=hit.document.title,
                    snippet=snippet,
                    retrieval_score=hit.score,
                    observation_coverage=observation_coverage,
                    anchor_coverage=anchor_coverage,
                    discriminator_coverage=discriminator_coverage,
                    foreign_hypothesis=foreign,
                    support_score=support,
                    retrieval_rank=hit.rank,
                    round_index=round_index,
                    query=query,
                )
            )
        ranked = sorted(items, key=lambda item: (-item.support_score, item.document_id))
        top = ranked[:3]
        aggregate = 0.0
        if top:
            aggregate = 0.70 * top[0].support_score + 0.30 * (
                sum(item.support_score for item in top) / len(top)
            )
        return EvidenceBundle(
            hypothesis_id=hypothesis.hypothesis_id,
            items=tuple(ranked),
            aggregate_support=aggregate,
            novel_item_count=len(ranked),
        )

