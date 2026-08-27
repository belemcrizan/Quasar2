"""Runtime sanitization. Not a production attestation."""

from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.parse import urlparse

SECRET_RE = re.compile(r"(api[_-]?key|secret|password|token)\s*[:=]\s*\S+", re.I)
INJECTION_MARKERS = ("ignore previous", "system:", "<script", "drop table")
PRIVATE_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def redact_text(text: str) -> str:
    return SECRET_RE.sub("[REDACTED]", text)


def sanitize_ask(question: str) -> str:
    cleaned = redact_text(question.strip())
    for marker in INJECTION_MARKERS:
        if marker in cleaned.lower():
            cleaned = cleaned.replace(marker, "[BLOCKED]")
    return cleaned[:500]


def allow_url(url: str, *, allowlist: tuple[str, ...] = ()) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if host in PRIVATE_HOSTS or host.endswith(".local"):
        return False
    if allowlist and host not in allowlist and not any(host.endswith("." + item) for item in allowlist):
        return False
    return True


def sanitize_document_text(text: str) -> str:
    return redact_text(text.replace("\x00", ""))


def threat_findings(payload: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    blob = str(payload)
    if SECRET_RE.search(blob):
        findings.append("secret_pattern")
    if any(marker in blob.lower() for marker in INJECTION_MARKERS):
        findings.append("injection_marker")
    return findings
