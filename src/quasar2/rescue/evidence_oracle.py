"""Evidence Oracle: gold mapping isolated from deployment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from quasar2.models.hypothesis import Hypothesis
from quasar2.retrieval.base import Document
from quasar2.signals.extractor import tokenize


CAUSAL_ORDER = (
    "OPEN_SET",
    "MISSING_EVIDENCE",
    "HYPOTHESIS_FAILURE",
    "RETRIEVAL_FAILURE",
    "DISCRIMINATION_FAILURE",
    "BELIEF_UPDATE_FAILURE",
    "DECISION_FAILURE",
    "NON_MONOTONIC_INTERACTION",
    "INDETERMINATE",
)


@dataclass(frozen=True, slots=True)
class EvidenceOracleRecord:
    query_id: str
    intent_id: str
    regime: str
    correct_hypothesis: str
    generated_hypothesis_ids: tuple[str, ...]
    evidence_doc_ids: tuple[str, ...]
    sufficient: str
    justification: str
    gold_source: str
    corpus_version: str
    required_intervention: str
    attribution_confidence: str
    review_needed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "query_id": self.query_id,
            "intent_id": self.intent_id,
            "regime": self.regime,
            "correct_hypothesis": self.correct_hypothesis,
            "generated_hypothesis_ids": list(self.generated_hypothesis_ids),
            "evidence_doc_ids": list(self.evidence_doc_ids),
            "sufficient": self.sufficient,
            "justification": self.justification,
            "gold_source": self.gold_source,
            "corpus_version": self.corpus_version,
            "required_intervention": self.required_intervention,
            "attribution_confidence": self.attribution_confidence,
            "review_needed": self.review_needed,
        }


def gold_documents_for(
    documents: Sequence[Document], hypothesis_id: str
) -> tuple[Document, ...]:
    return tuple(doc for doc in documents if hypothesis_id in doc.hypothesis_ids)


def is_discriminative_document(document: Document, hypothesis_id: str) -> bool:
    kind = str(document.metadata.get("kind", "")).lower()
    if kind in {"discriminative", "disc", "diagnostic"}:
        return hypothesis_id in document.hypothesis_ids
    tags = {token.lower() for token in document.tags}
    return "discriminative" in tags and hypothesis_id in document.hypothesis_ids


def sufficient_evidence(
    documents: Sequence[Document],
    hypothesis: Hypothesis,
    competitors: Sequence[Hypothesis],
) -> tuple[str, tuple[str, ...], str]:
    """Return (true|false|undetermined, gold doc ids, justification).

    Sufficient means at least one gold document tagged to H* that either is a
    discriminative item or contains unique discriminator tokens vs competitors.
    """

    gold = gold_documents_for(documents, hypothesis.hypothesis_id)
    if not gold:
        return "false", (), "no corpus document lists H* in hypothesis_ids"
    competitor_tokens: set[str] = set()
    for other in competitors:
        if other.hypothesis_id == hypothesis.hypothesis_id:
            continue
        competitor_tokens.update(tokenize(" ".join(other.discriminators + other.anchors)))
    unique = tuple(
        token
        for token in tokenize(" ".join(hypothesis.discriminators))
        if token not in competitor_tokens
    )
    sufficient_ids: list[str] = []
    for document in gold:
        if is_discriminative_document(document, hypothesis.hypothesis_id):
            sufficient_ids.append(document.document_id)
            continue
        text_tokens = set(tokenize(document.searchable_text))
        if unique and any(token in text_tokens for token in unique):
            sufficient_ids.append(document.document_id)
    if sufficient_ids:
        return (
            "true",
            tuple(dict.fromkeys(sufficient_ids)),
            "gold mapping lists H* and at least one document carries unique/discriminative evidence",
        )
    if gold:
        return (
            "true",
            tuple(doc.document_id for doc in gold),
            "gold mapping lists H*; core documents exist but unique discriminator overlap is weak (counted as supporting, not strongly discriminative)",
        )
    return "undetermined", (), "unverifiable"


def evaluate_case(
    *,
    query_id: str,
    intent_id: str,
    regime: str,
    correct_hypothesis: Hypothesis | None,
    catalog_ids: set[str],
    documents: Sequence[Document],
    generated_ids: Sequence[str],
    competitors: Sequence[Hypothesis],
    corpus_version: str,
) -> EvidenceOracleRecord:
    if correct_hypothesis is None or correct_hypothesis.hypothesis_id not in catalog_ids:
        return EvidenceOracleRecord(
            query_id=query_id,
            intent_id=intent_id,
            regime=regime,
            correct_hypothesis="" if correct_hypothesis is None else correct_hypothesis.hypothesis_id,
            generated_hypothesis_ids=tuple(generated_ids),
            evidence_doc_ids=(),
            sufficient="false",
            justification="H* is absent from the catalog (open set)",
            gold_source="intent.correct_hypothesis",
            corpus_version=corpus_version,
            required_intervention="OPEN_SET",
            attribution_confidence="high",
            review_needed=False,
        )
    flag, doc_ids, justification = sufficient_evidence(
        documents, correct_hypothesis, competitors
    )
    required = "NONE" if flag == "true" else "MISSING_EVIDENCE"
    return EvidenceOracleRecord(
        query_id=query_id,
        intent_id=intent_id,
        regime=regime,
        correct_hypothesis=correct_hypothesis.hypothesis_id,
        generated_hypothesis_ids=tuple(generated_ids),
        evidence_doc_ids=doc_ids,
        sufficient=flag,
        justification=justification,
        gold_source="document.hypothesis_ids + metadata.kind|tags",
        corpus_version=corpus_version,
        required_intervention=required,
        attribution_confidence="high" if flag != "undetermined" else "low",
        review_needed=flag == "undetermined",
    )
