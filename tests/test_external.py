from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from quasar2.external.benchmark import assign_splits, expand_states, freeze_state_for_policy, records_for_source
from quasar2.external.leakage import audit_batch
from quasar2.external.power import n_for_min_effect
from quasar2.external.provenance import deployment_view
from quasar2.external.source_audit import HIGH_PRIORITY, NOT_SUITABLE, SOURCE_AUDIT, selected_sources
from quasar2.external.taxonomy import AMBIGUITY_LABELS


class SourceAuditTests(unittest.TestCase):
    def test_every_row_classified(self) -> None:
        recs = {row["recommendation"] for row in SOURCE_AUDIT}
        self.assertIn(HIGH_PRIORITY, recs)
        self.assertIn(NOT_SUITABLE, recs)
        self.assertGreaterEqual(len(selected_sources()), 3)
        self.assertTrue(any("scrape" in row["source"].lower() or "scraped" in row["rationale"].lower() for row in SOURCE_AUDIT if row["recommendation"] == NOT_SUITABLE))

    def test_prestige_rejected(self) -> None:
        names = " ".join(row["source"] for row in SOURCE_AUDIT if row["recommendation"] == NOT_SUITABLE)
        self.assertIn("Image of the Day", names)


class SnapshotTests(unittest.TestCase):
    def test_synthetic_ids_are_prefixed(self) -> None:
        recs = records_for_source("nasa_exo_schema", n_objects=4)
        self.assertTrue(all(r["source_record_id"].startswith("SYN-") for r in recs))
        self.assertFalse(any(r["live_fetch"] for r in recs))

    def test_jwst_fixture_not_synthetic_prefix(self) -> None:
        recs = records_for_source("jwst_mast_fixture", n_objects=1)
        self.assertTrue(any(r["provenance_kind"] == "OFFICIAL_FIXTURE_METADATA" for r in recs))


class LeakageTests(unittest.TestCase):
    def test_deployment_view_drops_gold(self) -> None:
        states = assign_splits(expand_states(records_for_source("nasa_exo_schema", n_objects=3), degradations=("clean",)))
        dep = freeze_state_for_policy(states[0])
        self.assertNotIn("gold_hypothesis", dep)
        self.assertNotIn("hidden_evidence", dep)
        self.assertNotIn("true_kernels", dep)
        report = audit_batch(states, freeze_state_for_policy)
        self.assertTrue(report["ok"], report["issues"])

    def test_oracle_fields_stripped(self) -> None:
        stripped = deployment_view({"q_obs": "x", "gold_hypothesis": "H1", "true_kernel": {}})
        self.assertEqual(set(stripped), {"q_obs"})


class PowerTests(unittest.TestCase):
    def test_ops12_underpowered(self) -> None:
        plan = n_for_min_effect(min_effect=0.05, sigma=0.35, mean_cluster_size=6.0, icc=0.25)
        self.assertGreater(int(plan["n_rows"]), 12)


class TaxonomyTests(unittest.TestCase):
    def test_labels_include_open_set(self) -> None:
        self.assertIn("open_set", AMBIGUITY_LABELS)
        self.assertIn("non_recoverable_ambiguity", AMBIGUITY_LABELS)


class SmokeRunnerTests(unittest.TestCase):
    def test_external_smoke(self) -> None:
        from quasar2.external.runner import run_external

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ext"
            payload = run_external(dest, seed=0, smoke=True, overwrite=True)
            self.assertEqual(payload["gate1"], "FAIL")
            self.assertFalse(payload["live_official_dump"])
            self.assertIn("A", payload["answers"])
            self.assertTrue((dest / "REPORT.md").exists())
            self.assertNotEqual(payload["answers"]["A"], "")
            for claim in payload["claims"]:
                if claim["claim_id"].startswith("H_"):
                    self.assertNotEqual(claim["status"], "SUPPORTED_IN_SCOPE")


if __name__ == "__main__":
    unittest.main()
