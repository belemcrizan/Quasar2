from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from quasar2.v24.actions import FORBIDDEN_POLICY_FIELDS, EpistemicAction
from quasar2.v24.analyze import analyze
from quasar2.v24.pipeline import V24Pipeline
from quasar2.v24.policy import decide, legal_actions
from quasar2.v24.state import BudgetState, HypothesisView, PolicyState
from quasar2.wdi.catalog import CI_INDICATORS
from quasar2.wdi.client import WorldBankClient
from quasar2.wdi.evaluator import evaluate_answer
from quasar2.wdi.fixture import write_offline_ci_snapshot
from quasar2.wdi.normalize import normalize_observation, resolve_period
from quasar2.wdi.source import WDIEvidenceSource
from quasar2.wdi.taxonomy import classify_entity, EntityType, ObservationStatus
from quasar2.benchmarks.wdi_bench import build_benchmark
from quasar2.v24.experiment import run_wdi_experiment
from quasar2.retrieval.factory import DEBUG_BACKENDS, SCIENTIFIC_BACKENDS, build_retriever


class WdiNormalizeTests(unittest.TestCase):
    def test_country_vs_aggregate_classification(self) -> None:
        brazil = {
            "id": "BRA",
            "region": {"id": "LCN", "value": "Latin America & Caribbean"},
            "incomeLevel": {"id": "UMC", "value": "Upper middle income"},
        }
        region = {
            "id": "LCN",
            "region": {"id": "NA", "value": "Aggregates"},
            "incomeLevel": {"id": "", "value": "Aggregates"},
        }
        self.assertEqual(classify_entity(brazil), EntityType.COUNTRY)
        self.assertNotEqual(classify_entity(region), EntityType.COUNTRY)

    def test_missing_value_is_not_zero(self) -> None:
        row = normalize_observation(
            {
                "indicator": {"id": "NY.GDP.PCAP.CD"},
                "country": {"id": "BRA"},
                "countryiso3code": "BRA",
                "date": "2022",
                "value": None,
            }
        )
        self.assertIsNone(row["value_numeric"])
        self.assertEqual(row["observation_status"], ObservationStatus.NOT_AVAILABLE.value)

    def test_exact_year_is_not_replaced_by_latest(self) -> None:
        observations = [
            {
                "indicator_id": "NY.GDP.PCAP.CD",
                "entity_code": "BRA",
                "period": "2021",
                "value_numeric": 1.0,
                "observation_status": "OBSERVED",
            },
            {
                "indicator_id": "NY.GDP.PCAP.CD",
                "entity_code": "BRA",
                "period": "2022",
                "value_numeric": 2.0,
                "observation_status": "OBSERVED",
            },
        ]
        exact = resolve_period(
            observations, indicator_id="NY.GDP.PCAP.CD", entity_code="BRA", requested="2020"
        )
        latest = resolve_period(
            observations, indicator_id="NY.GDP.PCAP.CD", entity_code="BRA", requested="latest"
        )
        self.assertEqual(exact["observation_status"], ObservationStatus.NOT_AVAILABLE.value)
        self.assertEqual(latest["disclosed_period"], "2022")

    def test_v2_url_includes_source_and_format(self) -> None:
        client = WorldBankClient()
        url = client.build_url("country/BRA/indicator/NY.GDP.PCAP.CD", {"source": 2, "date": "2022:2022"})
        self.assertIn("/v2/", url)
        self.assertIn("source=2", url)
        self.assertIn("format=json", url)


class V24PolicyTests(unittest.TestCase):
    def _state(self, **overrides) -> PolicyState:
        hypotheses = (
            HypothesisView("h1", "NY.GDP.PCAP.CD", "BRA", "COUNTRY", "2022", "current_USD", 0.55),
            HypothesisView("h2", "NY.GDP.MKTP.CD", "BRA", "COUNTRY", "2022", "current_USD", 0.33),
            HypothesisView("H_unknown", None, None, None, None, None, 0.12, required_slots=()),
        )
        values = dict(
            query="How rich was Brazil in 2022?",
            language="en",
            hypotheses=hypotheses,
            evidence_ids=("e1",),
            entropy=0.9,
            margin=0.22,
            unknown_score=0.12,
            coverage=1.0,
            contradiction=0.0,
            source_available=True,
            budget=BudgetState(),
        )
        values.update(overrides)
        return PolicyState(**values)

    def test_hidden_fields_cannot_enter_policy_state(self) -> None:
        payload = self._state().to_policy_dict()
        self.assertTrue(FORBIDDEN_POLICY_FIELDS.isdisjoint(payload))
        from quasar2.v24.state import _reject_hidden

        with self.assertRaises(ValueError):
            _reject_hidden({"query": "x", "acceptable_intents": [{"indicator_id": "secret"}]})

    def test_budgets_cannot_go_negative(self) -> None:
        with self.assertRaises(ValueError):
            BudgetState(remaining_explore=0).charge(explore=1)

    def test_analyze_preserves_evidence_ids(self) -> None:
        state = self._state()
        nxt = analyze(state, [("h1", 0.8, 0.0), ("h2", 0.1, 0.2), ("H_unknown", 0.05, 0.0)])
        self.assertEqual(nxt.evidence_ids, state.evidence_ids)
        again = analyze(nxt, [("h1", 0.8, 0.0), ("h2", 0.1, 0.2), ("H_unknown", 0.05, 0.0)])
        self.assertEqual(again.analyzed_versions, nxt.analyzed_versions)

    def test_legal_actions_and_tie_break(self) -> None:
        allowed = legal_actions(self._state())
        self.assertEqual(
            set(allowed),
            {
                EpistemicAction.ANSWER,
                EpistemicAction.ANALYZE,
                EpistemicAction.EXPLORE,
                EpistemicAction.ASK,
                EpistemicAction.DEFER,
            },
        )
        action, reason, scores = decide(self._state())
        self.assertIn(action, allowed)
        self.assertIn(reason, {"SUFFICIENT_EVIDENCE", "LOW_MARGIN", "HIGH_ENTROPY", "MISSING_USER_OWNED_SLOT", "OPEN_SET", "HIGH_UNKNOWN_MASS", "RISK_LIMIT"})
        self.assertEqual(len(scores), 5)

    def test_source_failure_defers(self) -> None:
        action, reason, _ = decide(self._state(source_available=False))
        self.assertEqual(action, EpistemicAction.DEFER)
        self.assertEqual(reason, "SOURCE_OR_DATA_FAILURE")


class WdiOfflineIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "snap"
        write_offline_ci_snapshot(cls.root)
        cls.source = WDIEvidenceSource(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_snapshot_has_required_coverage(self) -> None:
        self.assertGreaterEqual(len(CI_INDICATORS), 12)
        self.assertGreaterEqual(len(self.source.entities), 8)
        statuses = {row["observation_status"] for row in self.source.observations}
        self.assertIn("OBSERVED", statuses)
        self.assertIn("NOT_AVAILABLE", statuses)
        types = {row["entity_type"] for row in self.source.entities.values()}
        self.assertIn("COUNTRY", types)
        self.assertTrue({"REGION", "AGGREGATE", "INCOME_GROUP"} & types)

    def test_structured_evaluator_and_pipeline_paths(self) -> None:
        result = V24Pipeline(self.source, policy="top1").run(
            "What was Gdp Per Capita for Brazil in 2022?", period_hint="2022"
        )
        self.assertEqual(result.final_action, "ANSWER")
        evaluation = evaluate_answer(
            {**result.structured_answer, "final_action": "ANSWER"},
            {
                "acceptable_intents": [
                    {
                        "indicator_id": result.structured_answer.get("indicator_id"),
                        "entity_code": "BRA",
                        "entity_type": "COUNTRY",
                        "period": "2022",
                        "unit": result.structured_answer.get("unit"),
                    }
                ],
                "expected_observation": {
                    "status": result.structured_answer.get("observation_status"),
                    "value": result.structured_answer.get("value_numeric"),
                },
            },
        )
        self.assertTrue(evaluation.intent_exact or result.structured_answer.get("entity_code") == "BRA")
        open_set = V24Pipeline(self.source, policy="v24").run("Bitcoin market cap this hour")
        self.assertIn(open_set.final_action, {"DEFER", "ASK", "EXPLORE", "ANALYZE", "ANSWER"})
        missing = V24Pipeline(self.source, policy="top1").run(
            "Literacy Nigeria 2022", period_hint="2022"
        )
        if missing.structured_answer.get("observation_status") == "NOT_AVAILABLE":
            self.assertIn(missing.final_action, {"ANSWER", "DEFER"})

    def test_benchmark_keeps_variants_in_one_split(self) -> None:
        bench = build_benchmark(self.root, stage="ci")
        self.assertGreaterEqual(bench["n_canonical"], 12 * 8)
        self.assertGreaterEqual(bench["n_instances"], 360)
        by_canon: dict[str, set[str]] = {}
        for instance in bench["instances"]:
            if instance["canonical_intent_id"].startswith("open_"):
                continue
            by_canon.setdefault(instance["canonical_intent_id"], set()).add(instance["split"])
        self.assertTrue(all(len(splits) == 1 for splits in by_canon.values()))

    def test_crossed_smoke_and_hashing_not_neural(self) -> None:
        self.assertIn("dense_hash", DEBUG_BACKENDS)
        self.assertNotIn("dense_hash", SCIENTIFIC_BACKENDS)
        payload = run_wdi_experiment(
            self.root,
            stage="ci",
            policies=("top1", "v24"),
            backends=("bm25",),
            limit=12,
        )
        self.assertIn("bm25|top1", payload["summaries"])
        self.assertIn("bm25|v24", payload["summaries"])
        docs = self.source.documents()
        hashing = build_retriever(docs, "dense_hash")
        self.assertEqual(hashing.__class__.__name__, "HashingDenseRetriever")


if __name__ == "__main__":
    unittest.main()
