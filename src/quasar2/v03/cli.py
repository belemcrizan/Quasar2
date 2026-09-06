"""Explicit acquisition and offline v03 commands."""

import json
from quasar2.v03.acquisition import DATASETS, sync, validate_snapshot
from quasar2.v03.datasets import (
    BEIRDataset,
    ScientificDataset,
    build_ir_cases,
    save_cases,
    synthetic_cases,
)
from quasar2.v03.registry import check_frozen, check_preregistration, validate_run
from quasar2.v03.runner import run


def command(args):
    if args.operation == "audit":
        result = {
            "frozen": check_frozen(args.root),
            "preregistration_hash": check_preregistration(args.root),
        }
    elif args.operation == "sync":
        result = sync(args.dataset, args.output, dry_run=not args.execute)
    elif args.operation == "validate":
        result = validate_snapshot(args.path)
    elif args.operation == "validate-run":
        result = validate_run(args.path)
    elif args.operation == "build":
        if args.dataset == "synthetic":
            cases, meta = synthetic_cases(args.limit or 600)
        else:
            dataset = (
                BEIRDataset(args.snapshot)
                if args.dataset in ("scifact", "nfcorpus", "fiqa", "trec-covid")
                else ScientificDataset(args.snapshot)
            )
            cases, meta = build_ir_cases(dataset, limit=args.limit)
        result = save_cases(args.output, cases, meta)
        result = {"dataset_hash": result["dataset_hash"], "n": len(cases)}
    else:
        result = {"run_directory": str(run(args.input, args.output, args.root))}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def add_commands(subparsers):
    parser = subparsers.add_parser(
        "v03", help="Experimental evidence program; not a validated v0.3 release"
    )
    actions = parser.add_subparsers(dest="operation", required=True)
    audit = actions.add_parser("audit")
    audit.add_argument("--root", default=".")
    audit.set_defaults(func=command)
    acquisition = actions.add_parser("sync")
    acquisition.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    acquisition.add_argument("--output", required=True)
    acquisition.add_argument("--execute", action="store_true")
    acquisition.set_defaults(func=command)
    for name in ("validate", "validate-run"):
        p = actions.add_parser(name)
        p.add_argument("path")
        p.set_defaults(func=command)
    build = actions.add_parser("build")
    build.add_argument("--dataset", choices=["synthetic", *sorted(DATASETS)], required=True)
    build.add_argument("--snapshot")
    build.add_argument("--limit", type=int)
    build.add_argument("--output", required=True)
    build.set_defaults(func=command)
    for name, target in [("evaluate", actions), ("reproduce-v03", subparsers)]:
        p = target.add_parser(name)
        p.add_argument("--input", required=True)
        p.add_argument("--output", required=True)
        p.add_argument("--root", default=".")
        p.set_defaults(func=command, operation="evaluate")
