"""Command-line interface for demo, validation, and benchmarking."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from quasar2 import __version__
from quasar2.benchmark import BenchmarkRunner, format_summary_table, load_intents, write_results
from quasar2.config import ProjectConfig, load_structured
from quasar2.datasets.ops_runbook import write_fixture
from quasar2.experiment import RegimeExperiment, format_experiment_table
from quasar2.hypotheses.catalog import HypothesisCatalog
from quasar2.pipeline import QuasarPipeline, VALID_ABLATIONS
from quasar2.retrieval import load_corpus


def _config(path: str | None) -> ProjectConfig:
    return ProjectConfig.load(path)


def command_demo(args: argparse.Namespace) -> int:
    pipeline = QuasarPipeline.from_config(_config(args.config))
    if getattr(args, "v2_shadow", False):
        pipeline.v2_shadow_enabled = True
    result = pipeline.run(args.query, args.domain, ablation=args.ablation)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0
    print(f"action: {result.decision.action.value}")
    print(f"predicted hypothesis: {result.predicted_hypothesis_id}")
    print(f"confidence: {result.final_belief.top_probability:.3f}")
    print(f"margin: {result.final_belief.margin:.3f}")
    print(f"retrieval calls: {result.retrieval_calls}")
    print(f"retrieval calls avoided: {result.retrieval_calls_avoided}")
    print(f"explore rounds: {result.explore_rounds}")
    print(f"pruned explorations: {result.pruned_explorations}")
    print(f"termination reason: {result.termination_reason}")
    print(f"mean document novelty: {result.mean_document_novelty:.3f}")
    print(f"total belief variation: {result.total_belief_variation:.3f}")
    print(
        "observed entropy reduction: "
        f"{result.total_observed_entropy_reduction:.3f}"
    )
    if result.answer:
        print(f"answer: {result.answer}")
    if result.clarification_question:
        print(f"question: {result.clarification_question}")
    if args.trace:
        print("\ntrace")
        for event in result.trace:
            payload = json.dumps(event.payload, sort_keys=True, ensure_ascii=False)
            print(f"{event.sequence:02d} {event.stage:<12} {event.message} | {payload}")
    return 0


def command_benchmark(args: argparse.Namespace) -> int:
    config = _config(args.config)
    runner = BenchmarkRunner(config)
    methods = tuple(args.methods.split(",")) if args.methods else None
    conditions = tuple(args.conditions.split(",")) if args.conditions else None
    results = runner.run(methods=methods, conditions=conditions, limit=args.limit)
    output = Path(args.output) if args.output else config.root / "experiments/results/benchmark.json"
    json_path, csv_path = write_results(results, output)
    print(format_summary_table(results))
    print(f"\nJSON: {json_path}")
    print(f"CSV:  {csv_path}")
    return 0


def command_experiment(args: argparse.Namespace) -> int:
    config_path = args.config
    if config_path is None:
        from quasar2.config import discover_project_root

        config_path = str(discover_project_root() / "configs/v02_regime.yaml")
    config = _config(config_path)
    runner = RegimeExperiment(config)
    methods = tuple(args.methods.split(",")) if args.methods else None
    seeds = tuple(int(item) for item in args.seeds.split(",")) if args.seeds else None
    results = runner.run(methods=methods, seeds=seeds, limit=args.limit)
    output = (
        Path(args.output)
        if args.output
        else config.root / "experiments/results/regime.json"
    )
    json_path, csv_path = write_results(results, output)
    print(format_experiment_table(results))
    print(f"\nJSON: {json_path}")
    print(f"CSV:  {csv_path}")
    return 0


def command_materialize(args: argparse.Namespace) -> int:
    root = _config(None).root
    write_fixture(root)
    print(f"wrote ops fixture under {root / 'data' / 'ops'}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    config = _config(args.config)
    paths = config.section("paths")
    domains = load_structured(config.resolve(str(paths["domains"])))
    intents = load_intents(config.resolve(str(paths["intents"])))
    catalog = HypothesisCatalog.from_directory(config.resolve(str(paths["catalog"])))
    documents = load_corpus(config.resolve(str(paths["corpus"])))
    hypothesis_ids = {hypothesis.hypothesis_id for hypothesis in catalog}
    errors: list[str] = []
    for intent in intents:
        if intent.domain not in domains:
            errors.append(f"{intent.intent_id}: unknown domain {intent.domain}")
        if intent.correct_hypothesis not in hypothesis_ids:
            errors.append(f"{intent.intent_id}: unknown hypothesis {intent.correct_hypothesis}")
    covered = {identifier for document in documents for identifier in document.hypothesis_ids}
    uncovered = sorted(hypothesis_ids - covered)
    if uncovered:
        errors.append(f"hypotheses without documents: {', '.join(uncovered)}")
    counts = {
        domain: sum(1 for intent in intents if intent.domain == domain) for domain in domains
    }
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("configuration: valid")
    print(f"domains: {', '.join(sorted(domains))}")
    print(f"hypotheses: {len(hypothesis_ids)}")
    print(f"documents: {len(documents)}")
    print(f"intents: {len(intents)} ({counts})")
    print(f"canonical benchmark queries: {len(intents) * 3}")
    return 0


def command_wdi_sync(args: argparse.Namespace) -> int:
    from quasar2.wdi.snapshot import sync_slice

    manifest = sync_slice(Path(args.output), stage=args.stage, source_id=args.source)
    print(json.dumps(manifest, indent=2))
    return 0 if manifest.get("status") == "COMPLETE" else 1


def command_wdi_validate(args: argparse.Namespace) -> int:
    from quasar2.wdi.snapshot import load_snapshot
    from quasar2.wdi.source import WDIEvidenceSource

    loaded = load_snapshot(Path(args.snapshot))
    source = WDIEvidenceSource(args.snapshot)
    report = source.validate()
    print(json.dumps({"manifest": loaded["manifest"], "validation": report.ok}, indent=2, default=str))
    return 0 if report.ok else 1


def command_wdi_build_corpus(args: argparse.Namespace) -> int:
    from quasar2.wdi.source import WDIEvidenceSource

    source = WDIEvidenceSource(args.snapshot)
    print(f"documents: {len(source.documents())}")
    print(f"snapshot: {source.manifest['snapshot_id']}")
    return 0


def command_neural_doctor(args: argparse.Namespace) -> int:
    import platform
    import sys

    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": None,
        "sentence_transformers": None,
        "cuda": False,
        "hashing_is_not_neural": True,
    }
    try:
        import torch

        info["torch"] = torch.__version__
        info["cuda"] = bool(torch.cuda.is_available())
    except Exception as error:
        info["torch_error"] = str(error)
    try:
        import sentence_transformers

        info["sentence_transformers"] = sentence_transformers.__version__
    except Exception as error:
        info["st_error"] = str(error)
    print(json.dumps(info, indent=2))
    return 0 if info["sentence_transformers"] else 1


def command_dataset_build(args: argparse.Namespace) -> int:
    from quasar2.benchmarks.wdi_bench import write_benchmark

    stage = "pilot" if args.dataset == "wdi-pilot" else "ci"
    path = write_benchmark(args.snapshot, args.output, stage=stage)
    print(path)
    return 0


def command_wdi_experiment(args: argparse.Namespace) -> int:
    from quasar2.v24.experiment import run_wdi_experiment

    payload = run_wdi_experiment(
        args.snapshot,
        stage=args.stage,
        policies=tuple(args.policies.split(",")),
        backends=tuple(args.backends.split(",")),
        output_dir=args.output,
        limit=args.limit,
    )
    print(json.dumps(payload["summaries"], indent=2))
    return 0


def command_gate_experiment(args: argparse.Namespace) -> int:
    from quasar2.v24.experiment import run_wdi_experiment

    payload = run_wdi_experiment(
        args.snapshot,
        stage=args.stage,
        policies=("fast_only", "quasar_always", "gated_quasar"),
        backends=tuple(args.backends.split(",")),
        output_dir=args.output,
        limit=args.limit,
    )
    print(json.dumps({"summaries": payload["summaries"], "claim_status": payload["claim_status"]}, indent=2))
    return 0


def command_a1_decompose(args: argparse.Namespace) -> int:
    from quasar2.analysis.a1 import run_a1

    payload = run_a1(
        list(args.run_dir),
        output_dir=args.output,
        benchmark_path=args.benchmark,
        repo_root=Path.cwd(),
    )
    print(
        json.dumps(
            {
                "n_matched": payload["metrics"]["n_matched"],
                "overall": payload["metrics"]["overall"],
                "blocked": payload["metrics"]["blocked"],
                "claim_status": payload["metrics"]["claim_status"],
                "validation": payload["validation"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    return 0 if payload["validation"]["ok"] or payload["metrics"]["n_matched"] else 1


def command_repository_audit(args: argparse.Namespace) -> int:
    from quasar2.analysis.io_util import write_json
    from quasar2.audit.repository_state import build_repository_state_manifest

    manifest = build_repository_state_manifest(Path.cwd())
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    write_json(dest / "repository_state_manifest.json", manifest)
    print(json.dumps({"test_method_count": manifest["test_method_count"], "output": str(dest)}, indent=2))
    return 0


def command_source_validate(args: argparse.Namespace) -> int:
    from quasar2.sources.fixtures import cern_open_data_source, inspire_hep_source, jwst_mast_source
    from quasar2.sources.registry import builtin_registry

    registry = builtin_registry()
    family = args.family
    if family == "worldbank_wdi":
        if not args.snapshot:
            print("ERROR: --snapshot is required for worldbank_wdi", file=sys.stderr)
            return 2
        from quasar2.wdi.source import WDIEvidenceSource

        report = WDIEvidenceSource(args.snapshot).validate()
        print(json.dumps({"source_id": "worldbank_wdi", "ok": report.ok, "descriptor": registry.get("worldbank_wdi").source_id}, indent=2))
        return 0 if report.ok else 1
    sources = {
        "jwst_mast": jwst_mast_source,
        "cern_open_data": cern_open_data_source,
        "inspire_hep": inspire_hep_source,
    }
    source = sources[family]()
    report = source.validate()
    print(json.dumps({"descriptor": dict(source.descriptor()), "validation": report}, indent=2))
    return 0 if report["ok"] else 1


def command_jwst_validate(_args: argparse.Namespace) -> int:
    namespace = argparse.Namespace(family="jwst_mast", snapshot=None)
    return command_source_validate(namespace)


def command_cern_validate(_args: argparse.Namespace) -> int:
    namespace = argparse.Namespace(family="cern_open_data", snapshot=None)
    return command_source_validate(namespace)


def command_theory_check(args: argparse.Namespace) -> int:
    from quasar2.theory.cards import default_cards
    from quasar2.theory.harness import write_theory_checks

    if args.dry_run:
        print(json.dumps({"cards": [card.id for card in default_cards()], "dry_run": True}, indent=2))
        return 0
    dest = Path(args.output)
    t4_trials = args.t4_trials
    if args.max_examples is not None:
        t4_trials = min(t4_trials, args.max_examples)
    path = write_theory_checks(
        dest,
        t4_trials=t4_trials,
        seed=args.seed,
        include_grids=not args.offline,
        t4_near_zero_trials=min(40, t4_trials),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if args.artifact_dir:
        from quasar2.reporting.registry import allocate_run_dir, write_manifest

        run_dir = allocate_run_dir(
            Path(args.artifact_dir) / "runs",
            run_id=None,
            overwrite=True,
        )
        write_manifest(run_dir, seed=args.seed, command="theory-check", root=Path.cwd())
        (run_dir / "metrics.json").write_text(json.dumps(payload["summary"], indent=2), encoding="utf-8")
        (run_dir / "theorem_checks.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"artifact: {path}")
    failing = [
        card_id
        for card_id, state in payload["summary"].items()
        if state.startswith("FAIL")
    ]
    if args.fail_fast and failing:
        return 1
    return 1 if failing else 0


def command_theorem_benchmark(args: argparse.Namespace) -> int:
    return command_theory_check(args)


def command_report(args: argparse.Namespace) -> int:
    from quasar2.theory.harness import run_theory_checks

    payload = run_theory_checks(t4_trials=args.t4_trials, include_grids=True)
    lines = [
        "# QUASAR2 theory report",
        "",
        f"code_version: {payload['code_version']}",
        "",
        "## Execution status",
        "",
    ]
    for check in payload["checks"]:
        lines.append(
            f"- `{check['card_id']}`: {check['execution_state']} "
            f"(layer={check['layer']}, atol={check['atol']})"
        )
    lines.extend(
        [
            "",
            "No claim is promoted to SUPPORTED by this report.",
            "See CLAIM_LEDGER.md and docs/THEOREM_STATUS.md.",
        ]
    )
    text = "\n".join(lines) + "\n"
    if args.output:
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        json_path = dest.with_suffix(".json")
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        csv_path = dest.with_suffix(".csv")
        import csv

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("card_id", "execution_state", "layer", "notes"))
            writer.writeheader()
            for check in payload["checks"]:
                writer.writerow(
                    {
                        "card_id": check["card_id"],
                        "execution_state": check["execution_state"],
                        "layer": check["layer"],
                        "notes": check.get("notes", ""),
                    }
                )
        print(f"wrote {dest}")
        print(f"wrote {json_path}")
        print(f"wrote {csv_path}")
    else:
        print(text)
    return 0


def command_phase_diagram(args: argparse.Namespace) -> int:
    from quasar2.reporting.phase_diagram import AXES, write_diagrams
    from quasar2.reporting.registry import allocate_run_dir, write_manifest

    axes = tuple(args.axes.split(",")) if args.axes else AXES
    dest = Path(args.output)
    if args.register:
        dest = allocate_run_dir(dest, run_id=args.run_id, overwrite=args.overwrite)
        write_manifest(dest, seed=0, command="phase-diagram", root=Path.cwd())
    else:
        dest.mkdir(parents=True, exist_ok=True)
    path = write_diagrams(dest, axes=axes, step=args.step)
    print(path)
    return 0


def command_recoverability_bench(args: argparse.Namespace) -> int:
    from quasar2.eval.recoverability_bench import write_recoverability_benchmark
    from quasar2.reporting.registry import allocate_run_dir, write_manifest

    dest = Path(args.output)
    if args.register:
        dest = allocate_run_dir(dest, run_id=args.run_id, overwrite=args.overwrite)
        write_manifest(dest, seed=0, command="recoverability-bench", root=Path.cwd())
    path = write_recoverability_benchmark(dest)
    print(path)
    return 0


def command_cycle2_audit(args: argparse.Namespace) -> int:
    from quasar2.cycle2.runner import run_cycle2

    dest = Path(args.output)
    if dest.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {dest}; pass --overwrite")
    payload = run_cycle2(
        output=dest,
        seed=int(args.seed),
        include_wdi=not args.skip_wdi,
        include_ops=not args.skip_ops,
        reproduce_gate1=not args.skip_gate1_reproduce,
    )
    print(
        json.dumps(
            {
                "run_id": payload.get("run_id"),
                "answers": payload.get("answers"),
                "maturity": payload.get("maturity"),
            },
            indent=2,
            default=str,
            ensure_ascii=True,
        )
    )
    return 0


def command_external_validity(args: argparse.Namespace) -> int:
    from quasar2.external.runner import run_external

    dest = Path(args.output)
    if dest.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {dest}; pass --overwrite")
    payload = run_external(
        dest,
        seed=int(args.seed),
        smoke=bool(args.smoke),
        overwrite=True,
    )
    print(
        json.dumps(
            {
                "run_id": payload.get("run_id"),
                "answers": payload.get("answers"),
                "leakage_ok": (payload.get("leakage") or {}).get("ok"),
                "live_official_dump": False,
                "artifact": str(dest),
            },
            indent=2,
            default=str,
        )
    )
    return 0


def command_reproduce_paper(args: argparse.Namespace) -> int:
    from quasar2.external.runner import run_reproduce_paper

    dest = Path(args.output)
    payload = run_reproduce_paper(dest, overwrite=bool(args.overwrite), smoke=not bool(args.full))
    print(json.dumps({"output": str(dest), "answers": payload.get("external_answers"), "mutable_download": False}, indent=2, default=str))
    return 0


def command_gate1_audit(args: argparse.Namespace) -> int:
    from quasar2.eval.gate1 import run_gate1_audit, write_gate1_audit
    from quasar2.reporting.registry import allocate_run_dir, write_manifest

    dest = Path(args.output)
    if args.register:
        dest = allocate_run_dir(dest, run_id=args.run_id, overwrite=args.overwrite)
        write_manifest(dest, seed=0, command="gate1-audit", root=Path.cwd())
    config = _config(args.config) if args.include_fixture else None
    payload = run_gate1_audit(
        config=config,
        include_fixture=bool(args.include_fixture),
        fixture_limit=args.fixture_limit,
    )
    path = write_gate1_audit(dest, payload)
    gate = payload["synthetic"]["gate"]
    print(
        json.dumps(
            {
                "gate1": gate["gate1"],
                "reason": gate["reason"],
                "analysis_plan_hash": payload["analysis_plan_hash"],
                "n_registered_test": payload["synthetic"]["n_registered_test"],
                "artifact": str(path),
            },
            indent=2,
        )
    )
    return 0


def command_shadow_study(args: argparse.Namespace) -> int:
    from quasar2.eval.shadow_study import run_shadow_study, write_shadow_study
    from quasar2.reporting.registry import allocate_run_dir, write_manifest

    dest = Path(args.output)
    if args.register:
        dest = allocate_run_dir(dest, run_id=args.run_id, overwrite=args.overwrite)
        write_manifest(dest, seed=int(_config(args.config).values.get("seed", 42)), command="shadow-study", root=Path.cwd())
    else:
        dest.mkdir(parents=True, exist_ok=True)
    conditions = tuple(item for item in args.conditions.split(",") if item)
    payload = run_shadow_study(
        _config(args.config),
        limit=args.limit,
        conditions=conditions,
        shadow_policy=args.shadow_policy,
    )
    path = write_shadow_study(dest, payload)
    print(json.dumps({
        "n": payload["n"],
        "agreement_rate": payload["agreement_rate"],
        "transition_matrix": payload["transition_matrix"],
        "divergence_taxonomy": payload["divergence_taxonomy"],
        "artifact": str(path),
    }, indent=2))
    return 0


def command_policy_compare(args: argparse.Namespace) -> int:
    from quasar2.eval.oracle_env import compare_policies
    from quasar2.reporting.registry import allocate_run_dir, write_manifest

    dest = Path(args.output)
    if args.register:
        dest = allocate_run_dir(dest, run_id=args.run_id, overwrite=args.overwrite)
        write_manifest(dest, seed=args.seed, command="policy-compare", root=Path.cwd())
    else:
        dest.mkdir(parents=True, exist_ok=True)
    payload = compare_policies(args.n, seed=args.seed)
    path = dest / "policy_compare.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"table": payload["table"], "budget_winners": payload["budget_winners"], "artifact": str(path)}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quasar2", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="run one full inference trace")
    demo.add_argument("--query", required=True)
    demo.add_argument("--domain", required=True)
    demo.add_argument("--ablation", default="full", choices=sorted(VALID_ABLATIONS))
    demo.add_argument("--config")
    demo.add_argument("--trace", action="store_true")
    demo.add_argument("--json", action="store_true")
    demo.add_argument(
        "--v2-shadow",
        action="store_true",
        help="compute v2 recommended_action_v2 without changing the executed legacy action",
    )
    demo.set_defaults(func=command_demo)

    benchmark = subparsers.add_parser("benchmark", help="run baselines and ablations")
    benchmark.add_argument("--config")
    benchmark.add_argument("--output")
    benchmark.add_argument("--methods", help="comma-separated method names")
    benchmark.add_argument("--conditions", help="comma-separated q0,q1,q2")
    benchmark.add_argument("--limit", type=int, help="limit intents for a smoke run")
    benchmark.set_defaults(func=command_benchmark)

    experiment = subparsers.add_parser(
        "experiment",
        help="v0.2 regime experiment (matched backends, factorial degradation)",
    )
    experiment.add_argument("--config", default=None)
    experiment.add_argument("--output")
    experiment.add_argument("--methods", help="comma-separated method names")
    experiment.add_argument("--limit", type=int, help="limit intents for a smoke run")
    experiment.add_argument("--seeds", help="comma-separated integer seeds")
    experiment.set_defaults(func=command_experiment)

    materialize = subparsers.add_parser(
        "materialize-ops", help="write the isolated ops runbook fixture under data/ops"
    )
    materialize.set_defaults(func=command_materialize)

    validate = subparsers.add_parser("validate", help="validate data and cross-references")
    validate.add_argument("--config")
    validate.set_defaults(func=command_validate)

    wdi_sync = subparsers.add_parser("wdi-sync", help="download an immutable WDI snapshot slice (network)")
    wdi_sync.add_argument("--source", type=int, default=2)
    wdi_sync.add_argument("--stage", default="ci", choices=("ci", "pilot"))
    wdi_sync.add_argument("--output", required=True)
    wdi_sync.set_defaults(func=command_wdi_sync)

    wdi_validate = subparsers.add_parser("wdi-validate", help="validate a local WDI snapshot offline")
    wdi_validate.add_argument("--snapshot", required=True)
    wdi_validate.set_defaults(func=command_wdi_validate)

    wdi_corpus = subparsers.add_parser("wdi-build-corpus", help="summarize IndicatorDocument/EntityDocument corpus")
    wdi_corpus.add_argument("--snapshot", required=True)
    wdi_corpus.set_defaults(func=command_wdi_build_corpus)

    neural = subparsers.add_parser("neural-doctor", help="report neural dependency versions")
    neural.set_defaults(func=command_neural_doctor)

    dataset = subparsers.add_parser("dataset-build", help="materialize QUASAR-Bench-WDI JSON")
    dataset.add_argument("--dataset", default="wdi-ci")
    dataset.add_argument("--snapshot", required=True)
    dataset.add_argument("--output", required=True)
    dataset.set_defaults(func=command_dataset_build)

    wdi_exp = subparsers.add_parser("wdi-experiment", help="crossed retriever x policy WDI evaluation")
    wdi_exp.add_argument("--snapshot", required=True)
    wdi_exp.add_argument("--stage", default="ci")
    wdi_exp.add_argument("--backends", default="bm25")
    wdi_exp.add_argument("--policies", default="top1,threshold,v24")
    wdi_exp.add_argument("--output")
    wdi_exp.add_argument("--limit", type=int)
    wdi_exp.set_defaults(func=command_wdi_experiment)

    gate_exp = subparsers.add_parser(
        "gate-experiment",
        help="Milestone A: FAST_ONLY vs QUASAR_ALWAYS vs GATED_QUASAR on WDI",
    )
    gate_exp.add_argument("--snapshot", required=True)
    gate_exp.add_argument("--stage", default="ci")
    gate_exp.add_argument("--backends", default="bm25")
    gate_exp.add_argument("--output", required=True)
    gate_exp.add_argument("--limit", type=int)
    gate_exp.set_defaults(func=command_gate_experiment)

    a1 = subparsers.add_parser(
        "a1-decompose",
        help="Milestone A1: matched FAST vs QUASAR rescue/overthinking decomposition",
    )
    a1.add_argument(
        "--run-dir",
        action="append",
        required=True,
        help="experiment result directory with per_query_results.csv or raw_results.csv",
    )
    a1.add_argument("--benchmark", help="WDI benchmark JSON for query text and ground truth")
    a1.add_argument("--output", required=True)
    a1.set_defaults(func=command_a1_decompose)

    repo_audit = subparsers.add_parser(
        "repository-audit",
        help="write RepositoryStateManifest (structural validation of claimed capabilities)",
    )
    repo_audit.add_argument("--output", default="experiments/results/repository_state")
    repo_audit.set_defaults(func=command_repository_audit)

    source_val = subparsers.add_parser(
        "source-validate",
        help="validate a typed source family against an offline fixture",
    )
    source_val.add_argument(
        "--family",
        required=True,
        choices=("worldbank_wdi", "jwst_mast", "cern_open_data", "inspire_hep"),
    )
    source_val.add_argument("--snapshot", help="WDI snapshot directory when family=worldbank_wdi")
    source_val.set_defaults(func=command_source_validate)

    jwst_val = subparsers.add_parser("jwst-validate", help="alias: validate JWST/MAST metadata fixture")
    jwst_val.set_defaults(func=command_jwst_validate)

    cern_val = subparsers.add_parser("cern-validate", help="alias: validate CERN Open Data metadata fixture")
    cern_val.set_defaults(func=command_cern_validate)

    theory = subparsers.add_parser(
        "theory-check",
        help="run deterministic/numeric T1–T4 and C1 checks (does not alter legacy policy)",
    )
    theory.add_argument("--output", default="artifacts/theorem_checks.json")
    theory.add_argument("--t4-trials", type=int, default=400)
    theory.add_argument("--seed", type=int, default=0)
    theory.add_argument("--max-examples", type=int, default=None)
    theory.add_argument("--offline", action="store_true")
    theory.add_argument("--artifact-dir", default=None)
    theory.add_argument("--fail-fast", action="store_true")
    theory.add_argument("--dry-run", action="store_true")
    theory.set_defaults(func=command_theory_check)

    theorem_bench = subparsers.add_parser(
        "theorem-benchmark",
        help="alias of theory-check",
    )
    theorem_bench.add_argument("--output", default="artifacts/theorem_checks.json")
    theorem_bench.add_argument("--t4-trials", type=int, default=400)
    theorem_bench.add_argument("--seed", type=int, default=0)
    theorem_bench.add_argument("--max-examples", type=int, default=None)
    theorem_bench.add_argument("--offline", action="store_true")
    theorem_bench.add_argument("--artifact-dir", default=None)
    theorem_bench.add_argument("--fail-fast", action="store_true")
    theorem_bench.add_argument("--dry-run", action="store_true")
    theorem_bench.set_defaults(func=command_theorem_benchmark)

    report = subparsers.add_parser("report", help="write a markdown/JSON theory status report")
    report.add_argument("--output", default="artifacts/theory_report.md")
    report.add_argument("--t4-trials", type=int, default=200)
    report.set_defaults(func=command_report)

    phase = subparsers.add_parser(
        "phase-diagram",
        help="write 2D shadow-decision diagrams (does not change the legacy policy)",
    )
    phase.add_argument("--output", default="experiments/runs")
    phase.add_argument(
        "--axes",
        help="comma-separated axis ids (default: all)",
    )
    phase.add_argument("--step", type=float, default=0.1)
    phase.add_argument("--register", action="store_true", help="allocate a non-overwriting run directory")
    phase.add_argument("--run-id")
    phase.add_argument("--overwrite", action="store_true")
    phase.set_defaults(func=command_phase_diagram)

    recov = subparsers.add_parser(
        "recoverability-bench",
        help="synthetic recoverability vs empirical VoI (does not change the legacy loop)",
    )
    recov.add_argument("--output", default="experiments/runs")
    recov.add_argument("--register", action="store_true")
    recov.add_argument("--run-id")
    recov.add_argument("--overwrite", action="store_true")
    recov.set_defaults(func=command_recoverability_bench)

    gate1 = subparsers.add_parser(
        "gate1-audit",
        help="Gate 1: deployment recoverability vs realized EXPLORE gain (does not change the legacy loop)",
    )
    gate1.add_argument("--output", default="experiments/runs")
    gate1.add_argument("--register", action="store_true")
    gate1.add_argument("--run-id")
    gate1.add_argument("--overwrite", action="store_true")
    gate1.add_argument(
        "--include-fixture",
        action="store_true",
        help="also run FULL vs noExplore on the sanity fixture (exploratory; slow relative to synthetic)",
    )
    gate1.add_argument("--fixture-limit", type=int, help="limit intents for a fixture smoke")
    gate1.add_argument("--config")
    gate1.set_defaults(func=command_gate1_audit)

    shadow = subparsers.add_parser(
        "shadow-study",
        help="sanity-fixture shadow transition matrix; does not overwrite frozen benchmark.json",
    )
    shadow.add_argument("--config")
    shadow.add_argument("--output", default="experiments/runs")
    shadow.add_argument("--limit", type=int)
    shadow.add_argument("--conditions", default="q0,q1,q2")
    shadow.add_argument("--shadow-policy", default="quadrant", choices=("quadrant", "threshold", "myopic_voi", "sprt_inspired"))
    shadow.add_argument("--register", action="store_true")
    shadow.add_argument("--run-id")
    shadow.add_argument("--overwrite", action="store_true")
    shadow.set_defaults(func=command_shadow_study)

    policy = subparsers.add_parser(
        "policy-compare",
        help="synthetic oracle vs threshold/myopic/SPRT/learned (not WDI)",
    )
    policy.add_argument("--output", default="experiments/runs")
    policy.add_argument("--n", type=int, default=400)
    policy.add_argument("--seed", type=int, default=0)
    policy.add_argument("--register", action="store_true")
    policy.add_argument("--run-id")
    policy.add_argument("--overwrite", action="store_true")
    policy.set_defaults(func=command_policy_compare)

    cycle2 = subparsers.add_parser(
        "cycle2-audit",
        help="cycle-2 recoverability/policy/synthetic/deployment-like path (does not change the legacy loop)",
    )
    cycle2.add_argument("--output", default="experiments/results/cycle2_maturity")
    cycle2.add_argument("--seed", type=int, default=0)
    cycle2.add_argument("--overwrite", action="store_true")
    cycle2.add_argument("--skip-wdi", action="store_true")
    cycle2.add_argument("--skip-ops", action="store_true")
    cycle2.add_argument("--skip-gate1-reproduce", action="store_true")
    cycle2.set_defaults(func=command_cycle2_audit)

    ext = subparsers.add_parser(
        "external-validity",
        help="source audit, schema-faithful NASA/ESA/ALMA transfer, scale, budget, regime (does not change the legacy loop)",
    )
    ext.add_argument("--output", default="experiments/results/external_validity")
    ext.add_argument("--seed", type=int, default=0)
    ext.add_argument("--overwrite", action="store_true")
    ext.add_argument("--smoke", action="store_true", help="smaller N for CI")
    ext.set_defaults(func=command_external_validity)

    repro = subparsers.add_parser(
        "reproduce-paper",
        help="reconstruct frozen tables and rerun the offline external program (no silent mutable downloads)",
    )
    repro.add_argument("--output", default="experiments/results/paper_reproduce")
    repro.add_argument("--overwrite", action="store_true")
    repro.add_argument("--full", action="store_true", help="run the non-smoke external program")
    repro.set_defaults(func=command_reproduce_paper)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
