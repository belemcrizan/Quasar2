"""Cycle-3 runner. Frozen v0.1.1, Gate 1, and Cycle 2 defaults are not rewritten."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quasar2 import __version__
from quasar2.config import discover_project_root
from quasar2.external import SCHEMA_VERSION
from quasar2.external.adversary import adversarial_suite, ops_structured_states
from quasar2.external.benchmark import assign_splits, corpus_for_records, expand_states, freeze_state_for_policy, records_for_source
from quasar2.external.budget import equal_budget_report, neu_surface
from quasar2.external.evaluate import evaluate_states, query_expansion_baseline, retrieval_table
from quasar2.external.leakage import audit_batch, audit_corpus_documents
from quasar2.external.power import default_justification
from quasar2.external.provenance import card_template
from quasar2.external.regime import by_ambiguity, discover_regime, per_state_delta
from quasar2.external.replicate import (
    cloud_replication_stub,
    environment_lock,
    git_sha,
    paper_tables,
    reconstruct_cycle2,
    reconstruct_frozen_sanity,
)
from quasar2.external.scale import ambiguity_scale, corpus_scale, hypothesis_scale, open_set_scale, query_scale_justification
from quasar2.external.snapshots import SNAPSHOT_ID, snapshot_manifest
from quasar2.external.source_audit import SOURCE_AUDIT, counts as audit_counts, rejected_sources, selected_sources
from quasar2.external.transfer import adaptation_ladder
from quasar2.reporting.registry import write_manifest


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _neural_status() -> dict[str, Any]:
    try:
        import sentence_transformers  # noqa: F401

        return {"available": True, "executed": False, "reason": "optional extra present but full neural sweep not in default stdlib run"}
    except Exception:
        return {"available": False, "executed": False, "reason": "sentence-transformers not installed"}


def _data_cards() -> list[dict[str, Any]]:
    return [
        card_template(
            "nasa_exo_schema",
            ownership="NASA/IPAC NExScI (schema); records are SYN- prefixed",
            public_access="Official TAP is public; this snapshot is not a TAP dump",
            license_terms="Do not cite SYN- ids as archive rows. Archive terms: exoplanetarchive.ipac.caltech.edu",
            snapshot=SNAPSHOT_ID,
            filtering="bounded constructed KOI/TOI-like rows",
            transformations="controlled query degradations",
            exclusions="no FITS light curves",
            known_biases="uniform gold rotation; not Kepler occurrence rates",
            ambiguity_construction="transit vs EB vs activity vs blend vs unknown",
            ground_truth="constructed gold_hypothesis; ORACLE_ONLY",
            limitations="Not live NASA data. Zero-shot tests schema transfer, not catalog-version transfer.",
        ),
        card_template(
            "esa_gaia_schema",
            ownership="ESA/Gaia/DPAC (schema); SYN-Gaia ids",
            public_access="Gaia Archive is public; this snapshot is not an ADQL dump",
            license_terms="Credit ESA/Gaia/DPAC for the real archive; do not cite SYN ids as source_id",
            snapshot=SNAPSHOT_ID,
            filtering="bounded constructed sources",
            transformations="channel astrometry vs XP",
            exclusions="no 1.8e9-source dump",
            known_biases="synthetic RUWE grid",
            ambiguity_construction="single vs binary vs spurious vs unknown",
            ground_truth="constructed",
            limitations="Not live Gaia DR3 rows.",
        ),
        card_template(
            "obs_alma_schema",
            ownership="ALMA/JAO partners (schema); SYN-ALMA ids",
            public_access="Archive is public after proprietary period; snapshot is not Request Handler output",
            license_terms="Cite real project codes only when using official products",
            snapshot=SNAPSHOT_ID,
            filtering="metadata-like constructed projects",
            transformations="band6 vs band7",
            exclusions="no visibilities",
            known_biases="equal class prior",
            ambiguity_construction="disk vs envelope vs outflow vs artifact vs unknown",
            ground_truth="constructed",
            limitations="Independent observatory family at schema level only.",
        ),
        card_template(
            "jwst_mast_fixture",
            ownership="STScI MAST fixture already in this repository",
            public_access="Metadata fixture; scientific_benchmark_complete=false",
            license_terms="Cite JWST data per STScI rules when using real products",
            snapshot="data/sources/fixtures/jwst_mast",
            retrieval_date="in-repo fixture",
            filtering="three observation metadata rows",
            transformations="none beyond overlay",
            exclusions="no FITS",
            known_biases="tiny N",
            ambiguity_construction="calibrated vs reprocessed product lineage",
            ground_truth="fixture supersedes field",
            limitations="Cannot support H_EXT alone.",
        ),
    ]


def _claims(answers: dict[str, str], regime: Mapping[str, Any], budget: Mapping[str, Any]) -> list[dict[str, Any]]:
    def status(letter: str) -> str:
        val = answers.get(letter, "NO")
        if val == "YES":
            return "PARTIALLY_SUPPORTED"
        if val == "PARTIAL":
            return "NOT_SUPPORTED"
        return "NOT_SUPPORTED"

    held = (regime.get("heldout") or {}).get("mean_delta_in_Rstar")
    return [
        {
            "claim_id": "H_EXT",
            "text": "Adaptive epistemic action transfers across independent scientific sources.",
            "status": "HYPOTHESIS" if answers.get("A") != "YES" else status("A"),
            "result": answers.get("A"),
            "scope": "schema-faithful NASA/ESA/ALMA snapshots, not live TAP dumps",
        },
        {
            "claim_id": "H_DOMAIN",
            "text": "Decision-theoretic acquisition principles transfer across astronomy and OPS.",
            "status": "HYPOTHESIS",
            "result": answers.get("B"),
            "scope": "ops_structured states clustered by incident class",
        },
        {
            "claim_id": "H_SCALE",
            "text": "Advantage region remains detectable as corpus and hypothesis spaces scale.",
            "status": "HYPOTHESIS",
            "result": answers.get("C"),
        },
        {
            "claim_id": "H_BUDGET",
            "text": "QUASAR2 occupies part of the utility-cost Pareto frontier in ambiguity/risk regimes.",
            "status": "HYPOTHESIS",
            "result": answers.get("E"),
            "detail": budget.get("pareto_calls"),
        },
        {
            "claim_id": "H_REGIME",
            "text": "QUASAR2 advantage can be predicted from observable regime variables.",
            "status": "HYPOTHESIS",
            "result": answers.get("H"),
            "heldout_mean_delta_in_Rstar": held,
        },
        {
            "claim_id": "H_MISMATCH",
            "text": "Observation-model mismatch explains a substantial portion of recoverability and policy failure.",
            "status": "HYPOTHESIS",
            "result": "TESTED_ON_CHANNEL_SHIFTS",
        },
        {
            "claim_id": "H_REPLICATION",
            "text": "Major findings reproduce across independent compute environments.",
            "status": "NOT_TESTED" if answers.get("D") != "YES" else "HYPOTHESIS",
            "result": answers.get("D"),
        },
        {
            "claim_id": "C3-live-official-dumps",
            "text": "Live NASA/ESA/ALMA TAP dumps were used as confirmatory evidence.",
            "status": "REFUTED",
            "result": "This cycle uses schema-faithful offline snapshots plus in-repo fixtures.",
        },
    ]


def _answers(payload: dict[str, Any]) -> dict[str, str]:
    transfer = payload["transfer"]["zero_shot"]["matrix"]
    by_role = {m["split_role"]: m for m in transfer}
    def pos(role: str) -> bool:
        cell = by_role.get(role) or {}
        d = (cell.get("delta_vs_answer") or {}).get("mean_delta")
        ci = (cell.get("delta_vs_answer") or {}).get("ci") or {}
        if d is None:
            return False
        low = ci.get("ci_low")
        return d > 0 and (low is None or float(low) > 0)

    nasa_roles = [r for r in by_role if "nasa" in r or r in {"external_nasa", "cross_instrument", "temporal_holdout"}]
    esa_ok = pos("external_esa")
    obs_ok = pos("external_observatory")
    nasa_any = any(pos(r) for r in nasa_roles)
    nasa_all = all(pos(r) for r in nasa_roles) if nasa_roles else False
    if nasa_all and esa_ok and obs_ok:
        a = "YES"
    elif nasa_any or esa_ok or obs_ok:
        a = "PARTIAL"
    else:
        a = "NO"

    ops_delta = payload["ops_delta"]
    ops_mean = (ops_delta or {}).get("mean_delta")
    ops_low = ((ops_delta or {}).get("ci") or {}).get("ci_low")
    if ops_mean is not None and ops_mean > 0 and ops_low is not None and float(ops_low) > 0:
        b = "YES"
    elif ops_mean is not None and ops_mean > 0:
        b = "PARTIAL"
    else:
        b = "NO"

    hyp = payload["hypothesis_scale"]["table"]
    c = "PARTIAL" if hyp else "NO"

    d = "PARTIAL"  # clean-checkout + container defined; cloud NOT_RUN

    frontier = payload["budget"]["pareto_calls"]
    myopic_on = any(p.get("policy") == "empirical_myopic" and p.get("on_frontier") for p in frontier)
    e = "YES" if myopic_on else ("PARTIAL" if any(p.get("policy") == "empirical_myopic" for p in frontier) else "NO")

    held = payload["regime"]["heldout"]
    h = "NO"
    if held.get("n") and held.get("mean_delta_in_Rstar") is not None:
        if float(held["mean_delta_in_Rstar"]) > 0 and float(held.get("mean_delta_outside") or 0) < float(held["mean_delta_in_Rstar"]):
            h = "PARTIAL"
            if held.get("n_predicted_Rstar", 0) >= 20:
                h = "PARTIAL"
    return {
        "A": a,
        "B": b,
        "C": c,
        "D": d,
        "E": e,
        "H": h,
        "F": payload.get("region_characterization", ""),
        "G": payload.get("failed_assumption", ""),
    }


def run_external(
    output: str | Path,
    *,
    seed: int = 0,
    smoke: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    dest = Path(output)
    if dest.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {dest}; pass --overwrite")
    dest.mkdir(parents=True, exist_ok=True)
    root = discover_project_root()
    n_obj = 12 if smoke else 48
    nasa = records_for_source("nasa_exo_schema", n_objects=n_obj)
    esa = records_for_source("esa_gaia_schema", n_objects=n_obj)
    alma = records_for_source("obs_alma_schema", n_objects=n_obj)
    jwst = records_for_source("jwst_mast_fixture", n_objects=3)
    degs = ("clean", "lexical") if smoke else ("clean", "lexical", "missing_context", "severe")
    states = assign_splits(
        expand_states(nasa, degradations=degs)
        + expand_states(esa, degradations=degs)
        + expand_states(alma, degradations=degs)
        + expand_states(jwst, degradations=("clean",))
    )
    states.extend(adversarial_suite())
    ops_states = ops_structured_states(24 if smoke else 96)
    all_decision_states = states + ops_states

    leakage = audit_batch(all_decision_states, freeze_state_for_policy)
    nasa_docs = corpus_for_records(nasa, distractors=30 if smoke else 120)
    leakage_docs = audit_corpus_documents(nasa_docs, states)

    ladder = adaptation_ladder(states, seed=seed)
    rows = ladder["rows"]
    ops_eval = evaluate_states(ops_states, seed=seed, bootstrap_samples=80 if smoke else 200)
    from quasar2.external.evaluate import paired_delta

    ops_delta = paired_delta(ops_eval["rows"], "empirical_myopic", "immediate_answer", seed=seed)
    adv_eval = evaluate_states(adversarial_suite(), seed=seed, bootstrap_samples=80)

    retrieval = retrieval_table([s for s in states if s["source"] == "nasa_exoplanet_archive_schema"], nasa_docs)
    qe = query_expansion_baseline([s for s in states if s["source"] == "nasa_exoplanet_archive_schema"], nasa_docs)

    budget = equal_budget_report(rows, seed=seed)
    surface_states = [s for s in states if s.get("transformation") == "clean"][: 24 if smoke else 80]
    surface = neu_surface(
        surface_states,
        rhos=(1.4,) if smoke else (0.5, 1.0, 1.4, 2.0, 4.0),
        kappas=(0.10,) if smoke else (0.02, 0.10, 0.25, 0.50),
        seed=seed,
    )
    regime = discover_regime(rows, train_roles=("development",))
    amb = by_ambiguity(rows)

    hscale = hypothesis_scale(sizes=(2, 5) if smoke else (2, 5, 10, 20), n_per=8 if smoke else 40, seed=seed)
    oscale = open_set_scale(rates=(0.0, 0.25) if smoke else (0.0, 0.05, 0.10, 0.25, 0.50), n=12 if smoke else 80, seed=seed)
    ascale = ambiguity_scale(etas=(0.1, 0.9) if smoke else (0.1, 0.35, 0.65, 0.9), n=12 if smoke else 60, seed=seed)
    cscale = corpus_scale(sizes=(40,) if smoke else (50, 200, 800), seed=seed)

    n_clusters = len({s["cluster_id"] for s in states})
    deltas = per_state_delta(rows)
    rstar = [d for d in deltas if d["delta_q"] > 0]
    region = (
        "Candidate empirical R*: high entropy, recoverable class, low mismatch_mu, not open-set. "
        f"Observed fraction with ΔQ>0 vs immediate ANSWER: {len(rstar)}/{len(deltas)}."
    )
    failed = ""
    if not rstar:
        failed = "No state with U_myopic > U_immediate_ANSWER under the registered NEU; equal-budget superiority may be empty."
    elif leakage["n_issues"]:
        failed = "Leakage issues present; favorable numbers cannot support claims."

    figures = {
        "fig1_transfer_matrix": ladder["zero_shot"]["matrix"],
        "fig2_cross_domain": ops_delta,
        "fig3_budget_frontier": budget["pareto_calls"],
        "fig4_5_neu_surface": surface,
        "fig6_ambiguity": amb,
        "fig7_regime": regime,
        "fig8_corpus_scale": cscale,
        "fig9_hypothesis_scale": hscale,
        "fig10_mismatch": [
            {
                "split": m["split_role"],
                "delta": m.get("delta_vs_answer"),
            }
            for m in ladder["zero_shot"]["matrix"]
            if m["split_role"] in {"cross_instrument", "external_esa", "external_observatory"}
        ],
        "fig11_open_set": oscale,
        "fig12_source_effects": ladder["summaries"],
        "fig13_pareto": budget,
        "fig14_failure_taxonomy": adv_eval["summaries"],
        "publication_figures_rendered": False,
        "reason": "Underlying analysis is schema-faithful / offline; do not dress as live NASA/ESA confirmation.",
    }

    started = datetime.now(timezone.utc).isoformat()
    sha = git_sha(root)
    plan = root / "experiments" / "analysis_plans" / "external_validity.json"
    env = environment_lock(root)
    frozen = reconstruct_frozen_sanity(root)
    c2 = reconstruct_cycle2(root)

    core = {
        "schema_version": SCHEMA_VERSION,
        "run_id": dest.name,
        "timestamp": started,
        "git_sha": sha,
        "package_version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "seed": seed,
        "smoke": smoke,
        "snapshot_id": SNAPSHOT_ID,
        "plan_hash": _hash_file(plan) if plan.exists() else None,
        "source_audit_counts": audit_counts(),
        "selected_sources": selected_sources(),
        "rejected_sources": rejected_sources(),
        "data_cards": _data_cards(),
        "power": default_justification(),
        "n_states": len(states),
        "n_clusters": n_clusters,
        "query_scale": query_scale_justification(len(states), n_clusters),
        "leakage": leakage,
        "leakage_docs_issues": leakage_docs,
        "retrieval": retrieval,
        "query_expansion": qe,
        "neural": _neural_status(),
        "transfer": ladder,
        "ops_eval": {"summaries": ops_eval["summaries"]},
        "ops_delta": ops_delta,
        "adversarial": adv_eval["summaries"],
        "budget": budget,
        "neu_surface": surface,
        "regime": regime,
        "ambiguity": amb,
        "hypothesis_scale": hscale,
        "open_set_scale": oscale,
        "ambiguity_scale": ascale,
        "corpus_scale": cscale,
        "snapshots": {
            "nasa": snapshot_manifest(nasa, "nasa_exo_schema"),
            "esa": snapshot_manifest(esa, "esa_gaia_schema"),
            "alma": snapshot_manifest(alma, "obs_alma_schema"),
        },
        "environment": env,
        "frozen_v011": frozen,
        "cycle2_preserved": c2,
        "cloud": cloud_replication_stub(),
        "figure_data": figures,
        "region_characterization": region,
        "failed_assumption": failed,
        "policy_stage": "SHADOW",
        "gate1": "FAIL",
        "t2_is_not_q": True,
        "hashing_is_not_neural": True,
        "hyde_not_run": True,
        "live_official_dump": False,
    }
    answers = _answers(core)
    core["answers"] = answers
    core["claims"] = _claims(answers, regime, budget)
    core["paper_tables"] = paper_tables(frozen, c2, core)

    write_manifest(dest, seed=seed, command="external-validity", root=root, config={"seed": seed, "smoke": smoke})
    (dest / "external.json").write_text(json.dumps(core, indent=2, default=str), encoding="utf-8")
    (dest / "source_audit.json").write_text(json.dumps(list(SOURCE_AUDIT), indent=2), encoding="utf-8")
    (dest / "figure_data.json").write_text(json.dumps(figures, indent=2, default=str), encoding="utf-8")
    (dest / "claim_ledger.jsonl").write_text("\n".join(json.dumps(c, default=str) for c in core["claims"]), encoding="utf-8")
    (dest / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    (dest / "leakage_audit.json").write_text(json.dumps({"states": leakage, "docs": leakage_docs}, indent=2), encoding="utf-8")
    (dest / "reproduction_manifest.json").write_text(
        json.dumps(
            {
                "command": "python -m quasar2.cli external-validity --output experiments/results/external_validity --overwrite",
                "reproduce_paper": "python -m quasar2.cli reproduce-paper --output experiments/results/paper_reproduce --overwrite",
                "seed": seed,
                "git_sha": sha,
                "snapshot_id": SNAPSHOT_ID,
                "live_fetch": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    from quasar2.external.report import write_report

    write_report(dest, core)
    core["artifact_dir"] = str(dest)
    return core


def run_reproduce_paper(output: str | Path, *, overwrite: bool = False, smoke: bool = True) -> dict[str, Any]:
    dest = Path(output)
    if dest.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {dest}; pass --overwrite")
    ext = run_external(dest / "external_validity", seed=0, smoke=smoke, overwrite=True)
    root = discover_project_root()
    payload = {
        "frozen": reconstruct_frozen_sanity(root),
        "cycle2": reconstruct_cycle2(root),
        "external_answers": ext["answers"],
        "claims": ext["claims"],
        "environment": environment_lock(root),
        "cloud": cloud_replication_stub(),
        "mutable_download": False,
    }
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "paper_tables.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return payload
