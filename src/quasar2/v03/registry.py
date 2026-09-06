"""Immutable experiment directories with content and provenance verification."""

from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from quasar2.v03.contracts import IntegrityError


def canonical(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def environment(root):
    def git(*args):
        try:
            return subprocess.check_output(
                ["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    deps = {}
    for name in ("numpy", "pytest", "scikit-learn", "sentence-transformers", "torch", "matplotlib"):
        try:
            deps[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            deps[name] = None
    status = git("status", "--porcelain", "--untracked-files=all")
    return {
        "git_sha": git("rev-parse", "HEAD"),
        "dirty": None if status is None else bool(status),
        "source_tree_hash": digest(
            {
                str(p.relative_to(root)): file_hash(p)
                for p in sorted((Path(root) / "src").rglob("*.py"))
            }
        ),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "dependencies": deps,
    }


def check_preregistration(root):
    root = Path(root)
    lock = root / "experiments/v03/manifests/preregistration.sha256"
    for line in lock.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        if file_hash(root / name) != expected:
            raise IntegrityError(f"Preregistration changed: {name}")
    return file_hash(root / "docs/V03_PREREGISTRATION.md")


def check_frozen(root):
    root = Path(root)
    baseline = json.loads((root / "experiments/v03/manifests/baseline.json").read_text())
    errors = [
        name
        for name, sha in baseline["frozen_local_sha256"].items()
        if not (root / name).is_file() or file_hash(root / name) != sha
    ]
    if errors:
        raise IntegrityError(f"Frozen artifacts changed: {errors[:5]}")
    return {
        "ok": True,
        "files_checked": len(baseline["frozen_local_sha256"]),
        "scope": "files available in baseline audit, remote history preserved separately",
    }


def safe_path(root, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not name:
        raise IntegrityError("Unsafe artifact path")
    target = (Path(root) / relative).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise IntegrityError("Artifact escapes root")
    return target


def register(
    root,
    artifacts,
    *,
    dataset_hash,
    config_hash,
    preregistration_hash,
    seed,
    mode="diagnostic",
    metadata=None,
):
    root = Path(root)
    env = environment(Path.cwd())
    if mode not in {"diagnostic", "confirmatory"}:
        raise IntegrityError("Invalid run mode")
    if mode == "confirmatory" and (env["dirty"] is not False or not env["git_sha"]):
        raise IntegrityError("Confirmatory runs require a clean known git tree")
    if mode == "confirmatory":
        raise IntegrityError(
            "Confirmatory execution is disabled pending independent evidence gates"
        )
    for name, value in [
        ("dataset_hash", dataset_hash),
        ("config_hash", config_hash),
        ("preregistration_hash", preregistration_hash),
    ]:
        if not re.fullmatch("[0-9a-f]{64}", value):
            raise IntegrityError(f"Missing or invalid {name}")
    timestamp = datetime.now(timezone.utc).isoformat()
    run_id = (
        f"v03-{timestamp[:10]}-{seed}-{(env['git_sha'] or 'unknown')[:8]}-{uuid.uuid4().hex[:12]}"
    )
    destination = root / run_id
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    try:
        for name, value in artifacts.items():
            path = safe_path(destination, name)
            write_json(path, value)
            hashes[name] = file_hash(path)
        manifest = {
            "schema_version": "v03.1",
            "run_id": run_id,
            "timestamp": timestamp,
            "seed": seed,
            "mode": mode,
            "dataset_hash": dataset_hash,
            "config_hash": config_hash,
            "preregistration_hash": preregistration_hash,
            "environment": env,
            "artifacts": hashes,
            "metadata": metadata or {},
            "status": "COMPLETE",
        }
        write_json(destination / "manifest.json", manifest)
        (destination / "manifest.sha256").write_text(
            file_hash(destination / "manifest.json") + "\n"
        )
    except Exception as error:
        write_json(
            destination / "FAILED.json", {"status": "FAILED", "error_type": type(error).__name__}
        )
        raise
    return destination


def validate_run(directory, expected_manifest_hash=None):
    directory = Path(directory)
    expected = expected_manifest_hash or (directory / "manifest.sha256").read_text().strip()
    if file_hash(directory / "manifest.json") != expected:
        raise IntegrityError("Manifest hash mismatch")
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("status") != "COMPLETE":
        raise IntegrityError("Run is incomplete")
    for key in ("dataset_hash", "config_hash", "preregistration_hash"):
        if not re.fullmatch("[0-9a-f]{64}", manifest.get(key, "")):
            raise IntegrityError(f"Missing {key}")
    for name, sha in manifest["artifacts"].items():
        if file_hash(safe_path(directory, name)) != sha:
            raise IntegrityError(f"Artifact hash mismatch: {name}")
    return manifest
