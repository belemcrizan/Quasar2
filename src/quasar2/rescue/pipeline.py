"""Experimental rescue loop. Does not replace QuasarPipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from quasar2.belief.updater import BeliefUpdater
from quasar2.decision.engine import DecisionEngine
from quasar2.evidence.scorer import EvidenceScorer
from quasar2.hypotheses.catalog import CatalogHypothesisGenerator
from quasar2.models.belief import BeliefState
from quasar2.models.decision import Action
from quasar2.models.evidence import EvidenceBundle, EvidenceItem
from quasar2.models.hypothesis import Hypothesis, HypothesisCandidate
from quasar2.models.observation import Observation
from quasar2.rescue.belief import DiscriminativeBeliefUpdater
from quasar2.rescue.leakage import LeakageError, assert_no_gold_fields
from quasar2.rescue.queries import build_discriminative_queries
from quasar2.rescue.scoring import rerank_hits
from quasar2.retrieval.base import Document, Retriever, SearchHit
from quasar2.signals.extractor import SignalExtractor

Arm = Literal[
    "fast",
    "relevance",
    "bm25",
    "dense",
    "hybrid",
    "hypothesis_conditioned",
    "pairwise_contrastive",
    "falsification",
    "contradiction",
    "eig_approx",
    "discriminative_rerank",
]


@dataclass(frozen=True, slots=True)
class RescueRun:
    predicted_id: str
    belief: BeliefState
    action: str
    evidence: tuple[EvidenceItem, ...]
    retrieved_ids: tuple[str, ...]
    candidates: tuple[HypothesisCandidate, ...]
    retrieval_calls: int
    seed_calls: int
    explore_rounds: int
    observation: Observation
    b_star_before: float | None
    b_star_after: float | None
    arm: str
    mode: str


class OracleHitInjector:
    """Diagnostic retriever: prepend gold documents. Not deployment-valid."""

    def __init__(self, inner: Retriever, gold_docs: Sequence[Document]) -> None:
        self.inner = inner
        self.gold_docs = tuple(gold_docs)

    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        gold_hits = tuple(
            SearchHit(document=doc, score=1.0 + 0.01 * index, rank=index + 1, components={"oracle": 1.0})
            for index, doc in enumerate(self.gold_docs)
        )
        rest = self.inner.search(query, top_k=top_k, domain=domain)
        merged: list[SearchHit] = list(gold_hits)
        seen = {hit.document.document_id for hit in merged}
        for hit in rest:
            if hit.document.document_id in seen:
                continue
            merged.append(hit)
            seen.add(hit.document.document_id)
            if len(merged) >= top_k:
                break
        return tuple(merged[:top_k])


def inject_hypothesis(
    generator: CatalogHypothesisGenerator,
    observation: Observation,
    *,
    max_candidates: int,
    gold: Hypothesis,
) -> tuple[HypothesisCandidate, ...]:
    generated = list(generator.generate(observation, max_candidates=max_candidates))
    if any(candidate.hypothesis.hypothesis_id == gold.hypothesis_id for candidate in generated):
        return tuple(generated)
    injected = HypothesisCandidate(
        hypothesis=gold,
        generation_score=1.0,
        rank=0,
        rationale="oracle_hypothesis_injection",
    )
    others = [candidate for candidate in generated if candidate.hypothesis.hypothesis_id != gold.hypothesis_id]
    return (injected, *others[: max(0, max_candidates - 1)])


class RescuePipeline:
    def __init__(
        self,
        *,
        extractor: SignalExtractor,
        generator: CatalogHypothesisGenerator,
        retriever: Retriever,
        bm25: Retriever,
        dense: Retriever,
        hybrid: Retriever,
        scorer: EvidenceScorer,
        legacy_updater: BeliefUpdater,
        disc_updater: DiscriminativeBeliefUpdater,
        decision: DecisionEngine,
        max_candidates: int = 4,
        initial_top_k: int = 1,
        top_k: int = 4,
        documents: Sequence[Document] = (),
    ) -> None:
        self.extractor = extractor
        self.generator = generator
        self.retriever = retriever
        self.bm25 = bm25
        self.dense = dense
        self.hybrid = hybrid
        self.scorer = scorer
        self.legacy_updater = legacy_updater
        self.disc_updater = disc_updater
        self.decision = decision
        self.max_candidates = max_candidates
        self.initial_top_k = initial_top_k
        self.top_k = top_k
        self.documents = tuple(documents)

    def _retriever_for(self, arm: str) -> Retriever:
        if arm in {"bm25"}:
            return self.bm25
        if arm in {"dense"}:
            return self.dense
        return self.hybrid if arm in {"hybrid", "relevance"} else self.retriever

    def _candidates(
        self,
        observation: Observation,
        *,
        mode: str,
        gold_hypothesis: Hypothesis | None,
    ) -> tuple[HypothesisCandidate, ...]:
        if mode == "oracle_hypothesis":
            if gold_hypothesis is None:
                raise LeakageError("oracle_hypothesis requires an explicit gold hypothesis")
            return inject_hypothesis(
                self.generator,
                observation,
                max_candidates=self.max_candidates,
                gold=gold_hypothesis,
            )
        generated = self.generator.generate(observation, max_candidates=self.max_candidates)
        return generated or generated[:1]

    def _score_round(
        self,
        observation: Observation,
        candidates: Sequence[HypothesisCandidate],
        hits_by_id: dict[str, tuple[SearchHit, ...]],
        *,
        round_index: int,
        seen_pairs: set[tuple[str, str]],
        query: str,
    ) -> list[EvidenceBundle]:
        bundles: list[EvidenceBundle] = []
        for candidate in candidates:
            hid = candidate.hypothesis.hypothesis_id
            hits = hits_by_id.get(hid, ())
            bundle = self.scorer.score(
                observation,
                candidate,
                hits,
                round_index=round_index,
                seen_pairs=seen_pairs,
                query=query,
            )
            bundles.append(bundle)
            for item in bundle.items:
                seen_pairs.add((item.hypothesis_id, item.document_id))
        return bundles

    def run(
        self,
        query: str,
        domain: str,
        *,
        arm: Arm = "fast",
        mode: str = "predicted_hypothesis",
        gold_hypothesis: Hypothesis | None = None,
        gold_docs: Sequence[Document] = (),
        oracle_belief: bool = False,
        oracle_evidence: bool = False,
        use_disc_updater: bool = True,
        metadata: dict[str, str] | None = None,
    ) -> RescueRun:
        if mode == "predicted_hypothesis":
            assert_no_gold_fields(metadata or {}, context="rescue.run metadata")
            if gold_hypothesis is not None or gold_docs or oracle_belief or oracle_evidence:
                raise LeakageError("predicted_hypothesis mode received oracle inputs")
        observation = self.extractor.extract(query, domain, metadata=metadata or {})
        candidates = self._candidates(observation, mode=mode, gold_hypothesis=gold_hypothesis)
        updater = self.disc_updater if use_disc_updater else self.legacy_updater
        belief = updater.initialize(candidates)
        b_star_before = (
            belief.probabilities.get(gold_hypothesis.hypothesis_id, 0.0) if gold_hypothesis else None
        )
        seen_pairs: set[tuple[str, str]] = set()
        seen_docs: set[str] = set()
        evidence_items: list[EvidenceItem] = []
        retrieved: list[str] = []
        retriever: Retriever = self.retriever
        if mode == "oracle_retrieval" and gold_docs:
            retriever = OracleHitInjector(self.retriever, gold_docs)
        seed_calls = 0
        hits_by_id: dict[str, tuple[SearchHit, ...]] = {}
        for candidate in candidates:
            hid = candidate.hypothesis.hypothesis_id
            seed_query = " ".join((observation.normalized_query, candidate.hypothesis.label))
            hits = retriever.search(seed_query, top_k=self.initial_top_k, domain=domain)
            hits_by_id[hid] = hits
            seed_calls += 1
            for hit in hits:
                retrieved.append(hit.document.document_id)
                seen_docs.add(hit.document.document_id)
        bundles = self._score_round(
            observation,
            candidates,
            hits_by_id,
            round_index=0,
            seen_pairs=seen_pairs,
            query=observation.normalized_query,
        )
        if oracle_evidence and gold_hypothesis is not None and gold_docs:
            bundles = _oracle_evidence_bundles(gold_hypothesis, gold_docs, candidates, round_index=0)
        for bundle in bundles:
            evidence_items.extend(bundle.items)
        belief = updater.update(belief, bundles, round_index=0)
        retrieval_calls = seed_calls
        explore_rounds = 0
        if arm != "fast":
            explore_rounds = 1
            extra_retriever = self._retriever_for(arm)
            if mode == "oracle_retrieval" and gold_docs:
                extra_retriever = OracleHitInjector(extra_retriever, gold_docs)
            queries = build_discriminative_queries(
                observation, candidates, belief, seen_document_ids=tuple(seen_docs)
            )
            selected_queries = _select_queries(arm, queries, observation)
            extra_hits: list[SearchHit] = []
            for text in selected_queries:
                extra_hits.extend(extra_retriever.search(text, top_k=self.top_k, domain=domain))
                retrieval_calls += 1
            ranked_ids = sorted(belief.probabilities, key=lambda key: (-belief.probabilities[key], key))
            by_id = {c.hypothesis.hypothesis_id: c.hypothesis for c in candidates}
            left = by_id.get(ranked_ids[0])
            right = by_id.get(ranked_ids[1]) if len(ranked_ids) > 1 else None
            if left is not None and arm in {
                "pairwise_contrastive",
                "discriminative_rerank",
                "eig_approx",
                "contradiction",
                "falsification",
                "hypothesis_conditioned",
            }:
                extra_hits = list(
                    rerank_hits(extra_hits, observation.normalized_query, left, right, seen_ids=tuple(seen_docs), top_k=self.top_k)
                )
            unique: dict[str, SearchHit] = {}
            for hit in extra_hits:
                unique.setdefault(hit.document.document_id, hit)
                seen_docs.add(hit.document.document_id)
                retrieved.append(hit.document.document_id)
            hits_by_id = {
                candidate.hypothesis.hypothesis_id: tuple(unique.values()) for candidate in candidates
            }
            bundles = self._score_round(
                observation,
                candidates,
                hits_by_id,
                round_index=1,
                seen_pairs=seen_pairs,
                query=observation.normalized_query,
            )
            if oracle_evidence and gold_hypothesis is not None and gold_docs:
                bundles = _oracle_evidence_bundles(gold_hypothesis, gold_docs, candidates, round_index=1)
            for bundle in bundles:
                evidence_items.extend(bundle.items)
            belief = updater.update(belief, bundles, round_index=1)
        if oracle_belief and gold_hypothesis is not None:
            ordered = [gold_hypothesis.hypothesis_id] + [
                c.hypothesis.hypothesis_id
                for c in candidates
                if c.hypothesis.hypothesis_id != gold_hypothesis.hypothesis_id
            ]
            belief = self.disc_updater.from_ranking(candidates, ordered, round_index=belief.round_index)
        support = {c.hypothesis.hypothesis_id: 0.0 for c in candidates}
        for item in evidence_items:
            support[item.hypothesis_id] = max(support.get(item.hypothesis_id, 0.0), item.support_score)
        decision = self.decision.decide(
            belief,
            support,
            explore_rounds=explore_rounds,
            discriminative_power=0.5 if arm != "fast" else 0.0,
            exploration_enabled=False,
            ask_enabled=True,
        )
        predicted = belief.top_hypothesis_id
        if decision.action == Action.ANSWER:
            predicted = decision.selected_hypothesis_id or predicted
        b_star_after = (
            belief.probabilities.get(gold_hypothesis.hypothesis_id, 0.0) if gold_hypothesis else None
        )
        return RescueRun(
            predicted_id=predicted,
            belief=belief,
            action=decision.action.value,
            evidence=tuple(evidence_items),
            retrieved_ids=tuple(dict.fromkeys(retrieved)),
            candidates=tuple(candidates),
            retrieval_calls=retrieval_calls,
            seed_calls=seed_calls,
            explore_rounds=explore_rounds,
            observation=observation,
            b_star_before=b_star_before,
            b_star_after=b_star_after,
            arm=arm,
            mode=mode,
        )


def _select_queries(arm: str, queries: dict[str, str], observation: Observation) -> list[str]:
    if arm in {"bm25", "dense", "hybrid", "relevance"}:
        return [observation.normalized_query]
    if arm == "hypothesis_conditioned":
        return [queries.get("hypothesis") or observation.normalized_query]
    if arm == "falsification":
        return [queries.get("falsification") or observation.normalized_query]
    if arm == "contradiction":
        return [queries.get("falsification") or observation.normalized_query]
    if arm in {"pairwise_contrastive", "discriminative_rerank", "eig_approx"}:
        return [queries[key] for key in ("pairwise_plus", "contrast", "falsification") if key in queries] or [
            observation.normalized_query
        ]
    return [observation.normalized_query]


def _oracle_evidence_bundles(
    gold: Hypothesis,
    gold_docs: Sequence[Document],
    candidates: Sequence[HypothesisCandidate],
    *,
    round_index: int,
) -> list[EvidenceBundle]:
    bundles: list[EvidenceBundle] = []
    for candidate in candidates:
        hid = candidate.hypothesis.hypothesis_id
        items: list[EvidenceItem] = []
        for rank, doc in enumerate(gold_docs, start=1):
            favor = hid == gold.hypothesis_id
            items.append(
                EvidenceItem(
                    evidence_id=f"oracle:{hid}:{doc.document_id}",
                    hypothesis_id=hid,
                    document_id=doc.document_id,
                    title=doc.title,
                    snippet=doc.text[:240],
                    retrieval_score=1.0 if favor else 0.05,
                    observation_coverage=1.0 if favor else 0.1,
                    anchor_coverage=1.0 if favor else 0.0,
                    discriminator_coverage=1.0 if favor else 0.0,
                    foreign_hypothesis=not favor,
                    support_score=0.95 if favor else 0.02,
                    retrieval_rank=rank,
                    round_index=round_index,
                    query="oracle_evidence",
                )
            )
        bundles.append(
            EvidenceBundle(
                hypothesis_id=hid,
                items=tuple(items),
                aggregate_support=0.95 if hid == gold.hypothesis_id else 0.02,
                novel_item_count=len(items),
            )
        )
    return bundles
