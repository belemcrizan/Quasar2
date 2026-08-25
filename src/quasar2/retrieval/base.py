"""Retrieval data structures, corpus loader, and protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class Document:
    document_id: str
    domain: str
    title: str
    text: str
    hypothesis_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def searchable_text(self) -> str:
        return " ".join((self.title, self.text, " ".join(self.tags)))


@dataclass(frozen=True, slots=True)
class SearchHit:
    document: Document
    score: float
    rank: int
    components: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", MappingProxyType(dict(self.components)))


class Retriever(Protocol):
    def search(self, query: str, *, top_k: int, domain: str | None = None) -> tuple[SearchHit, ...]:
        ...


def load_corpus(directory: str | Path) -> tuple[Document, ...]:
    root = Path(directory)
    documents: list[Document] = []
    seen: set[str] = set()
    for path in sorted(root.glob("*.jsonl")):
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            item = json.loads(raw_line)
            document_id = str(item["id"])
            if document_id in seen:
                raise ValueError(f"Duplicate document id {document_id!r} at {path}:{line_number}")
            seen.add(document_id)
            documents.append(
                Document(
                    document_id=document_id,
                    domain=str(item["domain"]),
                    title=str(item["title"]),
                    text=str(item["text"]),
                    hypothesis_ids=tuple(item.get("hypothesis_ids", ())),
                    tags=tuple(item.get("tags", ())),
                    metadata={str(k): str(v) for k, v in item.get("metadata", {}).items()},
                )
            )
    if not documents:
        raise ValueError(f"No JSONL documents found in {root}")
    return tuple(documents)


def filter_domain(documents: Sequence[Document], domain: str | None) -> list[int]:
    return [index for index, document in enumerate(documents) if domain is None or document.domain == domain]

