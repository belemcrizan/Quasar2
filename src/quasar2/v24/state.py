"""Policy-facing state. Hidden benchmark fields are rejected on construction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping  # Mapping used by _reject_hidden

from quasar2.v24.actions import FORBIDDEN_POLICY_FIELDS


def _reject_hidden(payload: Mapping[str, Any]) -> None:
    pending: list[Any] = [payload]
    seen: set[int] = set()
    while pending:
        value = pending.pop()
        if not isinstance(value, (Mapping, list, tuple)) or id(value) in seen:
            continue
        seen.add(id(value))
        if isinstance(value, Mapping):
            forbidden = sorted(set(value) & FORBIDDEN_POLICY_FIELDS)
            if forbidden:
                raise ValueError(f"Policy state contains forbidden fields: {forbidden}")
            pending.extend(value.values())
        else:
            pending.extend(value)


def _validate_budget(counts: tuple[int, ...], cost: float) -> None:
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in counts):
        raise ValueError("Budget counts must be non-negative integers")
    if isinstance(cost, bool) or not math.isfinite(cost) or cost < 0:
        raise ValueError("Budget cost must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class BudgetState:
    remaining_steps: int = 6
    remaining_analyze: int = 1
    remaining_explore: int = 2
    remaining_ask: int = 1
    remaining_retrieval_calls: int = 12
    used_cost: float = 0.0

    def __post_init__(self) -> None:
        _validate_budget(
            (
                self.remaining_steps,
                self.remaining_analyze,
                self.remaining_explore,
                self.remaining_ask,
                self.remaining_retrieval_calls,
            ),
            self.used_cost,
        )

    def charge(
        self,
        *,
        steps: int = 0,
        analyze: int = 0,
        explore: int = 0,
        ask: int = 0,
        retrieval: int = 0,
        cost: float = 0.0,
    ) -> "BudgetState":
        _validate_budget((steps, analyze, explore, ask, retrieval), cost)
        nxt = BudgetState(
            remaining_steps=self.remaining_steps - steps,
            remaining_analyze=self.remaining_analyze - analyze,
            remaining_explore=self.remaining_explore - explore,
            remaining_ask=self.remaining_ask - ask,
            remaining_retrieval_calls=self.remaining_retrieval_calls - retrieval,
            used_cost=self.used_cost + cost,
        )
        if (
            min(
                nxt.remaining_steps,
                nxt.remaining_analyze,
                nxt.remaining_explore,
                nxt.remaining_ask,
                nxt.remaining_retrieval_calls,
            )
            < 0
        ):
            raise ValueError("Budget would become negative")
        if nxt.used_cost < self.used_cost:
            raise ValueError("Used cost must be non-decreasing")
        return nxt


@dataclass(frozen=True, slots=True)
class HypothesisView:
    hypothesis_id: str
    indicator_id: str | None
    entity_code: str | None
    entity_type: str | None
    period: str | None
    unit: str | None
    belief_score: float
    required_slots: tuple[str, ...] = ("indicator_id", "entity_code", "period")
    status: str = "ACTIVE"


@dataclass(frozen=True, slots=True)
class PolicyState:
    query: str
    language: str
    hypotheses: tuple[HypothesisView, ...]
    evidence_ids: tuple[str, ...]
    entropy: float
    margin: float
    unknown_score: float
    coverage: float
    contradiction: float
    source_available: bool
    budget: BudgetState
    analyzed_versions: tuple[str, ...] = ()
    history: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _reject_hidden(asdict(self))

    def state_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_policy_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        _reject_hidden(payload)
        return payload
