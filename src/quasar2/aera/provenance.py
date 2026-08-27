"""Epistemic provenance graph. Gate: must change score, dedup, or audit — not decoration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


EDGE_TYPES = (
    "supports",
    "contradicts",
    "falsifies",
    "derived_from",
    "duplicates",
    "cites",
    "independently_confirms",
    "temporally_supersedes",
)


@dataclass
class ProvenanceGraph:
    nodes: dict[str, dict[str, str]] = field(default_factory=dict)
    edges: list[tuple[str, str, str]] = field(default_factory=list)

    def add_node(self, node_id: str, kind: str, label: str = "") -> None:
        self.nodes[node_id] = {"kind": kind, "label": label or node_id}

    def add_edge(self, src: str, dst: str, kind: str) -> None:
        if kind not in EDGE_TYPES:
            raise ValueError(f"unknown edge {kind}")
        self.edges.append((src, dst, kind))

    def duplicates_of(self, node_id: str) -> set[str]:
        found = {node_id}
        changed = True
        while changed:
            changed = False
            for src, dst, kind in self.edges:
                if kind != "duplicates":
                    continue
                if src in found and dst not in found:
                    found.add(dst)
                    changed = True
                if dst in found and src not in found:
                    found.add(src)
                    changed = True
        found.discard(node_id)
        return found

    def superseded(self, node_id: str) -> bool:
        return any(dst == node_id and kind == "temporally_supersedes" for _, dst, kind in self.edges)

    def independent_confirmations(self, node_id: str) -> int:
        return sum(1 for src, dst, kind in self.edges if dst == node_id and kind == "independently_confirms")


def adjusted_evidence_score(
    graph: ProvenanceGraph,
    evidence_id: str,
    base_score: float,
    *,
    seen: Iterable[str] = (),
) -> dict[str, float | bool]:
    """Duplicate and superseded evidence cannot dominate the score."""

    seen_set = set(seen)
    dup = graph.duplicates_of(evidence_id)
    redundant = bool(dup.intersection(seen_set) or evidence_id in seen_set)
    super_flag = graph.superseded(evidence_id)
    confirms = graph.independent_confirmations(evidence_id)
    score = base_score
    if redundant:
        score *= 0.15
    if super_flag:
        score *= 0.25
    if confirms:
        score *= 1.0 + 0.1 * min(confirms, 3)
    changed = score != base_score
    return {
        "base": base_score,
        "adjusted": score,
        "redundant": redundant,
        "superseded": super_flag,
        "decision_relevant": changed,
    }
