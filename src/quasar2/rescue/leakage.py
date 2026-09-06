"""Guards that keep ground truth out of deployment-valid paths."""

from __future__ import annotations

from typing import Any, Mapping

FORBIDDEN_DEPLOYMENT_FIELDS = frozenset(
    {
        "correct_hypothesis",
        "gold_doc_ids",
        "evidence_doc_ids",
        "H_star",
        "h_star",
        "intent_label",
        "acceptable_intents",
        "ground_truth",
        "oracle_sufficient",
    }
)


class LeakageError(RuntimeError):
    """Raised when a deployment-valid component reads oracle fields."""


class SealedGold:
    """Object that explodes if any gold attribute is read."""

    def __init__(self, **payload: Any) -> None:
        object.__setattr__(self, "_payload", dict(payload))

    def __getattribute__(self, name: str) -> Any:
        if name in {"_payload", "__class__", "__repr__", "__dict__"}:
            return object.__getattribute__(self, name)
        raise LeakageError(f"deployment-valid path read sealed gold field {name!r}")

    def __getitem__(self, name: str) -> Any:
        raise LeakageError(f"deployment-valid path indexed sealed gold field {name!r}")


def assert_no_gold_fields(record: Mapping[str, Any], *, context: str) -> None:
    overlap = FORBIDDEN_DEPLOYMENT_FIELDS.intersection(record)
    if overlap:
        raise LeakageError(f"{context} contains forbidden fields: {sorted(overlap)}")


def scan_mapping_for_gold(record: Mapping[str, Any]) -> tuple[str, ...]:
    found: list[str] = []
    pending: list[Any] = [record]
    seen: set[int] = set()
    while pending:
        value = pending.pop()
        if not isinstance(value, (Mapping, list, tuple)) or id(value) in seen:
            continue
        seen.add(id(value))
        if isinstance(value, Mapping):
            found.extend(str(key) for key in value if key in FORBIDDEN_DEPLOYMENT_FIELDS)
            pending.extend(value.values())
        else:
            pending.extend(value)
    return tuple(dict.fromkeys(found))
