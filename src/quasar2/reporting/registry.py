"""Experiment run directories that refuse silent overwrite."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping

from quasar2 import __version__


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    seed: int | None
    config_hash: str | None
    dataset_hash: str | None
    git_sha: str | None
    python_version: str
    package_version: str
    timestamp: str
    command: str | None = None


def _git_sha(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def hash_mapping(values: Mapping[str, Any] | None) -> str | None:
    if values is None:
        return None
    encoded = json.dumps(values, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def allocate_run_dir(
    base: str | Path,
    *,
    run_id: str | None = None,
    overwrite: bool = False,
) -> Path:
    dest_parent = Path(base)
    dest_parent.mkdir(parents=True, exist_ok=True)
    ident = run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    dest = dest_parent / ident
    if dest.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing run directory {dest}. "
            "Pass overwrite=True or choose a new run_id."
        )
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def write_manifest(
    dest: Path,
    *,
    seed: int | None = None,
    config: Mapping[str, Any] | None = None,
    dataset_hash: str | None = None,
    command: str | None = None,
    root: Path | None = None,
) -> RunManifest:
    manifest = RunManifest(
        run_id=dest.name,
        seed=seed,
        config_hash=hash_mapping(config),
        dataset_hash=dataset_hash,
        git_sha=_git_sha(root or dest),
        python_version=sys.version.split()[0],
        package_version=__version__,
        timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        command=command,
    )
    (dest / "manifest.json").write_text(
        json.dumps(asdict(manifest), indent=2),
        encoding="utf-8",
    )
    if config is not None:
        (dest / "config.json").write_text(
            json.dumps(dict(config), indent=2, default=str),
            encoding="utf-8",
        )
    env = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "package_version": __version__,
        "git_sha": manifest.git_sha,
    }
    (dest / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    return manifest
