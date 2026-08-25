"""Deterministic multi-signal extraction.

This stage deliberately avoids pretending that query normalization recovers the
latent intent.  It emits weak lexical, entity, phrase, and quality signals that
later stages can interpret under competing hypotheses.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable, Mapping

from quasar2.models.observation import Observation


_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?")
_ENTITY_RE = re.compile(r"\b(?:[A-Z]{2,}[A-Z0-9-]*|\d+(?:\.\d+)?)\b")
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
        "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
        "what", "when", "where", "which", "why", "with", "does", "do", "my",
        "um", "uma", "e", "o", "a", "os", "as", "de", "da", "do", "das", "dos",
        "em", "no", "na", "nos", "nas", "para", "por", "que", "como", "isso",
        "meu", "minha", "quando", "qual", "porque", "com", "sem", "tem", "fica",
    }
)


def normalize_text(text: str) -> str:
    """Lowercase, remove accents, and normalize punctuation/whitespace."""

    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    tokens = _TOKEN_RE.findall(ascii_text.lower())
    return " ".join(tokens)


def tokenize(text: str, *, remove_stopwords: bool = True) -> tuple[str, ...]:
    tokens = tuple(_TOKEN_RE.findall(normalize_text(text)))
    if not remove_stopwords:
        return tokens
    return tuple(token for token in tokens if token not in _STOPWORDS and len(token) > 1)


class SignalExtractor:
    """Extract observable signals and estimate query information quality."""

    def __init__(self, domain_cues: Mapping[str, Iterable[str]] | None = None) -> None:
        self.domain_cues = {
            domain: frozenset(tokenize(" ".join(cues)))
            for domain, cues in (domain_cues or {}).items()
        }

    def extract(
        self,
        query: str,
        domain: str,
        *,
        observation_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Observation:
        normalized = normalize_text(query)
        tokens = tokenize(query)
        unique_tokens = tuple(dict.fromkeys(tokens))
        bigrams = tuple(
            f"{left} {right}" for left, right in zip(unique_tokens, unique_tokens[1:])
        )
        entities = tuple(dict.fromkeys(_ENTITY_RE.findall(query)))
        cue_set = self.domain_cues.get(domain, frozenset())
        cue_coverage = len(set(unique_tokens) & cue_set) / max(1, min(3, len(cue_set)))
        token_signal = min(1.0, len(unique_tokens) / 7.0)
        phrase_signal = min(1.0, len(bigrams) / 5.0)
        entity_signal = min(1.0, len(entities) / 2.0)
        quality = min(
            1.0,
            0.60 * token_signal + 0.15 * phrase_signal + 0.15 * entity_signal + 0.10 * cue_coverage,
        )
        stable_id = observation_id or hashlib.sha1(
            f"{domain}\0{normalized}".encode("utf-8")
        ).hexdigest()[:12]
        return Observation(
            observation_id=stable_id,
            raw_query=query,
            domain=domain,
            normalized_query=normalized,
            tokens=unique_tokens,
            entities=entities,
            bigrams=bigrams,
            signal_quality=quality,
            estimated_degradation=1.0 - quality,
            metadata=metadata or {},
        )

