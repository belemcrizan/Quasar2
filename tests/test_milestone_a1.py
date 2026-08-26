from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from quasar2.analysis.a1 import run_a1
from quasar2.analysis.decomposition import decompose_pair, feature_associations, propose_backend_gate, summarize_rows
from quasar2.analysis.io_util import write_csv, write_json
from quasar2.analysis.matching import match_fast_quasar
from quasar2.failures.taxonomy import FOUR_WAY, four_way_class
from quasar2.wdi.normalize import sha256_bytes, sha256_canonical_text


def _row(
    *,
    backend: str,
    policy: str,
    query_id: str,
    correct: bool,
    split: str = "calibration",
    canonical: str = "fam1",
    complexity: float = 0.2,
    ambiguity: float = 0.3,
    unknown: float = 0.1,
    action: str = "ANSWER",
) -> dict:
    return {
        "backend": backend,
        "policy": policy,
        "query_id": query_id,
        "canonical_intent_id": canonical,
        "split": split,
        "action": action,
        "reason_code": "SUFFICIENT_EVIDENCE",
        "intent_exact": correct,
        "committed_wrong": not correct and action == "ANSWER",
        "retrieval_calls": 1 if policy in {"fast_only", "top1"} else 3,
        "unknown_score": unknown,
        "complexity_score": complexity,
        "ambiguity_score": ambiguity,
        "open_set_score": 0.0,
        "latency_ms": 1.0,
        "compute_proxy": 1.1 if policy in {"fast_only", "top1"} else 3.5,
        "gate_route": "FAST",
        "domain": "wdi",
        "language": "en",
        "recoverability": "CLEAR",
        "task_type": "NUMERIC_LOOKUP",
    }


def _write_run(root: Path, records: list[dict], snapshot: str, summaries: dict | None = None) -> Path:
    write_csv(root / "per_query_results.csv", records, list(records[0].keys()) if records else ["query_id"])
    write_json(
        root / "metrics.json",
        {
            "snapshot_id": snapshot,
            "stage": "test",
            "benchmark_hash": "hash-" + snapshot,
            "n_instances": len({row["query_id"] for row in records}) if records else 0,
            "summaries": summaries or {},
            "methods": {
                "backends": sorted({row["backend"] for row in records}),
                "policies": sorted({row["policy"] for row in records}),
            },
        },
    )
    return root


class FourWayTests(unittest.TestCase):
    def test_four_way_labels(self) -> None:
        self.assertEqual(four_way_class(True, True).label, "BOTH_CORRECT")
        self.assertEqual(four_way_class(True, False).label, "OVERTHINKING")
        self.assertEqual(four_way_class(False, True).label, "RESCUE")
        self.assertEqual(four_way_class(False, False).label, "BOTH_WRONG")

    def test_counts_exclusive_and_exhaustive(self) -> None:
        pairs = [
            {"fast": _row(backend="bm25", policy="fast_only", query_id="q1", correct=True),
             "quasar": _row(backend="bm25", policy="quasar_always", query_id="q1", correct=True),
             "backend": "bm25", "query_id": "q1", "instance": {"split": "calibration", "canonical_intent_id": "f"}},
            {"fast": _row(backend="bm25", policy="fast_only", query_id="q2", correct=True),
             "quasar": _row(backend="bm25", policy="quasar_always", query_id="q2", correct=False),
             "backend": "bm25", "query_id": "q2", "instance": {"split": "calibration", "canonical_intent_id": "f"}},
            {"fast": _row(backend="bm25", policy="fast_only", query_id="q3", correct=False),
             "quasar": _row(backend="bm25", policy="quasar_always", query_id="q3", correct=True),
             "backend": "bm25", "query_id": "q3", "instance": {"split": "calibration", "canonical_intent_id": "f"}},
            {"fast": _row(backend="bm25", policy="fast_only", query_id="q4", correct=False),
             "quasar": _row(backend="bm25", policy="quasar_always", query_id="q4", correct=False),
             "backend": "bm25", "query_id": "q4", "instance": {"split": "calibration", "canonical_intent_id": "f"}},
        ]
        rows = [decompose_pair(pair) for pair in pairs]
        summary = summarize_rows(rows)
        self.assertEqual(sum(summary["counts"].values()), 4)
        self.assertEqual(set(summary["counts"]), set(FOUR_WAY))
        self.assertEqual(summary["counts"]["BOTH_CORRECT"], 1)
        self.assertEqual(summary["counts"]["OVERTHINKING"], 1)
        self.assertEqual(summary["counts"]["RESCUE"], 1)
        self.assertEqual(summary["counts"]["BOTH_WRONG"], 1)


