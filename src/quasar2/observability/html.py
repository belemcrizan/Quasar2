"""Research Cockpit HTML. Reads artifacts; does not recompute science."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from quasar2.observability import (
    DATASET_MATURITY,
    default_rescue_dir,
    four_way_from_anatomy,
    load_run,
    project_root,
)
from quasar2.rescue.policy import action_registry


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _metric(block: dict[str, Any] | None, path: tuple[str, ...], default: str = "unavailable") -> str:
    cursor: Any = block
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return default
        cursor = cursor[key]
    return "unavailable" if cursor is None else str(cursor)


def render_cockpit(run_dir: Path | None = None) -> str:
    root = project_root()
    dest = Path(run_dir) if run_dir else default_rescue_dir(root)
    loaded = load_run(dest)
    if not loaded.get("available"):
        return _page(
            "<h1>QUASAR2 Research Cockpit</h1>"
            f"<p class='empty'>Run artifacts unavailable: {_esc(loaded.get('reason'))}. "
            "Execute <code>quasar2 rescue-cycle</code> first.</p>"
        )
    manifest = loaded["manifest"]
    anatomy = loaded["anatomy"]
    buckets = four_way_from_anatomy(anatomy)
    metrics = (manifest.get("confirmatory_metrics") or {}).get("falsification") or {}
    gates = manifest.get("gates") or {}
    claims = manifest.get("claims") or []
    actions = action_registry()
    cards = [
        ("N", manifest.get("n_queries")),
        ("Rescue (best predicted arm)", manifest.get("non_oracle_rescue_count")),
        ("NetRescueRate (falsification)", _metric(metrics, ("NetRescueRate", "rate"))),
        ("ΔU (falsification)", _metric(metrics, ("DeltaU_EXPLORE", "mean"))),
        ("OverthinkingRate_FC", _metric(metrics, ("OverthinkingRate_FC", "rate"))),
        ("OracleRescueCeiling", _metric(manifest.get("oracle_ceiling") or {}, ("overall", "rate"))),
        ("best_predicted_arm", manifest.get("best_predicted_arm")),
        ("cycle6_policy", gates.get("cycle6_policy")),
        ("dataset_maturity", DATASET_MATURITY["sanity_catalog"]),
    ]
    card_html = "".join(
        f"<article class='card'><h3>{_esc(title)}</h3><p>{_esc(value)}</p></article>" for title, value in cards
    )
    matrix = f"""
    <table>
      <tr><th></th><th>QUASAR correct</th><th>QUASAR wrong</th></tr>
      <tr><th>Fast correct</th><td><a href='#both-correct'>Both Correct n={len(buckets.get('BOTH_CORRECT', []))}</a></td>
          <td><a href='#overthinking'>Overthinking n={len(buckets.get('OVERTHINKING', []))}</a></td></tr>
      <tr><th>Fast wrong</th><td><a href='#rescue'>Rescue n={len(buckets.get('RESCUE', []))}</a></td>
          <td><a href='#both-wrong'>Both Wrong n={len(buckets.get('BOTH_WRONG', []))}</a></td></tr>
    </table>
    """
    claim_rows = "".join(
        "<tr>"
        f"<td>{_esc(c.get('claim_id'))}</td><td>{_esc(c.get('status'))}</td>"
        f"<td>{_esc(c.get('evidence'))}</td><td>{_esc(c.get('scope'))}</td>"
        f"<td>{_esc(c.get('limitation'))}</td></tr>"
        for c in claims
    )
    gate_rows = "".join(f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>" for k, v in gates.items())
    action_rows = "".join(
        f"<tr><td>{_esc(a['name'])}</td><td>{_esc(a['maturity'])}</td><td>{_esc(a['semantics'])}</td></tr>"
        for a in actions
    )
    dataset_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td><td>{'confirmatory' if v == 'CONFIRMATORY_BENCHMARK' else 'not confirmatory'}</td></tr>"
        for k, v in DATASET_MATURITY.items()
    )
    rescue_cases = "".join(
        f"<li><code>{_esc(row.get('query_id'))}</code> Fast={_esc(row.get('fast_predicted'))} "
        f"→ {_esc(row.get('disc_predicted'))} failure={_esc(row.get('primary_failure'))}</li>"
        for row in buckets.get("RESCUE", [])[:20]
    ) or "<li>No Rescue rows in this artifact.</li>"
    body = f"""
    <header>
      <h1>QUASAR2 Research Cockpit</h1>
      <p>run_id={_esc(manifest.get('run_id'))} · schema={_esc(manifest.get('schema_version'))} ·
         source={_esc(dest)} · numbers come from artifacts, not hardcoded series.</p>
    </header>
    <nav>
      <a href="#overview">Overview</a>
      <a href="#rescue">Rescue Lab</a>
      <a href="#claims">Claims</a>
      <a href="#policy">Policy</a>
      <a href="#external">External</a>
      <a href="/demo">Incident demo</a>
      <a href="/docs">OpenAPI</a>
    </nav>
    <section id="overview"><h2>Overview</h2><div class="grid">{card_html}</div></section>
    <section id="rescue"><h2>Rescue Lab</h2>{matrix}
      <h3>Rescue cases</h3><ul>{rescue_cases}</ul>
    </section>
    <section id="gates"><h2>Gates</h2><table><tr><th>Gate</th><th>Status</th></tr>{gate_rows}</table></section>
    <section id="claims"><h2>Claims</h2>
      <table><tr><th>Claim</th><th>Status</th><th>Evidence</th><th>Dataset/scope</th><th>Limitation</th></tr>
      {claim_rows}</table>
    </section>
    <section id="policy"><h2>Policy maturity</h2>
      <table><tr><th>Action</th><th>Status</th><th>Semantics</th></tr>{action_rows}</table>
      <p>Frozen v0.1.1 loop is unchanged. Experimental gated policy is not product-promoted while Cycle 6 is BLOCKED.</p>
    </section>
    <section id="external"><h2>External validity maturity</h2>
      <table><tr><th>Dataset</th><th>Class</th><th>Role</th></tr>{dataset_rows}</table>
    </section>
    <section id="finops"><h2>FinOps</h2>
      <p>Utility uses pre-registered abstract costs (wrong_answer=1.4, explore=0.10, ask=0.28).
      No live currency conversion table is attached; monetary claims are unavailable.</p>
    </section>
    """
    return _page(body)


def _page(body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>QUASAR2 Research Cockpit</title>
<style>
:root {{ --bg:#0f1419; --fg:#e8eef4; --muted:#9aa8b6; --card:#1b232c; --acc:#3d7ea6; --ok:#2a6f4e; }}
@media (prefers-color-scheme: light) {{
  :root {{ --bg:#f6f3ee; --fg:#1b1f24; --muted:#5c6770; --card:#fff; --acc:#215f8a; --ok:#1f6b45; }}
}}
body {{ font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--fg);
       margin:0; line-height:1.45; }}
header, nav, section {{ padding:1rem 1.25rem; max-width:1100px; margin:auto; }}
nav a {{ color:var(--acc); margin-right:1rem; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:0.75rem; }}
.card {{ background:var(--card); padding:0.8rem; border-radius:8px; border:1px solid #0003; }}
.card h3 {{ margin:0 0 0.4rem; font-size:0.85rem; color:var(--muted); font-weight:600; }}
table {{ border-collapse:collapse; width:100%; }}
th, td {{ border-bottom:1px solid #0003; text-align:left; padding:0.4rem 0.5rem; vertical-align:top; }}
.empty {{ color:var(--muted); }}
code {{ font-size:0.9em; }}
a {{ color:var(--acc); }}
</style></head><body>{body}</body></html>"""


def render_demo_page() -> str:
    from quasar2.observability.demo import DEMO_CASES, classify_demo_cases

    cases = classify_demo_cases()
    items = []
    for spec in DEMO_CASES:
        row = cases.get(spec["id"], {})
        status = row.get("status", "not_demonstrated")
        items.append(
            f"<article class='card'><h3>{_esc(spec['title'])}</h3>"
            f"<p>{_esc(spec['symptom'])}</p>"
            f"<p>class={_esc(spec['expected_class'])} · status=<strong>{_esc(status)}</strong></p>"
            f"<p>{_esc(row.get('note', ''))}</p></article>"
        )
    body = (
        "<header><h1>Incident investigation demo</h1>"
        "<p>Offline runbook snapshot. Golden demos are not fabricated: undemonstrated classes stay labeled.</p>"
        "<p><a href='/'>Back to cockpit</a></p></header>"
        f"<section class='grid'>{''.join(items)}</section>"
    )
    return _page(body)
