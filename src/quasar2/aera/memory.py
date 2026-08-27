"""Epistemic experience memory with train/eval isolation and TTL."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


FORBIDDEN_KEYS = frozenset({"correct_hypothesis", "gold_doc_ids", "evidence_doc_ids", "H_star"})


@dataclass
class MemoryRecord:
    domain: str
    state_key: str
    action: str
    outcome_delta_u: float
    cost: float
    ts: float
    split: str


@dataclass
class EpistemicMemory:
    ttl_seconds: float = 86400.0 * 30
    train: list[MemoryRecord] = field(default_factory=list)
    evaluation: list[MemoryRecord] = field(default_factory=list)

    def remember(self, record: MemoryRecord) -> None:
        payload = {
            "domain": record.domain,
            "state_key": record.state_key,
            "action": record.action,
        }
        if FORBIDDEN_KEYS.intersection(payload):
            raise ValueError("memory refused gold fields")
        if record.split == "evaluation":
            self.evaluation.append(record)
        else:
            self.train.append(record)

    def _live(self, rows: list[MemoryRecord], now: float) -> list[MemoryRecord]:
        return [row for row in rows if now - row.ts <= self.ttl_seconds]

    def action_value(self, *, domain: str, action: str, now: float | None = None) -> float | None:
        now = now if now is not None else time.time()
        rows = [
            row
            for row in self._live(self.train, now)
            if row.domain == domain and row.action == action
        ]
        if not rows:
            return None
        return sum(row.outcome_delta_u - row.cost for row in rows) / len(rows)

    def contaminates_eval(self) -> bool:
        train_keys = {(row.domain, row.state_key) for row in self.train}
        eval_keys = {(row.domain, row.state_key) for row in self.evaluation}
        return bool(train_keys.intersection(eval_keys))


def memory_gain(with_memory: float, without_memory: float) -> dict[str, Any]:
    return {
        "with_memory": with_memory,
        "without_memory": without_memory,
        "delta": with_memory - without_memory,
        "helps": with_memory > without_memory,
    }
