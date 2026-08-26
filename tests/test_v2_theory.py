from __future__ import annotations

import unittest

from quasar2.analysis.operators import ComputationalState, ConsistencyAnalyze, MixtureProjectionAnalyze, NoOpAnalyze
from quasar2.belief.types import EstimatedBelief, IdealBelief, diagnose
from quasar2.math.divergences import kl_divergence
from quasar2.math.stopping import NormalUCB, stop_if_all_ucb_nonpositive
from quasar2.theory.harness import check_c1, check_t1, check_t2, check_t3, check_t4
from quasar2.v24.actions import EpistemicAction, LEGAL_TRANSITIONS
from quasar2.v24.analyze import analyze
from quasar2.v24.state import BudgetState, HypothesisView, PolicyState


def _policy_state(evidence: tuple[str, ...]) -> PolicyState:
    hyps = (
        HypothesisView("h1", "NY.GDP", "BRA", "country", "2020", "US$", 0.6),
        HypothesisView("h2", "SP.POP", "BRA", "country", "2020", "count", 0.3),
        HypothesisView("H_unknown", None, None, None, None, None, 0.1),
    )
    return PolicyState(
        query="gdp brazil",
        language="en",
        hypotheses=hyps,
        evidence_ids=evidence,
        entropy=1.0,
        margin=0.3,
        unknown_score=0.1,
        coverage=1.0,
        contradiction=0.2,
        source_available=True,
        budget=BudgetState(),
    )


class TheoremHarnessTests(unittest.TestCase):
    def test_c1_t1_t2_t3_pass_within_assumptions(self) -> None:
        for check in (check_c1(), check_t1(), check_t2(), check_t3()):
            self.assertEqual(check.execution_state, "PASS_WITHIN_ASSUMPTIONS", check.to_dict())

    def test_t4_does_not_claim_sequential_coverage(self) -> None:
        check = check_t4(n_trials=80, n_samples=30, seed=1)
        self.assertIn(check.execution_state, {"PASS_WITHIN_ASSUMPTIONS", "INCONCLUSIVE", "FAIL_MONTE_CARLO"})
        self.assertEqual(check.metrics["coverage_scope"], "fixed_stage")
        self.assertIn("Sequential coverage is NOT_IMPLEMENTED", check.notes)


class BeliefSeparationTests(unittest.TestCase):
    def test_inference_error_uses_kl_estimated_parallel_ideal(self) -> None:
        estimated = EstimatedBelief({"h1": 0.9, "h2": 0.1})
        ideal = IdealBelief({"h1": 0.6, "h2": 0.4})
        diagnostics = diagnose(estimated, ideal)
        expected = kl_divergence({"h1": 0.9, "h2": 0.1}, {"h1": 0.6, "h2": 0.4})
        self.assertAlmostEqual(diagnostics.inference_error_kl, expected)
        inverted = kl_divergence({"h1": 0.6, "h2": 0.4}, {"h1": 0.9, "h2": 0.1})
        self.assertNotAlmostEqual(diagnostics.inference_error_kl, inverted)


class AnalyzeInvariantTests(unittest.TestCase):
    def test_operators_do_not_change_evidence(self) -> None:
        evidence = ("e1", "e2")
        belief = {"h1": 0.7, "h2": 0.3}
        state = ComputationalState()
        for operator in (NoOpAnalyze(), ConsistencyAnalyze(), MixtureProjectionAnalyze(0.3)):
            kwargs = {"target": {"h1": 0.5, "h2": 0.5}} if isinstance(operator, MixtureProjectionAnalyze) else {}
            result = operator.analyze(state, evidence, belief, **kwargs)
            self.assertEqual(result.evidence_ids, evidence)

    def test_v24_analyze_keeps_evidence_ids(self) -> None:
        before = _policy_state(("doc-a", "doc-b"))
        after = analyze(before, (("h1", 0.4, 0.1), ("h2", 0.1, 0.5)))
        self.assertEqual(after.evidence_ids, before.evidence_ids)
        self.assertNotEqual(after.hypotheses[0].belief_score, before.hypotheses[0].belief_score)


class TerminalActionTests(unittest.TestCase):
    def test_answer_and_defer_have_empty_successors(self) -> None:
        self.assertEqual(LEGAL_TRANSITIONS[EpistemicAction.ANSWER], frozenset())
        self.assertEqual(LEGAL_TRANSITIONS[EpistemicAction.DEFER], frozenset())


class StoppingTests(unittest.TestCase):
    def test_stop_when_all_ucb_nonpositive(self) -> None:
        decision = stop_if_all_ucb_nonpositive(
            {"ANALYZE": -0.1, "EXPLORE": -0.2, "ASK": -0.05},
            {"ANALYZE": -0.2, "EXPLORE": -0.3, "ASK": -0.1},
            alpha=0.05,
            oracle_best_net_voi=0.4,
            delta_positive=0.01,
        )
        self.assertTrue(decision.stop_decision)
        self.assertTrue(decision.false_stop)

    def test_normal_ucb_finite(self) -> None:
        bound = NormalUCB().upper_bound([0.1, 0.2, 0.15], 0.05, 3)
        self.assertTrue(bound > 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
