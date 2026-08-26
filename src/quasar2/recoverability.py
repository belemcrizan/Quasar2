"""Recoverability estimators. No single divergence is assumed to be best."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from quasar2.math.divergences import (
    kl_divergence,
    symmetric_kl,
    total_variation,
    weighted_jsd,
)
from quasar2.math.voi import voi_bound_binary, voi_bound_general
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
}
