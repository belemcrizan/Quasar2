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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quasar2", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="run one full inference trace")
    demo.add_argument("--query", required=True)
    demo.add_argument("--domain", required=True, choices=("astronomy", "ai"))
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

    validate = subparsers.add_parser("validate", help="validate data and cross-references")
    validate.add_argument("--config")
    validate.set_defaults(func=command_validate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
