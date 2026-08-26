"""External validity, scale, replication, and regime discovery (Cycle 3).

Does not replace the frozen v0.1.1 loop, Gate 1 FAIL, or Cycle 2 artifacts.
Policy remains shadow / not promoted. Negative results stay visible.
"""

from __future__ import annotations

CYCLE_ID = "C3"
SCHEMA_VERSION = "external.1"
PROGRAM = "EXTERNAL_VALIDITY_SCALE_REPLICATION_REGIME"
POLICY_STAGE = "SHADOW"
GATE1_LOCKED = "FAIL"

REGISTERED_HYPOTHESES = (
    "H_EXT",
    "H_DOMAIN",
    "H_SCALE",
    "H_BUDGET",
    "H_REGIME",
    "H_MISMATCH",
    "H_REPLICATION",
)
