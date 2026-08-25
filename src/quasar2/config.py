"""Configuration loading with no mandatory third-party dependency.

The distributed ``*.yaml`` files use JSON syntax, which is a valid subset of
YAML 1.2.  This lets the POC remain installable offline while keeping familiar
YAML filenames.  If a user writes conventional YAML, PyYAML is used when it is
available and an actionable error is raised otherwise.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


def load_structured(path: str | Path) -> dict[str, Any]:
    """Load JSON or YAML and require a mapping at the document root."""

    source = Path(path)
    raw = source.read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as json_error:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as import_error:
            raise ValueError(
                f"{source} is not JSON-compatible YAML. Install PyYAML to read "
                "general YAML syntax."
            ) from import_error
        value = yaml.safe_load(raw)
        if value is None:
            value = {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object at the root of {source}")
    return value


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge an override without mutating either input."""

    merged = deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def discover_project_root(start: str | Path | None = None) -> Path:
    """Find the nearest directory containing both pyproject and configs."""

    cursor = Path(start or Path.cwd()).resolve()
    for candidate in (cursor, *cursor.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "configs").is_dir():
            return candidate
    # Installed-package fallback: src/quasar2/config.py -> project root.
    package_root = Path(__file__).resolve().parents[2]
    if (package_root / "pyproject.toml").exists():
        return package_root
    raise FileNotFoundError("Could not locate the QUASAR2 project root")


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Resolved POC configuration and its owning project root."""

    root: Path
    values: Mapping[str, Any]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ProjectConfig":
        config_path = Path(path).resolve() if path else discover_project_root() / "configs/poc.yaml"
        return cls(root=config_path.parent.parent, values=load_structured(config_path))

    def section(self, name: str) -> Mapping[str, Any]:
        value = self.values.get(name, {})
        if not isinstance(value, Mapping):
            raise ValueError(f"Configuration section {name!r} must be an object")
        return value

    def resolve(self, configured_path: str) -> Path:
        return (self.root / configured_path).resolve()

