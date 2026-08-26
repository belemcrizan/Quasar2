from __future__ import annotations

from dataclasses import asdict
import tempfile
from pathlib import Path
import unittest

from quasar2.evidence.contracts import NeutralEvidenceItem
from quasar2.evidence.envelope import EvidenceEnvelope, envelope_from_neutral
from quasar2.gate.complexity import RetrievalSignals, evaluate_gate
from quasar2.sources.fixtures import jwst_mast_source
from quasar2.sources.registry import builtin_registry
from quasar2.v24.actions import PUBLIC_ACTIONS, EpistemicAction, public_action_label
from quasar2.v24.pipeline import V24Pipeline
from quasar2.v24.policy import decide, legal_actions
from quasar2.v24.state import BudgetState, HypothesisView, PolicyState
from quasar2.wdi.fixture import write_offline_ci_snapshot
from quasar2.wdi.normalize import sha256_bytes, sha256_canonical_text
from quasar2.wdi.source import WDIEvidenceSource
from quasar2.v24.experiment import run_wdi_experiment


class GateTests(unittest.TestCase):
    def test_simple_high_margin_routes_fast(self) -> None:
        decision = evaluate_gate(
            "What was GDP per capita for Brazil in 2022?",
            RetrievalSignals(scores=(0.90, 0.10, 0.05)),
        )
        self.assertEqual(decision.route, "FAST")
        self.assertGreater(decision.margin, 0.12)

    def test_open_set_can_defer_early(self) -> None:
        decision = evaluate_gate("Bitcoin market cap this hour")
        self.assertEqual(decision.route, "DEFER_EARLY")
        self.assertIn("OPEN_SET_RISK", decision.labels)

    def test_ambiguous_margin_routes_quasar(self) -> None:
        decision = evaluate_gate(
            "Tell me about Brazil lately.",
            RetrievalSignals(scores=(0.22, 0.21, 0.20)),
        )
        self.assertEqual(decision.route, "QUASAR")

    def test_gate_is_deterministic(self) -> None:
        signals = RetrievalSignals(scores=(0.4, 0.3, 0.2))
        query = "How rich was Germany in 2018?"
        self.assertEqual(evaluate_gate(query, signals), evaluate_gate(query, signals))

    def test_negative_blank_query_is_not_fast(self) -> None:
        decision = evaluate_gate("ok")
        self.assertNotEqual(decision.route, "FAST")


class EnvelopeAndSourceTests(unittest.TestCase):
    def test_envelope_rejects_unknown_modality(self) -> None:
        with self.assertRaises(ValueError):
            EvidenceEnvelope(
                evidence_id="e",
                source_id="s",
                source_record_id="r",
                source_type="DOCUMENT",
                modality="VIDEO_STREAM",
                content_or_reference=None,
                content_hash="0",
            )

    def test_neutral_adapter_preserves_raw_score(self) -> None:
        item = NeutralEvidenceItem(
            evidence_id="e1",
            source="worldbank_wdi",
            source_snapshot="snap",
            kind="INDICATOR_METADATA",
            payload={"indicator_id": "NY.GDP.PCAP.CD"},
            retrieval_score=0.42,
            content_hash="abc",
        )
        envelope = envelope_from_neutral(asdict(item), modality="TABLE")
        self.assertEqual(envelope.raw_retrieval_score, 0.42)
        self.assertEqual(envelope.adjusted_score, None)

    def test_registry_contains_required_families(self) -> None:
        registry = builtin_registry()
        families = {item.family for item in registry.all()}
        self.assertTrue(
            {
                "WORLD_BANK_WDI",
                "JWST_MAST",
                "JWST_CRDS",
                "NASA_ADS",
                "CERN_OPEN_DATA",
                "INSPIRE_HEP",
            }.issubset(families)
        )

    def test_jwst_cutoff_excludes_future_products(self) -> None:
        source = jwst_mast_source()
        at_t0 = source.filter_by_cutoff("2023-12-31")
        ids = {row["record_id"] for row in at_t0}
        self.assertIn("jwst-obs-001", ids)
        self.assertNotIn("jwst-obs-002", ids)
        later = source.search("WASP-39 NIRSpec", cutoff="2023-12-31")
        self.assertFalse(any(row["record_id"] == "jwst-obs-002" for row in later))

    def test_absence_of_future_record_is_not_evidence_of_absence(self) -> None:
        source = jwst_mast_source()
        missing = [row for row in source.filter_by_cutoff("2023-12-31") if row["record_id"] == "jwst-obs-002"]
        self.assertEqual(missing, [])

    def test_crlf_does_not_change_canonical_hash(self) -> None:
        lf = b'{"a": 1}\n'
        crlf = b'{"a": 1}\r\n'
        self.assertEqual(sha256_canonical_text(lf), sha256_canonical_text(crlf))
        self.assertNotEqual(sha256_bytes(lf), sha256_bytes(crlf))


class ActionAndGatePipelineTests(unittest.TestCase):
    def test_verify_exists_but_is_not_default_legal(self) -> None:
        self.assertIn(EpistemicAction.VERIFY, PUBLIC_ACTIONS)
        self.assertEqual(public_action_label("THINK"), "ANALYZE")
        self.assertEqual(public_action_label("SEARCH"), "EXPLORE")
        hypotheses = (
            HypothesisView("h1", "NY.GDP.PCAP.CD", "BRA", "COUNTRY", "2022", "current_USD", 0.55),
            HypothesisView("h2", "NY.GDP.MKTP.CD", "BRA", "COUNTRY", "2022", "current_USD", 0.33),
            HypothesisView("H_unknown", None, None, None, None, None, 0.12, required_slots=()),
        )
        state = PolicyState(
            query="q",
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
        self.assertNotIn(EpistemicAction.VERIFY, legal_actions(state))
        action, _, scores = decide(state)
        self.assertEqual(len(scores), 5)
        self.assertIn(action, legal_actions(state))

    def test_gated_policy_records_route_and_latency(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "snap"
        write_offline_ci_snapshot(root)
        source = WDIEvidenceSource(root)
        pipeline = V24Pipeline(source, policy="gated_quasar")
        result = pipeline.run("What was Gdp Per Capita for Brazil in 2022?", period_hint="2022")
        self.assertIn(result.gate_route, {"FAST", "QUASAR", "DEFER_EARLY"})
        self.assertGreaterEqual(result.latency_ms, 0.0)
        self.assertGreaterEqual(result.retrieval_calls, 1)
        self.assertGreaterEqual(result.compute_proxy, 1.0)
        tmp.cleanup()

    def test_top1_behavior_unchanged_on_fixture(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "snap"
        write_offline_ci_snapshot(root)
        from quasar2.wdi.source import WDIEvidenceSource

        source = WDIEvidenceSource(root)
        result = V24Pipeline(source, policy="top1").run(
            "What was Gdp Per Capita for Brazil in 2022?", period_hint="2022"
        )
        self.assertEqual(result.final_action, "ANSWER")
        self.assertEqual(result.retrieval_calls, 1)
        tmp.cleanup()

    def test_gate_experiment_smoke_writes_summaries(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "snap"
        write_offline_ci_snapshot(root)
        payload = run_wdi_experiment(
            root,
            stage="ci",
            policies=("fast_only", "quasar_always", "gated_quasar"),
            backends=("bm25",),
            limit=8,
        )
        self.assertIn("bm25|fast_only", payload["summaries"])
        self.assertIn("bm25|quasar_always", payload["summaries"])
        self.assertIn("bm25|gated_quasar", payload["summaries"])
        self.assertEqual(payload["claim_status"]["C1"]["status"], "INCONCLUSIVE")
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
