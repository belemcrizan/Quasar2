"""2D phase diagrams of shadow recommendations. Regions are empirical, not imposed."""

from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any, Callable

from quasar2.decision.shadow import recommended_action_v2_shadow


AXES = (
    "ambiguity_recoverability",
    "inference_error_retrieval_cost",
    "risk_ambiguity",
    "interaction_cost_recoverability",
)

ACTIONS = ("ANSWER", "ANALYZE", "EXPLORE", "ASK", "DEFER")


def intensity_grid(step: float = 0.1) -> tuple[float, ...]:
    values = []
    n = int(round(1.0 / step))
    for i in range(n + 1):
        values.append(round(i * step, 10))
    return tuple(values)


def _cell_ambiguity_recoverability(x: float, y: float) -> str:
    return recommended_action_v2_shadow(
        entropy=x,
        recoverability=y,
        inference_error=None,
        unknown_mass=0.0,
    )


def _cell_inference_cost(x: float, y: float) -> str:
    # y = retrieval cost in [0,1]; high cost reduces recoverability value.
    recoverability = max(0.0, 1.0 - y)
    return recommended_action_v2_shadow(
        entropy=0.7,
        recoverability=recoverability,
        inference_error=x,
        unknown_mass=0.0,
    )


def _cell_risk_ambiguity(x: float, y: float) -> str:
    return recommended_action_v2_shadow(
        entropy=y,
        recoverability=0.1,
        inference_error=None,
        unknown_mass=x,
    )


def _cell_interaction_recoverability(x: float, y: float) -> str:
    # x = interaction/ask cost proxy: high cost with high recoverability prefers EXPLORE.
    if x >= 0.7 and y >= 0.25:
        entropy = 0.7
        recoverability = y
    else:
        entropy = 0.7
        recoverability = y
    return recommended_action_v2_shadow(
        entropy=entropy,
        recoverability=recoverability,
        inference_error=None,
        unknown_mass=0.05,
    )


CELL_FNS: dict[str, Callable[[float, float], str]] = {
    "ambiguity_recoverability": _cell_ambiguity_recoverability,
    "inference_error_retrieval_cost": _cell_inference_cost,
    "risk_ambiguity": _cell_risk_ambiguity,
    "interaction_cost_recoverability": _cell_interaction_recoverability,
}

AXIS_LABELS = {
    "ambiguity_recoverability": ("ambiguity", "recoverability"),
    "inference_error_retrieval_cost": ("inference_error", "retrieval_cost"),
    "risk_ambiguity": ("risk_unknown", "ambiguity"),
    "interaction_cost_recoverability": ("interaction_cost", "recoverability"),
}


def build_diagram(axis: str, *, step: float = 0.1) -> dict[str, Any]:
    if axis not in CELL_FNS:
        raise ValueError(f"Unknown axis {axis!r}; choose from {AXES}")
    xs = intensity_grid(step)
    ys = intensity_grid(step)
    fn = CELL_FNS[axis]
    cells = []
    for y in ys:
        for x in xs:
            action = fn(x, y)
            cells.append({"x": x, "y": y, "action": action})
    counts = Counter(cell["action"] for cell in cells)
    xlabel, ylabel = AXIS_LABELS[axis]
    return {
        "axis": axis,
        "x_label": xlabel,
        "y_label": ylabel,
        "step": step,
        "grid": list(xs),
        "cells": cells,
        "action_counts": dict(counts),
        "hypothesis": "Regions emerge from the shadow recommender; topology is not imposed.",
    }


def ascii_heatmap(diagram: MappingLike) -> str:
    xs = diagram["grid"]
    ys = diagram["grid"]
    lookup = {(cell["x"], cell["y"]): cell["action"][0] for cell in diagram["cells"]}
    lines = [
        f"# phase diagram {diagram['axis']}",
        f"# x={diagram['x_label']} (left→right 0..1)  y={diagram['y_label']} (bottom→top 0..1)",
        f"# letters: " + " ".join(f"{action[0]}={action}" for action in ACTIONS),
        "",
    ]
    for y in reversed(ys):
        row = "".join(lookup[(x, y)] for x in xs)
        lines.append(f"{y:3.1f} {row}")
    lines.append("    " + "".join(str(int(x * 10) % 10) for x in xs))
    return "\n".join(lines) + "\n"


def markdown_table(diagram: MappingLike) -> str:
    counts = diagram["action_counts"]
    rows = ["| action | count |", "|---|---|"]
    for action in ACTIONS:
        rows.append(f"| {action} | {counts.get(action, 0)} |")
    return "\n".join(rows) + "\n"


def html_report(diagrams: list[dict[str, Any]]) -> str:
    parts = ["<html><body><h1>QUASAR2 phase diagrams</h1>", "<p>Empirical shadow recommendations. No topology is imposed.</p>"]
    for diagram in diagrams:
        parts.append(f"<h2>{diagram['axis']}</h2>")
        parts.append(f"<pre>{ascii_heatmap(diagram)}</pre>")
    parts.append("</body></html>")
    return "\n".join(parts)


def write_diagrams(
    dest: Path,
    *,
    axes: tuple[str, ...] = AXES,
    step: float = 0.1,
) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    diagrams = [build_diagram(axis, step=step) for axis in axes]
    payload = {"schema_version": "phase_diagram.1", "diagrams": diagrams}
    (dest / "phase_diagrams.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    csv_path = dest / "phase_diagrams.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("axis", "x", "y", "action"))
        writer.writeheader()
        for diagram in diagrams:
            for cell in diagram["cells"]:
                writer.writerow({"axis": diagram["axis"], **cell})
    md_lines = ["# QUASAR2 phase diagrams", "", "Regions emerge from the shadow recommender.", ""]
    for diagram in diagrams:
        md_lines.append(f"## {diagram['axis']}")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(ascii_heatmap(diagram).rstrip())
        md_lines.append("```")
        md_lines.append("")
        md_lines.append(markdown_table(diagram))
        md_lines.append("")
    (dest / "phase_diagrams.md").write_text("\n".join(md_lines), encoding="utf-8")
    (dest / "phase_diagrams.html").write_text(html_report(diagrams), encoding="utf-8")
    return dest / "phase_diagrams.json"


# Avoid importing Mapping only for a type alias in a stdlib-only module.
MappingLike = dict[str, Any]
