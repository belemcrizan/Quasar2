"""Render diagnostic comparisons from frozen, measured run reports."""

import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[2]
report = json.loads((root / "experiments/v03/reports/results.json").read_text())
fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
colors = ["#355c7d", "#6c5b7b", "#c06c84"]
for ax, (name, result) in zip(axes, report.items()):
    selected = {row["policy"]: row for row in result["primary"]["policies"]}
    policies = ["stop", "rstar_full", "always"]
    ax.bar(["STOP", "R*", "ALWAYS"], [selected[p]["utility"] for p in policies], color=colors)
    ax.set_title(name + "\n" + result["query_provenance"], fontsize=10)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylim(0, 1)
axes[0].set_ylabel("Mean test utility (retrieval price 0.05)")
fig.suptitle("Diagnostic only — generated/synthetic queries; no external support claim")
fig.tight_layout()
fig.savefig(root / "artifacts/v03/utility-comparison.svg", metadata={"Date": None})
