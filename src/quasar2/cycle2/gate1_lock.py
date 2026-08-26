"""Lock and reproduce Gate 1 FAIL without retuning DRS on registered_test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quasar2.config import discover_project_root
from quasar2.eval.gate1 import analysis_plan_hash, load_analysis_plan, run_gate1_audit


def frozen_gate1_path() -> Path:
    return discover_project_root() / "experiments" / "results" / "gate1_cycle1" / "gate1.json"


def lock_gate1(*, reproduce: bool = True) -> dict[str, Any]:
    frozen = json.loads(frozen_gate1_path().read_text(encoding="utf-8"))
    plan = load_analysis_plan()
    plan_h = analysis_plan_hash(plan)
    reproduced = None
    if reproduce:
        payload = run_gate1_audit(include_fixture=False)
        gate = (payload.get("synthetic") or {}).get("gate") or payload.get("gate") or {}
        reproduced = {
            "gate1": gate.get("gate1"),
            "reason": gate.get("reason"),
            "analysis_plan_hash": gate.get("analysis_plan_hash") or payload.get("analysis_plan_hash"),
        }
    gate = (
        frozen.get("gate")
        or (frozen.get("synthetic") or {}).get("gate")
        or {}
    )
    frozen_status = frozen.get("gate1") or gate.get("gate1")
    frozen_reason = frozen.get("reason") or gate.get("reason")
    match = True
    if reproduced is not None:
        match = reproduced["gate1"] == "FAIL" and (frozen_status in {None, "FAIL"} or reproduced["gate1"] == frozen_status)
    return {
        "GATE_1_RESULT": "FAIL",
        "locked": True,
        "frozen_status": frozen_status,
        "frozen_reason": frozen_reason,
        "reproduced": reproduced,
        "reproduction_matches_fail": reproduced is None or reproduced["gate1"] == "FAIL",
        "analysis_plan_hash_now": plan_h,
        "do_not_retune_on_registered_test": True,
    }
