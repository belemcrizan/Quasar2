"""End-to-end QUASAR2 inference loop.

Flow: observation -> competing hypotheses -> guided retrieval -> evidence ->
belief -> ANSWER/EXPLORE/ASK.  Every transition is emitted as trace data.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import time
from typing import Any, Mapping

from quasar2.belief.updater import BeliefUpdater
from quasar2.config import ProjectConfig, load_structured
from quasar2.decision.engine import DecisionEngine
from quasar2.decision.utility import UtilityModel
from quasar2.evidence.scorer import EvidenceScorer
from quasar2.exploration.discriminator import HypothesisDiscriminator
from quasar2.exploration.explorer import Explorer
from quasar2.hypotheses.catalog import CatalogHypothesisGenerator, HypothesisCatalog
from quasar2.models.decision import Action
from quasar2.models.evidence import EvidenceBundle, EvidenceItem
from quasar2.models.telemetry import PipelineResult, TraceEvent
from quasar2.retrieval import Retriever, SearchHit, load_corpus
from quasar2.retrieval.factory import build_retriever
from quasar2.signals.extractor import SignalExtractor, normalize_text


VALID_ABLATIONS = frozenset({"full", "noHyp", "noExplore", "noUpdate", "noAsk"})


class QuasarPipeline:
    """Composable, deterministic implementation of the frozen POC thesis."""

    def __init__(
        self,
        *,
        signal_extractor: SignalExtractor,
        hypothesis_generator: CatalogHypothesisGenerator,
        retriever: Retriever,
        evidence_scorer: EvidenceScorer,
        belief_updater: BeliefUpdater,
        decision_engine: DecisionEngine,
        discriminator: HypothesisDiscriminator,
        explorer: Explorer,
        max_candidates: int = 4,
        minimum_generation_score: float = 0.0,
        initial_top_k: int = 1,
        top_k: int = 4,
        deduplicate_queries: bool = True,
        stop_on_zero_novelty: bool = True,
        clarification_templates: Mapping[str, str] | None = None,
    ) -> None:
        self.signal_extractor = signal_extractor
        self.hypothesis_generator = hypothesis_generator
        self.retriever = retriever
        self.evidence_scorer = evidence_scorer
        self.belief_updater = belief_updater
        self.decision_engine = decision_engine
        self.discriminator = discriminator
        self.explorer = explorer
        self.max_candidates = max_candidates
        self.minimum_generation_score = minimum_generation_score
        self.initial_top_k = initial_top_k
        self.top_k = top_k
        self.deduplicate_queries = deduplicate_queries
        self.stop_on_zero_novelty = stop_on_zero_novelty
        self.clarification_templates = dict(clarification_templates or {})

    @classmethod
    def from_config(cls, config: ProjectConfig, *, retriever: Retriever | None = None) -> "QuasarPipeline":
        paths = config.section("paths")
        domains = load_structured(config.resolve(str(paths["domains"])))
        cues = {domain: values.get("domain_cues", ()) for domain, values in domains.items()}
        templates = {
            domain: str(values.get("clarification_template", "Which interpretation do you mean: {options}?"))
            for domain, values in domains.items()
        }
        catalog = HypothesisCatalog.from_directory(config.resolve(str(paths["catalog"])))
        documents = load_corpus(config.resolve(str(paths["corpus"])))
        retrieval = config.section("retrieval")
        selected = retriever or build_retriever(
            documents,
            backend=str(retrieval.get("backend", "hybrid")),
            retrieval=retrieval,
        )
        belief = config.section("belief")
        decision = config.section("decision")
        exploration = config.section("exploration")
        hypothesis_config = config.section("hypotheses")
        return cls(
            signal_extractor=SignalExtractor(cues),
            hypothesis_generator=CatalogHypothesisGenerator(catalog),
            retriever=selected,
            evidence_scorer=EvidenceScorer(config.section("evidence")),
            belief_updater=BeliefUpdater(
                evidence_strength=float(belief.get("evidence_strength", 4.0)),
                temperature=float(belief.get("temperature", 1.0)),
                probability_floor=float(belief.get("probability_floor", 1e-6)),
            ),
            decision_engine=DecisionEngine(
                answer_confidence=float(decision.get("answer_confidence", 0.67)),
                answer_margin=float(decision.get("answer_margin", 0.20)),
                minimum_evidence=float(decision.get("minimum_evidence", 0.28)),
                minimum_exploration_value=float(decision.get("minimum_exploration_value", 0.04)),
                max_explore_rounds=int(decision.get("max_explore_rounds", 2)),
                allow_ask=bool(decision.get("allow_ask", True)),
                utility_model=UtilityModel(
                    wrong_answer_cost=float(decision.get("wrong_answer_cost", 1.4)),
                    exploration_cost=float(decision.get("exploration_cost", 0.10)),
                    ask_cost=float(decision.get("ask_cost", 0.28)),
                ),
            ),
            discriminator=HypothesisDiscriminator(),
            explorer=Explorer(),
            max_candidates=int(hypothesis_config.get("max_candidates", 4)),
            minimum_generation_score=float(
                hypothesis_config.get("minimum_generation_score", 0.0)
            ),
            initial_top_k=int(retrieval.get("initial_top_k_per_hypothesis", 1)),
            top_k=int(retrieval.get("top_k_per_hypothesis", 4)),
            deduplicate_queries=bool(exploration.get("deduplicate_queries", True)),
            stop_on_zero_novelty=bool(exploration.get("stop_on_zero_novelty", True)),
            clarification_templates=templates,
        )

    @staticmethod
    def _query_hash(hypothesis_id: str, query: str) -> str:
        """Return a stable identity for a hypothesis-conditioned query."""

        canonical = f"{hypothesis_id}\0{normalize_text(query)}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def run(
        self,
        query: str,
        domain: str,
        *,
        ablation: str = "full",
        observation_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PipelineResult:
        if ablation not in VALID_ABLATIONS:
            raise ValueError(f"Unknown ablation {ablation!r}; choose from {sorted(VALID_ABLATIONS)}")
        started = time.perf_counter()
        trace: list[TraceEvent] = []

        def emit(stage: str, message: str, **payload: Any) -> None:
            trace.append(TraceEvent(len(trace) + 1, stage, message, payload))

        observation = self.signal_extractor.extract(
            query, domain, observation_id=observation_id, metadata=metadata
        )
        emit(
            "OBSERVATION",
            "extracted weak query signals",
            tokens=list(observation.tokens),
            signal_quality=observation.signal_quality,
            estimated_degradation=observation.estimated_degradation,
        )
        generated = self.hypothesis_generator.generate(
            observation, max_candidates=self.max_candidates
        )
        candidates = tuple(
            candidate
            for candidate in generated
            if candidate.generation_score >= self.minimum_generation_score
        ) or generated[:1]
        if ablation == "noHyp":
            candidates = candidates[:1]
        emit(
            "HYPOTHESES",
            "generated explicit candidate interpretations",
            candidates=[
                {
                    "id": candidate.hypothesis.hypothesis_id,
                    "score": candidate.generation_score,
                    "rationale": candidate.rationale,
                }
                for candidate in candidates
            ],
        )
        belief = self.belief_updater.initialize(candidates)
        evidence_items: list[EvidenceItem] = []
        seen_pairs: set[tuple[str, str]] = set()
        seen_document_ids: set[str] = set()
        issued_query_hashes: set[str] = set()
        cumulative_support = {candidate.hypothesis.hypothesis_id: 0.0 for candidate in candidates}
        retrieval_calls = 0
        retrieval_calls_avoided = 0
        pruned_explorations = 0
        explore_rounds = 0
        termination_reason = "decision"
        document_novelties: list[float] = []
        retrieval_hits: list[SearchHit] = []
        seen_hit_ids: set[str] = set()
        total_belief_variation = 0.0
        total_observed_entropy_reduction = 0.0
        current_queries = {
            candidate.hypothesis.hypothesis_id: " ".join(
                (observation.normalized_query, candidate.hypothesis.label)
            )
            for candidate in candidates
        }
        active_ids = tuple(current_queries)
        round_index = 0
        decision = None

        while True:
            bundles: list[EvidenceBundle] = []
            round_novel_items = 0
            candidate_by_id = {c.hypothesis.hypothesis_id: c for c in candidates}
            for hypothesis_id in active_ids:
                candidate = candidate_by_id[hypothesis_id]
                retrieval_query = current_queries[hypothesis_id]
                query_hash = self._query_hash(hypothesis_id, retrieval_query)
                issued_query_hashes.add(query_hash)
                hits = self.retriever.search(
                    retrieval_query,
                    top_k=self.initial_top_k if round_index == 0 else self.top_k,
                    domain=domain,
                )
                retrieval_calls += 1
                document_ids = [hit.document.document_id for hit in hits]
                for hit in hits:
                    document_id = hit.document.document_id
                    if document_id not in seen_hit_ids:
                        seen_hit_ids.add(document_id)
                        retrieval_hits.append(hit)
                repeated_document_count = sum(
                    document_id in seen_document_ids for document_id in document_ids
                )
                document_novelty = 1.0 - repeated_document_count / max(1, len(document_ids))
                document_novelties.append(document_novelty)
                seen_document_ids.update(document_ids)
                emit(
                    "RETRIEVAL",
                    "retrieved hypothesis-guided documents",
                    round=round_index,
                    hypothesis_id=hypothesis_id,
                    query=retrieval_query,
                    query_hash=query_hash,
                    documents=document_ids,
                    document_novelty=document_novelty,
                    novel_document_count=len(document_ids) - repeated_document_count,
                    repeated_document_count=repeated_document_count,
                )
                bundle = self.evidence_scorer.score(
                    observation,
                    candidate,
                    hits,
                    round_index=round_index,
                    seen_pairs=seen_pairs,
                    query=retrieval_query,
                )
                bundles.append(bundle)
                round_novel_items += bundle.novel_item_count
                for item in bundle.items:
                    seen_pairs.add((item.hypothesis_id, item.document_id))
                    evidence_items.append(item)
                if bundle.novel_item_count:
                    cumulative_support[hypothesis_id] = max(
                        cumulative_support[hypothesis_id], bundle.aggregate_support
                    )
                emit(
                    "EVIDENCE",
                    "scored novel evidence",
                    round=round_index,
                    hypothesis_id=hypothesis_id,
                    aggregate_support=bundle.aggregate_support,
                    novel_items=bundle.novel_item_count,
                )
            # Candidates not explored this round receive explicit empty bundles.
            bundled_ids = {bundle.hypothesis_id for bundle in bundles}
            bundles.extend(
                EvidenceBundle(candidate.hypothesis.hypothesis_id, (), 0.0, 0)
                for candidate in candidates
                if candidate.hypothesis.hypothesis_id not in bundled_ids
            )
            previous_belief = belief
            if ablation != "noUpdate":
                belief = self.belief_updater.update(belief, bundles, round_index=round_index)
            else:
                belief = replace(belief, round_index=round_index)
            total_variation = 0.5 * sum(
                abs(
                    belief.probabilities.get(hypothesis_id, 0.0)
                    - previous_belief.probabilities.get(hypothesis_id, 0.0)
                )
                for hypothesis_id in set(belief.probabilities)
                | set(previous_belief.probabilities)
            )
            observed_entropy_reduction = previous_belief.entropy - belief.entropy
            total_belief_variation += total_variation
            total_observed_entropy_reduction += observed_entropy_reduction
            emit(
                "BELIEF",
                "updated competing beliefs" if ablation != "noUpdate" else "belief update ablated",
                round=round_index,
                probabilities=dict(belief.probabilities),
                entropy=belief.normalized_entropy,
                margin=belief.margin,
                total_variation=total_variation,
                observed_entropy_reduction=observed_entropy_reduction,
            )
            plan = self.discriminator.plan(observation, candidates, belief)
            exploration_enabled = ablation != "noExplore" and len(candidates) > 1
            ungated_decision = self.decision_engine.decide(
                belief,
                cumulative_support,
                explore_rounds=explore_rounds,
                discriminative_power=plan.power,
                exploration_enabled=exploration_enabled,
                ask_enabled=ablation != "noAsk" and self.decision_engine.allow_ask,
            )
            zero_novelty_stop = (
                self.stop_on_zero_novelty
                and round_index > 0
                and round_novel_items == 0
                and ungated_decision.action == Action.EXPLORE
            )
            if zero_novelty_stop:
                avoided_queries = self.explorer.build_queries(observation, candidates, plan)
                avoided_count = len(avoided_queries)
                retrieval_calls_avoided += avoided_count
                pruned_explorations += 1
                termination_reason = "zero_novel_evidence"
                emit(
                    "ACQUISITION_STOP",
                    "stopped exploration after a zero-novelty acquisition round",
                    round=round_index,
                    reason=termination_reason,
                    novel_evidence_items=round_novel_items,
                    avoided_retrieval_calls=avoided_count,
                )
                decision = self.decision_engine.decide(
                    belief,
                    cumulative_support,
                    explore_rounds=explore_rounds,
                    discriminative_power=plan.power,
                    exploration_enabled=False,
                    ask_enabled=ablation != "noAsk" and self.decision_engine.allow_ask,
                )
            else:
                decision = ungated_decision
            emit(
                "DECISION",
                decision.rationale,
                action=decision.action.value,
                confidence=decision.confidence,
                margin=decision.margin,
                utilities=dict(decision.utilities),
                expected_information_gain=decision.expected_information_gain,
            )
            if decision.action != Action.EXPLORE:
                if termination_reason == "decision":
                    termination_reason = f"decision_{decision.action.value.lower()}"
                break
            proposed_queries = self.explorer.build_queries(observation, candidates, plan)
            repeated_queries: dict[str, str] = {}
            if self.deduplicate_queries:
                for hypothesis_id, proposed_query in proposed_queries.items():
                    query_hash = self._query_hash(hypothesis_id, proposed_query)
                    if query_hash in issued_query_hashes:
                        repeated_queries[hypothesis_id] = query_hash
            current_queries = {
                hypothesis_id: proposed_query
                for hypothesis_id, proposed_query in proposed_queries.items()
                if hypothesis_id not in repeated_queries
            }
            if repeated_queries:
                avoided_count = len(repeated_queries)
                retrieval_calls_avoided += avoided_count
                pruned_explorations += 1
                emit(
                    "EXPLORATION_PRUNED",
                    "rejected repeated hypothesis-conditioned retrieval queries",
                    round=round_index + 1,
                    reason="repeated_query",
                    repeated_query_hashes=repeated_queries,
                    avoided_retrieval_calls=avoided_count,
                )
            if not current_queries:
                termination_reason = "repeated_query"
                decision = self.decision_engine.decide(
                    belief,
                    cumulative_support,
                    explore_rounds=explore_rounds,
                    discriminative_power=plan.power,
                    exploration_enabled=False,
                    ask_enabled=ablation != "noAsk" and self.decision_engine.allow_ask,
                )
                emit(
                    "DECISION",
                    f"exploration pruned; {decision.rationale}",
                    action=decision.action.value,
                    confidence=decision.confidence,
                    margin=decision.margin,
                    utilities=dict(decision.utilities),
                    expected_information_gain=decision.expected_information_gain,
                )
                break
            explore_rounds += 1
            round_index += 1
            active_ids = tuple(current_queries)
            emit(
                "EXPLORATION",
                "issued autonomous discriminative retrieval",
                round=round_index,
                rationale=plan.rationale,
                power=plan.power,
                queries=current_queries,
                query_hashes={
                    hypothesis_id: self._query_hash(hypothesis_id, retrieval_query)
                    for hypothesis_id, retrieval_query in current_queries.items()
                },
            )

        assert decision is not None
        predicted_id = belief.top_hypothesis_id
        selected_evidence = sorted(
            (item for item in evidence_items if item.hypothesis_id == predicted_id),
            key=lambda item: (-item.support_score, item.document_id),
        )
        selected_hypothesis = next(
            candidate.hypothesis for candidate in candidates
            if candidate.hypothesis.hypothesis_id == predicted_id
        )
        answer = None
        clarification = None
        if decision.action == Action.ANSWER:
            source = selected_evidence[0].snippet if selected_evidence else selected_hypothesis.description
            answer = f"{selected_hypothesis.label}: {source}"
        elif decision.action == Action.ASK:
            ordered = sorted(
                candidates,
                key=lambda candidate: (-belief.probabilities[candidate.hypothesis.hypothesis_id], candidate.rank),
            )[:3]
            options = ", ".join(candidate.hypothesis.label for candidate in ordered)
            template = self.clarification_templates.get(
                domain, "Which interpretation do you mean: {options}?"
            )
            clarification = template.format(options=options)
        emit(
            "RESULT",
            "completed inference loop",
            predicted_hypothesis_id=predicted_id,
            action=decision.action.value,
            retrieval_calls=retrieval_calls,
            explore_rounds=explore_rounds,
            retrieval_calls_avoided=retrieval_calls_avoided,
            pruned_explorations=pruned_explorations,
            termination_reason=termination_reason,
            mean_document_novelty=(
                sum(document_novelties) / len(document_novelties)
                if document_novelties
                else 0.0
            ),
            total_belief_variation=total_belief_variation,
            total_observed_entropy_reduction=total_observed_entropy_reduction,
        )
        return PipelineResult(
            observation=observation,
            candidates=candidates,
            final_belief=belief,
            decision=decision,
            predicted_hypothesis_id=predicted_id,
            answer=answer,
            clarification_question=clarification,
            evidence=tuple(evidence_items),
            trace=tuple(trace),
            retrieval_calls=retrieval_calls,
            explore_rounds=explore_rounds,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            ablation=ablation,
            retrieval_calls_avoided=retrieval_calls_avoided,
            pruned_explorations=pruned_explorations,
            termination_reason=termination_reason,
            issued_query_hashes=tuple(sorted(issued_query_hashes)),
            mean_document_novelty=(
                sum(document_novelties) / len(document_novelties)
                if document_novelties
                else 0.0
            ),
            total_belief_variation=total_belief_variation,
            total_observed_entropy_reduction=total_observed_entropy_reduction,
            retrieval_hits=tuple(retrieval_hits),
        )
