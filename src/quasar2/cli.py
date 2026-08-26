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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
