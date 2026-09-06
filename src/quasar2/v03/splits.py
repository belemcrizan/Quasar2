"""Outcome-independent grouping; explicit holdouts are never random row splits."""

import hashlib
from dataclasses import replace


def assign_split(group: str, *, seed: int = 42) -> str:
    bucket = int(hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()[:12], 16) % 100
    return (
        "train"
        if bucket < 60
        else "development"
        if bucket < 75
        else "calibration"
        if bucket < 85
        else "test"
    )


def holdout(cases, *, axis: str, values: set[str]):
    if axis not in {"domain", "entity", "template", "group_id"} or not values:
        raise ValueError("Explicit nonempty holdout axis and values required")
    if any(not getattr(case, axis) for case in cases):
        raise ValueError(f"Missing metadata for {axis} holdout")
    return tuple(
        replace(
            case,
            split="test"
            if getattr(case, axis) in values
            else assign_split(case.group_id)
            if assign_split(case.group_id) != "test"
            else "development",
        )
        for case in cases
    )
