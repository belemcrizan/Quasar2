"""Versioned theorem cards and execution status. Never record a bare PASS."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


THEOREM_KINDS = ("theorem", "proposition", "hypothesis", "empirical_result", "refuted")
EXECUTION_STATES = (
    "NOT_IMPLEMENTED",
    "IMPLEMENTED_NOT_RUN",
    "PASS_WITHIN_ASSUMPTIONS",
    "FAIL_NUMERICAL",
    "FAIL_MONTE_CARLO",
    "FAIL_ASSUMPTION",
    "COUNTEREXAMPLE_FOUND",
    "INCONCLUSIVE",
)


@dataclass(frozen=True, slots=True)
class TheoremCard:
    id: str
    status: str
    statement: str
    assumptions: tuple[str, ...]
    quantities_observable: tuple[str, ...]
    oracle_only: tuple[str, ...]
    proof_or_reference: str
    test_harness: str
    numeric_tolerance: Mapping[str, float] | None = None
    known_counterexamples: tuple[str, ...] = ()
    last_validated_run_id: str | None = None
    code_version: str | None = None
    dataset_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.numeric_tolerance is not None:
            payload["numeric_tolerance"] = dict(self.numeric_tolerance)
        return payload


@dataclass
class TheoremCheck:
    card_id: str
    execution_state: str
    layer: str
    assumptions_verified: tuple[str, ...]
    implementation: str
    atol: float
    rtol: float
    seeds: tuple[int, ...]
    dataset: str
    notes: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_cards() -> tuple[TheoremCard, ...]:
    return (
        TheoremCard(
            id="T1",
            status="theorem",
            statement=(
                "For a fixed model, evidence, and target posterior, an admissible "
                "variational update that does not decrease ELBO also does not increase KL(q||p*)."
            ),
            assumptions=(
                "target posterior fixed",
                "evidence fixed",
                "support compatible",
                "operator is admissible variational or exact I-projection mixture",
            ),
            quantities_observable=("elbo_before", "elbo_after", "kl_before", "kl_after"),
            oracle_only=("target posterior p*",),
            proof_or_reference="docs/THEORY.md#t1; Blei et al. arXiv:1601.00670",
            test_harness="quasar2.theory.harness.check_t1",
            numeric_tolerance={"atol": 1e-9, "rtol": 1e-8},
        ),
        TheoremCard(
            id="T2",
            status="theorem",
            statement=(
                "E|b'-b| = 2 b (1-b) TV(P1,P2); VoI bounds follow from the declared Lipschitz convention."
            ),
            assumptions=(
                "binary hypotheses",
                "common observation space",
                "V* Lipschitz in the declared norm",
                "observation kernels used in the bound match the sampling mechanism",
            ),
            quantities_observable=("expected_belief_movement", "tv", "jsd", "voi_empirical"),
            oracle_only=("true kernels", "true VoI"),
            proof_or_reference="docs/THEORY.md#t2",
            test_harness="quasar2.theory.harness.check_t2",
            numeric_tolerance={"atol": 1e-9, "rtol": 1e-8},
        ),
        TheoremCard(
            id="T3",
            status="theorem",
            statement=(
                "The optimal Bellman operator on a discounted bounded-reward MDP is a gamma-contraction "
                "in sup norm; value-iteration error is gamma^k times the initial error."
            ),
            assumptions=("MDP", "bounded rewards", "gamma in [0,1)", "exact Bellman backup"),
            quantities_observable=("sup_norm_residual", "contraction_ratio"),
            oracle_only=("V* when compared exactly",),
            proof_or_reference="docs/THEORY.md#t3",
            test_harness="quasar2.theory.harness.check_t3",
            numeric_tolerance={"atol": 1e-8, "rtol": 1e-7},
        ),
        TheoremCard(
            id="T4",
            status="proposition",
            statement=(
                "Fixed-stage Bonferroni UCB controls P(false stop) at a single look under valid "
                "per-action tail inequalities. Sequential looks require a different coverage_scope."
            ),
            assumptions=(
                "fixed stage or declared sequential correction",
                "valid UCB estimator for the sample class",
                "m information actions",
            ),
            quantities_observable=("false_stop_rate", "wilson_upper"),
            oracle_only=("oracle_best_net_voi",),
            proof_or_reference="docs/THEORY.md#t4",
            test_harness="quasar2.theory.harness.check_t4",
            numeric_tolerance={"atol": 0.02, "rtol": 0.0},
        ),
        TheoremCard(
            id="C1",
            status="proposition",
            statement=(
                "I(I;Q_clean)-I(I;Q_obs) is a nonnegative information loss only under a Markov "
                "degradation chain. Side information can make the difference negative."
            ),
            assumptions=("discrete joint identifiable", "optional Markov degradation"),
            quantities_observable=("information_difference",),
            oracle_only=("true joints",),
            proof_or_reference="docs/THEORY.md#c1",
            test_harness="quasar2.theory.harness.check_c1",
            numeric_tolerance={"atol": 1e-9, "rtol": 1e-8},
        ),
    )
