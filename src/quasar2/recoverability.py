"""Recoverability estimators. No single divergence is assumed to be best."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from quasar2.math.divergences import (
    entropy,
    kl_divergence,
    symmetric_kl,
    total_variation,
    weighted_jsd,
)
from quasar2.math.linear import dot, ridge_fit
from quasar2.math.voi import (
    empirical_binary_voi_zero_one,
    empirical_decision_flip_probability,
    voi_bound_binary,
    voi_bound_general,
)
from quasar2.math.conventions import LipschitzNorm, MeasureConventions


@dataclass(frozen=True, slots=True)
class RecoverabilityResult:
    method: str
    score: float
    recoverability_kl: float | None = None
    recoverability_tv: float | None = None
    recoverability_jsd: float | None = None
    conditional_mutual_information: float | None = None
    details: Mapping[str, float | str | bool | None] | None = None


class RecoverabilityEstimator(Protocol):
    name: str

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        ...


class TVRecoverability:
    name = "tv"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        pair = _top_pair(belief, hypotheses, observation_model)
        if pair is None:
            return RecoverabilityResult(self.name, 0.0, recoverability_tv=0.0)
        left, right = pair
        tv = total_variation(observation_model[left], observation_model[right])
        return RecoverabilityResult(self.name, tv, recoverability_tv=tv)


class KLRecoverability:
    name = "kl"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        pair = _top_pair(belief, hypotheses, observation_model)
        if pair is None:
            return RecoverabilityResult(self.name, 0.0, recoverability_kl=0.0)
        left, right = pair
        kl = kl_divergence(observation_model[left], observation_model[right])
        return RecoverabilityResult(self.name, kl, recoverability_kl=kl)


class SymmetricKLRecoverability:
    name = "symmetric_kl"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        pair = _top_pair(belief, hypotheses, observation_model)
        if pair is None:
            return RecoverabilityResult(self.name, 0.0, recoverability_kl=0.0)
        left, right = pair
        score = symmetric_kl(observation_model[left], observation_model[right])
        return RecoverabilityResult(self.name, score, recoverability_kl=score)


class JSDRecoverability:
    name = "jsd"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        weights = {hyp: float(belief.get(hyp, 0.0)) for hyp in hypotheses if hyp in observation_model}
        total = sum(weights.values())
        if total <= 0.0:
            return RecoverabilityResult(self.name, 0.0, recoverability_jsd=0.0)
        weights = {key: value / total for key, value in weights.items()}
        jsd = weighted_jsd(observation_model, weights)
        return RecoverabilityResult(
            self.name,
            jsd,
            recoverability_jsd=jsd,
            conditional_mutual_information=jsd,
        )


class MutualInformationRecoverability(JSDRecoverability):
    name = "mutual_information"


class EmpiricalDiscriminationRecoverability:
    name = "empirical_discrimination"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        pair = _top_pair(belief, hypotheses, observation_model)
        if pair is None:
            return RecoverabilityResult(self.name, 0.0)
        left, right = pair
        tv = total_variation(observation_model[left], observation_model[right])
        b = float(belief.get(left, 0.0))
        conventions = MeasureConventions(lipschitz_norm=LipschitzNorm.SCALAR_BINARY)
        bound = voi_bound_binary(b, observation_model[left], observation_model[right], conventions=conventions)
        general = voi_bound_general(observation_model, {hyp: float(belief.get(hyp, 0.0)) for hyp in hypotheses})
        return RecoverabilityResult(
            self.name,
            tv,
            recoverability_tv=tv,
            recoverability_kl=bound.recoverability_kl,
            recoverability_jsd=general.recoverability_jsd,
            conditional_mutual_information=general.conditional_mutual_information,
            details={"candidate_action": candidate_action, "voi_bound_tv": bound.voi_bound_tv},
        )


class DecisionRecoverability:
    """Expected probability that one observation flips the 0-1 argmax.

    Deployment-safe: uses only belief and an observation model. Gold intent is unused.
    """

    name = "decision_recoverability"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        pair = _top_pair(belief, hypotheses, observation_model)
        if pair is None:
            return RecoverabilityResult(self.name, 0.0, details={"candidate_action": candidate_action})
        left, right = pair
        b = float(belief.get(left, 0.0))
        score = empirical_decision_flip_probability(b, observation_model[left], observation_model[right])
        return RecoverabilityResult(self.name, score, details={"candidate_action": candidate_action})


class BeliefMarginRecoverability:
    name = "belief_margin"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        ranked = sorted((float(belief.get(hyp, 0.0)) for hyp in hypotheses), reverse=True)
        if len(ranked) < 2:
            score = 1.0
        else:
            score = ranked[0] - ranked[1]
        return RecoverabilityResult(self.name, score, details={"candidate_action": candidate_action})


class EntropyRecoverability:
    """Uncertainty baseline, not a recoverability claim. Kept for comparison."""

    name = "entropy"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        masses = {hyp: float(belief.get(hyp, 0.0)) for hyp in hypotheses}
        total = sum(masses.values())
        if total <= 0.0:
            return RecoverabilityResult(self.name, 0.0)
        normalized = {key: value / total for key, value in masses.items()}
        return RecoverabilityResult(self.name, entropy(normalized), details={"candidate_action": candidate_action})


class RetrieverScoreMarginRecoverability:
    name = "retriever_score_margin"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        pair = _top_pair(belief, hypotheses, observation_model)
        if pair is None:
            return RecoverabilityResult(self.name, 0.0)
        left, right = pair
        left_hit = float(observation_model[left].get("hit", max(observation_model[left].values(), default=0.0)))
        right_hit = float(observation_model[right].get("hit", max(observation_model[right].values(), default=0.0)))
        return RecoverabilityResult(self.name, abs(left_hit - right_hit))


class EmbeddingSeparationRecoverability:
    """TV of observation kernels as an embedding-separation proxy when embeddings are absent."""

    name = "embedding_separation"

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        pair = _top_pair(belief, hypotheses, observation_model)
        if pair is None:
            return RecoverabilityResult(self.name, 0.0)
        left, right = pair
        tv = total_variation(observation_model[left], observation_model[right])
        return RecoverabilityResult(self.name, tv, recoverability_tv=tv)


def deployment_features(
    belief: Mapping[str, float],
    hypotheses: tuple[str, ...],
    observation_model: Mapping[str, Mapping[str, float]],
) -> list[float]:
    """Features available at deployment. Gold intent is not included."""

    ranked = sorted(
        (float(belief.get(hyp, 0.0)) for hyp in hypotheses),
        reverse=True,
    )
    top1 = ranked[0] if ranked else 0.0
    margin = (ranked[0] - ranked[1]) if len(ranked) >= 2 else 1.0
    masses = {hyp: float(belief.get(hyp, 0.0)) for hyp in hypotheses}
    total = sum(masses.values())
    normalized = {key: value / total for key, value in masses.items()} if total > 0.0 else masses
    ent = entropy(normalized) if total > 0.0 else 0.0
    pair = _top_pair(belief, hypotheses, observation_model)
    tv = 0.0
    jsd = 0.0
    kl = 0.0
    drs = 0.0
    score_margin = 0.0
    if pair is not None:
        left, right = pair
        tv = total_variation(observation_model[left], observation_model[right])
        jsd = weighted_jsd(observation_model, normalized)
        kl_raw = kl_divergence(observation_model[left], observation_model[right], smooth=1e-12)
        kl = 20.0 if kl_raw == float("inf") else min(20.0, max(0.0, kl_raw))
        b = float(belief.get(left, 0.0))
        drs = empirical_decision_flip_probability(b, observation_model[left], observation_model[right])
        left_hit = float(observation_model[left].get("hit", max(observation_model[left].values(), default=0.0)))
        right_hit = float(observation_model[right].get("hit", max(observation_model[right].values(), default=0.0)))
        score_margin = abs(left_hit - right_hit)
        if jsd == float("inf"):
            jsd = 20.0
    unknown = float(belief.get("H_unknown", 0.0))
    return [1.0, ent, margin, top1, tv, jsd, kl, drs, score_margin, unknown]


def router_features(
    belief: Mapping[str, float],
    hypotheses: tuple[str, ...],
    observation_model: Mapping[str, Mapping[str, float]],
    *,
    entropy: float,
    unknown_mass: float,
    inference_error: float | None,
    explore_cost: float,
    ask_cost: float,
    evidence_present: bool,
) -> list[float]:
    return deployment_features(belief, hypotheses, observation_model) + [
        entropy,
        unknown_mass,
        0.0 if inference_error is None else inference_error,
        explore_cost,
        ask_cost,
        1.0 if evidence_present else 0.0,
    ]


class LearnedRecoverabilityEstimator:
    """Optional linear predictor of empirical VoI. Fit only on synthetic labels.

    Labels may be VoI_empirical or 1[NetVoI>0] from a simulatable environment.
    """

    name = "learned"

    def __init__(self, weights: list[float] | None = None) -> None:
        self.weights = weights

    def fit(
        self,
        rows: list[tuple[Mapping[str, float], tuple[str, ...], Mapping[str, Mapping[str, float]]]],
        targets: list[float],
        *,
        lam: float = 1e-3,
    ) -> None:
        design = [deployment_features(belief, hyps, kernels) for belief, hyps, kernels in rows]
        self.weights = ridge_fit(design, targets, lam=lam)

    def estimate(
        self,
        belief: Mapping[str, float],
        hypotheses: tuple[str, ...],
        candidate_action: str,
        observation_model: Mapping[str, Mapping[str, float]],
    ) -> RecoverabilityResult:
        if self.weights is None:
            return RecoverabilityResult(self.name, 0.0, details={"fitted": False, "candidate_action": candidate_action})
        features = deployment_features(belief, hypotheses, observation_model)
        score = max(0.0, dot(self.weights, features))
        return RecoverabilityResult(self.name, score, details={"fitted": True, "candidate_action": candidate_action})


def _top_pair(
    belief: Mapping[str, float],
    hypotheses: tuple[str, ...],
    observation_model: Mapping[str, Mapping[str, float]],
) -> tuple[str, str] | None:
    ranked = [
        hyp
        for hyp in sorted(hypotheses, key=lambda item: (-float(belief.get(item, 0.0)), item))
        if hyp in observation_model
    ]
    if len(ranked) < 2:
        return None
    return ranked[0], ranked[1]


ESTIMATORS: dict[str, RecoverabilityEstimator] = {
    "tv": TVRecoverability(),
    "kl": KLRecoverability(),
    "symmetric_kl": SymmetricKLRecoverability(),
    "jsd": JSDRecoverability(),
    "mutual_information": MutualInformationRecoverability(),
    "empirical_discrimination": EmpiricalDiscriminationRecoverability(),
    "decision_recoverability": DecisionRecoverability(),
    "retriever_score_margin": RetrieverScoreMarginRecoverability(),
    "embedding_separation": EmbeddingSeparationRecoverability(),
}

COMPARISON_PREDICTORS: dict[str, RecoverabilityEstimator] = {
    "belief_margin": BeliefMarginRecoverability(),
    "entropy": EntropyRecoverability(),
}
