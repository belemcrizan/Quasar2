"""End-to-end QUASAR2 inference loop.

Flow: observation -> competing hypotheses -> guided retrieval -> evidence ->
belief -> ANSWER/EXPLORE/ASK.  Every transition is emitted as trace data.
"""

from __future__ import annotations

from dataclasses import replace
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
from quasar2.retrieval import BM25Retriever, HashingDenseRetriever, HybridRetriever, load_corpus
from quasar2.signals.extractor import SignalExtractor


VALID_ABLATIONS = frozenset({"full", "noHyp", "noExplore", "noUpdate", "noAsk"})


class QuasarPipeline:
    """Composable, deterministic implementation of the frozen POC thesis."""

    def __init__(
        self,
        *,
        signal_extractor: SignalExtractor,
        hypothesis_generator: CatalogHypothesisGenerator,
        retriever: HybridRetriever,
        evidence_scorer: EvidenceScorer,
        belief_updater: BeliefUpdater,
        decision_engine: DecisionEngine,
        discriminator: HypothesisDiscriminator,
        explorer: Explorer,
        max_candidates: int = 4,
        minimum_generation_score: float = 0.0,
        initial_top_k: int = 1,
        top_k: int = 4,
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
        self.clarification_templates = dict(clarification_templates or {})

    @classmethod
    def from_config(cls, config: ProjectConfig) -> "QuasarPipeline":
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
        sparse = BM25Retriever(documents)
        dense = HashingDenseRetriever(
            documents, dimensions=int(retrieval.get("dense_dimensions", 384))
        )
        hybrid = HybridRetriever(
            sparse,
            dense,
            sparse_weight=float(retrieval.get("bm25_weight", 0.6)),
            dense_weight=float(retrieval.get("dense_weight", 0.4)),
            rrf_k=int(retrieval.get("rrf_k", 20)),
        )
        belief = config.section("belief")
        decision = config.section("decision")
        hypothesis_config = config.section("hypotheses")
        return cls(
            signal_extractor=SignalExtractor(cues),
            hypothesis_generator=CatalogHypothesisGenerator(catalog),
            retriever=hybrid,
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
            clarification_templates=templates,
        )

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
        cumulative_support = {candidate.hypothesis.hypothesis_id: 0.0 for candidate in candidates}
        retrieval_calls = 0
        explore_rounds = 0
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
            candidate_by_id = {c.hypothesis.hypothesis_id: c for c in candidates}
            for hypothesis_id in active_ids:
                candidate = candidate_by_id[hypothesis_id]
                retrieval_query = current_queries[hypothesis_id]
                hits = self.retriever.search(
                    retrieval_query,
                    top_k=self.initial_top_k if round_index == 0 else self.top_k,
                    domain=domain,
                )
                retrieval_calls += 1
                emit(
                    "RETRIEVAL",
                    "retrieved hypothesis-guided documents",
                    round=round_index,
                    hypothesis_id=hypothesis_id,
                    query=retrieval_query,
                    documents=[hit.document.document_id for hit in hits],
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
            if ablation != "noUpdate":
                belief = self.belief_updater.update(belief, bundles, round_index=round_index)
            else:
                belief = replace(belief, round_index=round_index)
            emit(
                "BELIEF",
                "updated competing beliefs" if ablation != "noUpdate" else "belief update ablated",
                round=round_index,
                probabilities=dict(belief.probabilities),
                entropy=belief.normalized_entropy,
                margin=belief.margin,
            )
            plan = self.discriminator.plan(observation, candidates, belief)
            decision = self.decision_engine.decide(
                belief,
                cumulative_support,
                explore_rounds=explore_rounds,
                discriminative_power=plan.power,
                exploration_enabled=ablation != "noExplore" and len(candidates) > 1,
                ask_enabled=ablation != "noAsk" and self.decision_engine.allow_ask,
            )
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
                break
            explore_rounds += 1
            round_index += 1
            current_queries = self.explorer.build_queries(observation, candidates, plan)
            active_ids = tuple(current_queries)
            emit(
                "EXPLORATION",
                "issued autonomous discriminative retrieval",
                round=round_index,
                rationale=plan.rationale,
                power=plan.power,
                queries=current_queries,
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
        )

