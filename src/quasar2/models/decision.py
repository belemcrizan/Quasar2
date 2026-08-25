"""Decision action and explicit utility accounting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class Action(str, Enum):
    ANSWER = "ANSWER"
    EXPLORE = "EXPLORE"
    ASK = "ASK"


@dataclass(frozen=True, slots=True)
class Decision:
    action: Action
    selected_hypothesis_id: str | None
    utilities: Mapping[str, float]
    rationale: str
    confidence: float
    margin: float
    expected_information_gain: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "utilities", MappingProxyType(dict(self.utilities)))

