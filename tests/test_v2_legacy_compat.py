from __future__ import annotations

from pathlib import Path
import unittest

from quasar2.config import ProjectConfig
from quasar2.models.decision import Action
from quasar2.pipeline import VALID_ABLATIONS, QuasarPipeline


class LegacyCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.config = ProjectConfig.load(root / "configs/poc.yaml")
        cls.pipeline = QuasarPipeline.from_config(cls.config)

    def test_legacy_action_space_unchanged(self) -> None:
        self.assertEqual({item.value for item in Action}, {"ANSWER", "EXPLORE", "ASK"})
        self.assertEqual(VALID_ABLATIONS, frozenset({"full", "noHyp", "noExplore", "noUpdate", "noAsk"}))

    def test_poc_config_does_not_enable_shadow_by_default(self) -> None:
        self.assertFalse(self.pipeline.v2_shadow_enabled)

    def test_default_result_has_null_v2_telemetry(self) -> None:
        result = self.pipeline.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        self.assertIsNone(result.v2_telemetry)
        self.assertEqual(result.decision.action.value, "ASK")
        self.assertEqual(result.retrieval_calls, 5)
        self.assertEqual(result.explore_rounds, 1)

    def test_shadow_does_not_change_executed_action(self) -> None:
        shadowed = QuasarPipeline.from_config(self.config)
        shadowed.v2_shadow_enabled = True
        baseline = self.pipeline.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        other = shadowed.run(
            "The starlight keeps dipping when something crosses the disk",
            "astronomy",
        )
        self.assertEqual(baseline.decision.action, other.decision.action)
        self.assertEqual(baseline.predicted_hypothesis_id, other.predicted_hypothesis_id)
        self.assertEqual(baseline.retrieval_calls, other.retrieval_calls)
        self.assertIsNotNone(other.v2_telemetry)
        self.assertEqual(other.v2_telemetry.executed_action_legacy, other.decision.action.value)
        self.assertIsNotNone(other.v2_telemetry.recommended_action_v2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
