from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from quasar2.observability.http import handle
from quasar2.observability.html import render_cockpit
from quasar2.rescue.leakage import LeakageError, scan_mapping_for_gold
from quasar2.rescue.policy import ActionCatalog, DISABLED_BY_GATE, execute_selected
from quasar2.rescue.recoverability import preaction_features
from quasar2.rescue.trace import build_trace, runtime_only


class ObservabilityTests(unittest.TestCase):
    def test_runtime_trace_rejects_gold(self) -> None:
        with self.assertRaises(LeakageError):
            build_trace(run_id="r", runtime={"correct_hypothesis": "secret"})
        trace = build_trace(
            run_id="r",
            runtime={"query": "q", "selected_action": "ANSWER", "executed_action": "ANSWER"},
            oracle={"correct_hypothesis": "secret"},
        )
        exposed = runtime_only(trace)
        self.assertNotIn("oracle", exposed["trace"])
        self.assertFalse(scan_mapping_for_gold(exposed["trace"]["runtime"]))

    def test_health_and_actions_and_openapi(self) -> None:
        status, headers, body = handle("GET", "/health", b"", "req-1")
        self.assertEqual(status, 200)
        self.assertIn("X-Request-ID", headers)
        self.assertIn(b"ok", body)
        status, _, body = handle("GET", "/v1/actions", b"", "req-2")
        self.assertEqual(status, 200)
        self.assertIn(b"DISABLED_BY_GATE", body)
        self.assertIn(b"VERIFY", body)
        status, _, body = handle("GET", "/v1/openapi.json", b"", "req-3")
        self.assertEqual(status, 200)
        self.assertIn(b"/v1/decide", body)
        status, _, body = handle("GET", "/v1/datasets", b"", "req-4")
        self.assertEqual(status, 200)
        self.assertIn(b"SCHEMA_FAITHFUL", body)
        self.assertNotIn(b"CONFIRMATORY_BENCHMARK", body)

    def test_runtime_endpoints_do_not_embed_oracle_keys(self) -> None:
        _, _, body = handle("GET", "/v1/metrics", b"", "req-5")
        text = body.decode("utf-8")
        self.assertNotIn("gold_doc_ids", text)

    def test_cockpit_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html = render_cockpit(Path(tmp) / "missing")
        self.assertIn("unavailable", html.lower())
        self.assertNotIn("hardcoded rescue = 12", html.lower())

    def test_recoverability_ignores_post_treatment(self) -> None:
        feats = preaction_features(
            {
                "fast_entropy": 0.8,
                "fast_margin": 0.1,
                "evidence_doc_ids": ["gold"],
                "correct_hypothesis": "h*",
            }
        )
        self.assertNotIn("evidence_doc_ids", feats)
        self.assertNotIn("correct_hypothesis", feats)

    def test_verify_disabled_and_not_analyze(self) -> None:
        catalog = ActionCatalog()
        self.assertEqual(catalog.status("VERIFY"), DISABLED_BY_GATE)
        self.assertFalse(catalog.selectable("VERIFY"))
        self.assertTrue(catalog.selectable("ANALYZE"))
        from quasar2.config import ProjectConfig
        from quasar2.rescue.runner import _build_rescue_pipeline

        root = Path(__file__).resolve().parents[1]
        pipeline, _, _, _ = _build_rescue_pipeline(ProjectConfig.load(root / "configs" / "poc.yaml"))
        with self.assertRaises(PermissionError):
            execute_selected(pipeline, "starlight dip", "astronomy", "VERIFY")
        analyzed = execute_selected(pipeline, "starlight dip", "astronomy", "ANALYZE")
        self.assertEqual(analyzed["selected_action"], "ANALYZE")
        self.assertEqual(analyzed["executed_action"], "ANALYZE")
        self.assertTrue(analyzed["evidence_frozen"])
        self.assertEqual(analyzed["retrieval_delta"], 0)

    def test_selected_action_is_executed(self) -> None:
        from quasar2.config import ProjectConfig
        from quasar2.rescue.runner import _build_rescue_pipeline

        root = Path(__file__).resolve().parents[1]
        pipeline, _, _, _ = _build_rescue_pipeline(ProjectConfig.load(root / "configs" / "poc.yaml"))
        for action in ("ANSWER", "BM25", "DISCRIMINATIVE"):
            out = execute_selected(pipeline, "starlight dip", "astronomy", action)
            self.assertEqual(out["selected_action"], out["executed_action"])
            self.assertEqual(out["selected_action"], action)

    def test_cli_aliases_exist(self) -> None:
        from quasar2.cli import build_parser

        choices = build_parser()._subparsers._group_actions[0].choices
        for name in (
            "rescue-experiment",
            "policy-evaluate",
            "serve",
            "dashboard",
            "compare-runs",
            "load-test",
            "external-sync",
            "external-validate",
            "external-benchmark",
        ):
            self.assertIn(name, choices)


class LoadTestUnit(unittest.TestCase):
    def test_unreachable_host_records_errors(self) -> None:
        from quasar2.observability.loadtest import run_load_test

        payload = run_load_test("http://127.0.0.1:1", concurrency=1, n=2, path="/health")
        self.assertEqual(payload["n"], 2)
        self.assertGreater(payload["errors"], 0)


if __name__ == "__main__":
    unittest.main()