class MatchingTests(unittest.TestCase):
    def test_zero_rows(self) -> None:
        result = match_fast_quasar([{"records": [], "snapshot_id": "s", "run_dir": "x"}])
        self.assertEqual(result["matched"], [])
        self.assertEqual(result["unmatched"], [])

    def test_one_sided_missing(self) -> None:
        records = [_row(backend="bm25", policy="fast_only", query_id="q1", correct=True)]
        result = match_fast_quasar([{"records": records, "snapshot_id": "s", "run_dir": "x"}])
        self.assertEqual(result["matched"], [])
        self.assertEqual(result["unmatched"][0]["reason"], "MISSING_QUASAR")

    def test_duplicate_query_id(self) -> None:
        records = [
            _row(backend="bm25", policy="fast_only", query_id="q1", correct=True),
            _row(backend="bm25", policy="fast_only", query_id="q1", correct=False),
            _row(backend="bm25", policy="quasar_always", query_id="q1", correct=True),
        ]
        result = match_fast_quasar([{"records": records, "snapshot_id": "s", "run_dir": "x"}])
        reasons = {item["reason"] for item in result["unmatched"]}
        self.assertIn("DUPLICATE_QUERY_ID", reasons)

    def test_snapshot_mismatch(self) -> None:
        fast = [_row(backend="bm25", policy="fast_only", query_id="q1", correct=True)]
        quasar = [_row(backend="bm25", policy="quasar_always", query_id="q1", correct=True)]
        result = match_fast_quasar(
            [
                {"records": fast, "snapshot_id": "snap-a", "run_dir": "a", "benchmark_hash": "h1"},
                {"records": quasar, "snapshot_id": "snap-b", "run_dir": "b", "benchmark_hash": "h2"},
            ]
        )
        reasons = {item["reason"] for item in result["unmatched"]}
        self.assertIn("SNAPSHOT_MISMATCH", reasons)
        self.assertEqual(result["matched"], [])

    def test_backend_mismatch_is_visible(self) -> None:
        records = [
            _row(backend="bm25", policy="fast_only", query_id="q1", correct=True),
            _row(backend="neural", policy="quasar_always", query_id="q1", correct=True),
        ]
        result = match_fast_quasar([{"records": records, "snapshot_id": "s", "run_dir": "x"}])
        reasons = {item["reason"] for item in result["unmatched"]}
        self.assertEqual(result["matched"], [])
        self.assertIn("MISSING_QUASAR", reasons)
        self.assertIn("MISSING_FAST", reasons)


class A1ArtifactTests(unittest.TestCase):
    def _tiny(self) -> tuple[Path, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        run = Path(tmp.name) / "run"
        run.mkdir()
        records = [
            _row(backend="bm25", policy="fast_only", query_id="q1", correct=True, split="calibration", complexity=0.1),
            _row(backend="bm25", policy="quasar_always", query_id="q1", correct=True, split="calibration"),
            _row(backend="bm25", policy="fast_only", query_id="q2", correct=True, split="calibration", complexity=0.15),
            _row(backend="bm25", policy="quasar_always", query_id="q2", correct=False, split="calibration"),
            _row(backend="bm25", policy="fast_only", query_id="q3", correct=False, split="development", complexity=0.8, ambiguity=0.9),
            _row(backend="bm25", policy="quasar_always", query_id="q3", correct=True, split="development"),
            _row(backend="bm25", policy="fast_only", query_id="q4", correct=False, split="sealed_test", complexity=0.99, ambiguity=0.99),
            _row(backend="bm25", policy="quasar_always", query_id="q4", correct=True, split="sealed_test"),
            _row(backend="neural", policy="top1", query_id="q1", correct=False, split="calibration"),
            _row(backend="neural", policy="v24", query_id="q1", correct=True, split="calibration"),
        ]
        summaries = {
            "bm25|fast_only": {"intent_exact": 0.5},
            "bm25|quasar_always": {"intent_exact": 0.75},
            "neural|top1": {"intent_exact": 0.0},
            "neural|v24": {"intent_exact": 1.0},
        }
        _write_run(run, records, "snap-test", summaries)
        out = Path(tmp.name) / "out"
        return run, out

    def test_writes_required_artifacts_and_reconciles(self) -> None:
        run, out = self._tiny()
        payload = run_a1([run], output_dir=out, repo_root=Path.cwd())
        for name in (
            "per_query_decomposition.csv",
            "metrics.json",
            "feature_analysis.csv",
            "rescue_overthinking_report.md",
            "manifest.json",
            "validation_report.json",
            "unmatched_queries.csv",
            "data_dictionary.md",
            "split_manifest.json",
            "repository_state_manifest.json",
        ):
            self.assertTrue((out / name).exists(), name)
        self.assertEqual(payload["metrics"]["n_matched"], 5)
        self.assertEqual(payload["validation"]["reconciliation_issues"], [])
        rates = payload["metrics"]["rates"]["bm25|ALL"]
        self.assertAlmostEqual(rates["OverthinkingRate"], 0.25)
        self.assertAlmostEqual(rates["RescueRate"], 0.5)
        proposal = propose_backend_gate(payload["rows"])
        self.assertEqual(proposal["bm25|snap-test"]["do_not_fit_on"], ["sealed_test"])
        self.assertEqual(proposal["bm25|snap-test"]["n_calibration"], 2)
        self.assertEqual(proposal["bm25|snap-test"]["n_rescue"], 0)
        self.assertTrue(all(not row["used_sealed_test"] for row in feature_associations(payload["rows"])))
        sealed = [row for row in payload["rows"] if row["split"] == "sealed_test"]
        self.assertEqual(len(sealed), 1)
        self.assertFalse(sealed[0]["used_for_feature_ranking"])
        self.assertFalse(sealed[0]["used_for_threshold_proposal"])
        self.assertEqual(payload["metrics"]["claim_status"], "EXPLORATORY")

    def test_deterministic_and_lf_hash(self) -> None:
        run, out = self._tiny()
        first = run_a1([run], output_dir=out / "a", repo_root=Path.cwd())
        second = run_a1([run], output_dir=out / "b", repo_root=Path.cwd())
        self.assertEqual(first["manifest"]["per_query_sha256_canonical"], second["manifest"]["per_query_sha256_canonical"])
        raw = (out / "a" / "per_query_decomposition.csv").read_bytes()
        crlf = raw.replace(b"\n", b"\r\n")
        self.assertEqual(sha256_canonical_text(raw), sha256_canonical_text(crlf))
        self.assertNotEqual(sha256_bytes(raw), sha256_bytes(crlf))
        self.assertNotIn(b"\r\n", raw)


if __name__ == "__main__":
    unittest.main()
