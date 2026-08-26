"""ANALYZE operators act on computational state without acquiring evidence.

ANALYZE_theory (variational / I-projection) is not claimed for heuristic impls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

from quasar2.math.divergences import kl_divergence
from quasar2.math.numerical import normalize_mass


@dataclass(frozen=True, slots=True)
class ComputationalState:
    features: Mapping[str, float] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    belief: Mapping[str, float]
    state: ComputationalState
    evidence_ids: tuple[str, ...]
    analyze_theory: str
    analyze_impl: str
    elbo_before: float | None = None
    elbo_after: float | None = None
    exact_update: bool = False
    target_fixed: bool = False
    support_compatible: bool = True
    changed_top1: bool = False


class AnalyzeOperator(Protocol):
    name: str
    analyze_theory: str

    def analyze(
        self,
        state: ComputationalState,
        evidence: Sequence[str],
        belief: Mapping[str, float],
        *,
        supports: Mapping[str, tuple[float, float]] | None = None,
        target: Mapping[str, float] | None = None,
    ) -> AnalyzeResult:
        ...


def _changed_top1(before: Mapping[str, float], after: Mapping[str, float]) -> bool:
    if not before or not after:
        return False
    top_before = max(before, key=lambda key: (before[key], key))
    top_after = max(after, key=lambda key: (after[key], key))
    return top_before != top_after


class NoOpAnalyze:
    name = "noop"
    analyze_theory = "none"

    def analyze(
        self,
        state: ComputationalState,
        evidence: Sequence[str],
        belief: Mapping[str, float],
        *,
        supports: Mapping[str, tuple[float, float]] | None = None,
        target: Mapping[str, float] | None = None,
    ) -> AnalyzeResult:
        return AnalyzeResult(
            belief=dict(belief),
            state=state,
            evidence_ids=tuple(evidence),
            analyze_theory=self.analyze_theory,
            analyze_impl=self.name,
            exact_update=True,
            target_fixed=True,
        )


class ConsistencyAnalyze:
    name = "consistency"
    analyze_theory = "heuristic"

    def analyze(
        self,
        state: ComputationalState,
        evidence: Sequence[str],
        belief: Mapping[str, float],
        *,
        supports: Mapping[str, tuple[float, float]] | None = None,
        target: Mapping[str, float] | None = None,
    ) -> AnalyzeResult:
        supports = supports or {}
        raw: dict[str, float] = {}
        for hyp, mass in belief.items():
            support, contradiction = supports.get(hyp, (0.0, 0.0))
            raw[hyp] = max(1e-12, mass * (1.0 + support) / (1.0 + contradiction))
        updated = normalize_mass(raw)
        return AnalyzeResult(
            belief=updated,
            state=state,
            evidence_ids=tuple(evidence),
            analyze_theory=self.analyze_theory,
            analyze_impl=self.name,
            changed_top1=_changed_top1(belief, updated),
        )


class ContradictionPropagationAnalyze(ConsistencyAnalyze):
    name = "contradiction_propagation"


class EvidenceReweightingAnalyze(ConsistencyAnalyze):
    name = "evidence_reweighting"


class SourceReliabilityAnalyze(ConsistencyAnalyze):
    name = "source_reliability"


class MixtureProjectionAnalyze:
    """Convex mixture toward a fixed target posterior. Valid T1 operator, not CAVI."""

    name = "mixture_projection"
    analyze_theory = "i_projection_mixture"

    def __init__(self, step: float = 0.5) -> None:
        if not 0.0 < step <= 1.0:
            raise ValueError("step must be in (0, 1]")
        self.step = step

    def analyze(
        self,
        state: ComputationalState,
        evidence: Sequence[str],
        belief: Mapping[str, float],
        *,
        supports: Mapping[str, tuple[float, float]] | None = None,
        target: Mapping[str, float] | None = None,
    ) -> AnalyzeResult:
        if target is None:
            raise ValueError("MixtureProjectionAnalyze requires a fixed target posterior")
        target_n = normalize_mass(target)
        belief_n = normalize_mass(belief)
        updated = {
            key: (1.0 - self.step) * belief_n.get(key, 0.0) + self.step * target_n.get(key, 0.0)
            for key in set(belief_n) | set(target_n)
        }
        updated = normalize_mass(updated)
        kl_before = kl_divergence(belief_n, target_n, smooth=1e-12)
        kl_after = kl_divergence(updated, target_n, smooth=1e-12)
        # ELBO relative to fixed log p(E): -KL(q || p*) up to a constant.
        return AnalyzeResult(
            belief=updated,
            state=state,
            evidence_ids=tuple(evidence),
            analyze_theory=self.analyze_theory,
            analyze_impl=self.name,
            elbo_before=-kl_before,
            elbo_after=-kl_after,
            exact_update=self.step == 1.0,
            target_fixed=True,
            support_compatible=True,
            changed_top1=_changed_top1(belief_n, updated),
        )


class VariationalAnalyze(MixtureProjectionAnalyze):
    """Experimental label. This is mixture projection, not mean-field CAVI."""

    name = "variational_mixture"
    analyze_theory = "variational_mixture_not_cavi"


OPERATORS: dict[str, AnalyzeOperator] = {
    "noop": NoOpAnalyze(),
    "consistency": ConsistencyAnalyze(),
    "contradiction_propagation": ContradictionPropagationAnalyze(),
    "evidence_reweighting": EvidenceReweightingAnalyze(),
    "source_reliability": SourceReliabilityAnalyze(),
    "mixture_projection": MixtureProjectionAnalyze(),
    "variational": VariationalAnalyze(),
}
