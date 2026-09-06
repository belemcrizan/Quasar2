import unittest
from copy import deepcopy

from quasar2.rescue.leakage import LeakageError
from quasar2.rescue.trace import build_trace, runtime_only
from quasar2.v24.state import BudgetState, _reject_hidden
from quasar2.wdi.evaluator import evaluate_answer


class RuntimeBoundaries(unittest.TestCase):
    def test_nested_gold_is_rejected_inside_arrays(self):
        payload = {"events": [{"payload": ({"acceptable_intents": []},)}]}
        with self.assertRaises(ValueError):
            _reject_hidden(payload)
        with self.assertRaises(LeakageError):
            build_trace(run_id="r", runtime=payload)
        with self.assertRaises(LeakageError):
            runtime_only({"trace": {"runtime": payload}})

    def test_negative_charges_cannot_increase_budget(self):
        budget = BudgetState()
        for field in ("steps", "analyze", "explore", "ask", "retrieval", "cost"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                budget.charge(**{field: -1})

    def test_invalid_budget_construction_and_charges(self):
        for kwargs in (
            {"remaining_steps": -1},
            {"remaining_steps": True},
            {"remaining_steps": 1.5},
            {"used_cost": float("nan")},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                BudgetState(**kwargs)
        for kwargs in ({"cost": float("inf")}, {"steps": 0.5}, {"steps": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                BudgetState().charge(**kwargs)

    def test_valid_charge_preserves_original(self):
        original = BudgetState()
        updated = original.charge(steps=1, cost=0.1)
        self.assertEqual(updated.remaining_steps, original.remaining_steps - 1)
        self.assertEqual(original.used_cost, 0)


class WdiEvaluationIntegrity(unittest.TestCase):
    def setUp(self):
        self.intent = {
            "indicator_id": "GDP",
            "entity_code": "BRA",
            "entity_type": "COUNTRY",
            "period": "2022",
            "unit": "USD",
        }
        self.truth = {
            "acceptable_intents": [self.intent],
            "expected_observation": {"status": "OBSERVED", "value": 1.0, "period": "2022"},
        }
        self.prediction = {
            **self.intent,
            "observation_status": "OBSERVED",
            "value": 1.0,
            "final_action": "ANSWER",
        }

    def test_fields_cannot_match_different_acceptable_intents(self):
        self.truth["acceptable_intents"].append(
            {**self.intent, "indicator_id": "POP", "entity_code": "USA"}
        )
        result = evaluate_answer({**self.prediction, "entity_code": "USA"}, self.truth)
        self.assertFalse(result.intent_exact)
        self.assertTrue(result.committed_wrong)

    def test_wrong_unit_and_entity_type_are_not_correct_answers(self):
        for changes in ({"unit": "percent"}, {"entity_type": "REGION"}):
            with self.subTest(changes=changes):
                result = evaluate_answer({**self.prediction, **changes}, self.truth)
                self.assertFalse(result.intent_exact)
                self.assertTrue(result.committed_wrong)

    def test_latest_year_is_checked_against_truth(self):
        self.truth["acceptable_intents"] = [{**self.intent, "period": "latest"}]
        wrong = {**self.prediction, "period": "2018", "disclosed_period": "2018"}
        self.assertTrue(evaluate_answer(wrong, self.truth).committed_wrong)
        correct = {**self.prediction, "disclosed_period": "2022"}
        self.assertFalse(evaluate_answer(correct, self.truth).committed_wrong)

    def test_zero_tolerance_is_respected(self):
        self.truth["expected_observation"]["relative_tolerance"] = 0
        self.assertTrue(
            evaluate_answer({**self.prediction, "value": 1.0000001}, self.truth).committed_wrong
        )

    def test_observed_truth_requires_finite_value(self):
        self.truth["expected_observation"]["value"] = None
        with self.assertRaises(ValueError):
            evaluate_answer({**self.prediction, "value": None}, self.truth)

    def test_boolean_is_not_a_numeric_prediction(self):
        self.assertTrue(
            evaluate_answer({**self.prediction, "value": True}, self.truth).committed_wrong
        )

    def test_missing_status_cannot_hide_fabricated_value(self):
        self.truth["expected_observation"] = {"status": "NOT_AVAILABLE", "value": None}
        fabricated = {**self.prediction, "observation_status": "NOT_AVAILABLE", "value": 999}
        self.assertTrue(evaluate_answer(fabricated, self.truth).committed_wrong)
        legitimate = {**fabricated, "value": None}
        self.assertFalse(evaluate_answer(legitimate, self.truth).committed_wrong)

    def test_valid_answer_and_inputs_preserved(self):
        before = deepcopy(self.truth)
        result = evaluate_answer(self.prediction, self.truth)
        self.assertTrue(result.intent_exact)
        self.assertFalse(result.committed_wrong)
        self.assertEqual(self.truth, before)


class WdiUnitProvenance(unittest.TestCase):
    def test_empty_unit_uses_public_indicator_catalog(self):
        from quasar2.wdi.source import indicator_document

        document = indicator_document({"indicator_id": "NY.GDP.PCAP.CD", "unit": ""})
        self.assertEqual(document.metadata["unit"], "current_USD")
        self.assertEqual(document.metadata["unit_source"], "indicator_catalog")
        explicit = indicator_document({"indicator_id": "NY.GDP.PCAP.CD", "unit": "source-unit"})
        self.assertEqual(explicit.metadata["unit"], "source-unit")
        self.assertEqual(explicit.metadata["unit_source"], "snapshot")

    def test_fetch_does_not_relabel_values_with_requested_units(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from quasar2.evidence.contracts import FetchRequest
        from quasar2.wdi.fixture import write_offline_ci_snapshot
        from quasar2.wdi.source import WDIEvidenceSource

        with TemporaryDirectory() as tmp:
            write_offline_ci_snapshot(Path(tmp))
            source = WDIEvidenceSource(tmp)
            with self.assertRaises(ValueError):
                source.fetch(FetchRequest("NY.GDP.PCAP.CD", "BRA", "2022", unit="percent"))
            payload = source.fetch(FetchRequest("NY.GDP.PCAP.CD", "BRA", "2022"))[0].payload
            self.assertEqual(payload["unit"], "current_USD")
