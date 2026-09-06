"""External IR adapters and counterfactual datasets with explicit query provenance."""

from __future__ import annotations
import csv
import json
import math
import random
import time
from pathlib import Path
from typing import Protocol

from quasar2.retrieval.base import Document
from quasar2.retrieval.factory import build_retriever
from quasar2.v03.acquisition import validate_snapshot, validate_nasa
from quasar2.v03.contracts import (
    Action,
    Case,
    Costs,
    FEATURES,
    IntegrityError,
    Outcome,
    RuntimeState,
)
from quasar2.v03.registry import digest, write_json
from quasar2.v03.splits import assign_split


class ExternalIRDataset(Protocol):
    def corpus(self) -> tuple[Document, ...]: ...
    def queries(self) -> dict[str, str]: ...
    def qrels(self) -> dict[str, dict[str, int]]: ...
    def metadata(self) -> dict: ...
    def split(self, query_id: str) -> str: ...
    def license(self) -> str: ...


class BEIRDataset:
    def __init__(self, root, *, verify=True):
        self.root = Path(root)
        self.manifest = (
            validate_snapshot(root)
            if verify
            else {
                "dataset": "fixture",
                "source": {"provenance": "FIXTURE", "query_provenance": "FIXTURE"},
            }
        )

        def records(name):
            out = {}
            for line in (self.root / name).read_text().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                key = str(row["_id"])
                if key in out:
                    raise IntegrityError("Duplicate external ID")
                out[key] = row
            return out

        corpus = records("corpus.jsonl")
        queries = records("queries.jsonl")
        self._corpus = tuple(
            Document(key, self.manifest["dataset"], str(row.get("title", "")), str(row["text"]))
            for key, row in corpus.items()
        )
        self._queries = {key: str(row["text"]) for key, row in queries.items()}
        self._qrels = {}
        self._splits = {}
        for file in sorted((self.root / "qrels").glob("*.tsv")):
            with file.open() as stream:
                for row in csv.DictReader(stream, delimiter="\t"):
                    q, d = str(row["query-id"]), str(row["corpus-id"])
                    score = int(row["score"])
                    if q not in queries or d not in corpus:
                        raise IntegrityError("Orphan qrel")
                    if q in self._splits and self._splits[q] != file.stem:
                        raise IntegrityError("Query appears in multiple official splits")
                    if d in self._qrels.setdefault(q, {}):
                        raise IntegrityError("Duplicate relevance judgment")
                    self._splits[q] = file.stem
                    self._qrels[q][d] = score
        if not self._corpus or not self._qrels:
            raise IntegrityError("Empty external IR dataset")

    def corpus(self):
        return self._corpus

    def queries(self):
        return {q: self._queries[q] for q in self._qrels}

    def qrels(self):
        return self._qrels

    def metadata(self):
        return self.manifest

    def license(self):
        return self.manifest["source"].get("redistribution", "fixture only")

    def split(self, query_id):
        original = self._splits[query_id]
        if original == "test":
            return "test"
        assigned = assign_split(query_id)
        if original == "dev":
            return "calibration" if assigned == "calibration" else "development"
        return assigned if assigned != "test" else "train"


class ScientificDataset:
    def __init__(self, root):
        self.root = Path(root)
        self.manifest = validate_snapshot(root)
        self._corpus = []
        self._queries = {}
        self._qrels = {}
        self.groups = {}
        self.languages = {}
        name = self.manifest["dataset"]
        if name == "nasa-exoplanet":
            with (self.root / "source.csv").open(encoding="utf-8-sig") as stream:
                rows = list(csv.DictReader(stream))
            validate_nasa(rows)
            for row in rows:
                key = row["pl_name"]
                host = row["hostname"]
                self._corpus.append(
                    Document(key, name, key, " ".join(f"{k} {v}" for k, v in row.items()))
                )
                for suffix, query, language in [
                    ("identity", f"Which observations describe {key}?", "en"),
                    ("host", f"Planet of {host}, discovery method and orbital period", "en"),
                    ("pt", f"Qual o período orbital e o método de descoberta de {key}?", "pt"),
                ]:
                    qid = f"{key}:{suffix}"
                    self._queries[qid] = query
                    # Group every planet of a host, including shared host queries.
                    self.groups[qid] = host
                    self.languages[qid] = language
                    self._qrels[qid] = {
                        r["pl_name"]: 1
                        for r in rows
                        if (r["hostname"] == host if suffix == "host" else r["pl_name"] == key)
                    }
        elif name == "inspire":
            rows = json.loads((self.root / "source.json").read_text())["hits"]["hits"]
            for row in rows:
                metadata = row["metadata"]
                key = str(row["id"])
                title = metadata["titles"][0]["title"]
                abstract = " ".join(x.get("value", "") for x in metadata.get("abstracts", []))
                self._corpus.append(Document(key, name, title, abstract))
                self._queries[key] = "Find research about " + " ".join(title.split()[:8])
                self._qrels[key] = {key: 1}
                self.groups[key] = key
                self.languages[key] = "en"
        else:
            raise IntegrityError("Not a supported scientific snapshot")
        # Host questions repeat verbatim across planets. Keep one per query text,
        # preserving the whole acceptable relevance set, before any model runs.
        seen = set()
        for qid in list(self._queries):
            if self._queries[qid] in seen:
                del self._queries[qid]
                del self._qrels[qid]
            else:
                seen.add(self._queries[qid])

    def corpus(self):
        return tuple(self._corpus)

    def queries(self):
        return self._queries

    def qrels(self):
        return self._qrels

    def metadata(self):
        return self.manifest

    def license(self):
        return self.manifest["source"]["redistribution"]

    def split(self, query_id):
        return assign_split(self.groups[query_id])


def features_from_hits(query, hits):
    scores = [max(0, h.score) for h in hits]
    total = sum(scores)
    probs = [s / total for s in scores] if total else []
    confidence = probs[0] if probs else 0
    margin = confidence - (probs[1] if len(probs) > 1 else 0)
    entropy = (
        -sum(p * math.log(p) for p in probs if p) / math.log(len(probs)) if len(probs) > 1 else 0
    )
    terms = set(query.lower().split())
    covered = set()
    for hit in hits:
        covered |= terms.intersection(hit.document.searchable_text.lower().split())
    coverage = len(covered) / max(1, len(terms))
    values = dict.fromkeys(FEATURES, 0.0)
    values.update(
        entropy=entropy,
        margin=margin,
        confidence=confidence,
        recoverability=coverage * (1 - margin),
        decision_relevance=1 - confidence,
        coverage=coverage,
        novelty=1 - coverage,
        unknown_mass=1 - coverage,
        score_dispersion=(max(scores) - min(scores)) / max(scores) if scores and max(scores) else 0,
        query_length=len(query.split()),
        evidence_count=len(hits),
        previous_calls=1,
        estimated_cost=0.05,
    )
    return RuntimeState(values, tuple(hit.document.document_id for hit in hits))


def fuse(first, second):
    scores = {}
    docs = {}
    for hits in (first, second):
        for hit in hits:
            key = hit.document.document_id
            docs[key] = hit.document
            scores[key] = scores.get(key, 0) + 1 / (20 + hit.rank)
    return sorted(scores, key=lambda key: (-scores[key], key))


def build_ir_cases(
    dataset, *, retriever="bm25", additional="dense_hash", limit=None, settings=None
):
    if retriever in {"hybrid", "hybrid_neural", "hybrid_bge"} or additional in {
        "hybrid",
        "hybrid_neural",
        "hybrid_bge",
    }:
        raise IntegrityError(
            "Primary action-count experiment needs single-call backends; use cached fusion instead"
        )
    corpus = dataset.corpus()
    first = build_retriever(corpus, retriever, settings)
    second = build_retriever(corpus, additional, settings)
    # Explicit warmup excluded from per-query timings, not hidden in outcome cost.
    first.search("warmup", top_k=10)
    second.search("warmup", top_k=10)
    queries = dataset.queries()
    qids = sorted(queries)
    if limit is not None:
        if limit <= 0:
            raise IntegrityError("Limit must be positive")
        qids = qids[:limit]
    cases = []
    retrieval = []
    for qid in qids:
        query = queries[qid]
        start = time.perf_counter()
        initial = first.search(query, top_k=10)
        first_ms = (time.perf_counter() - start) * 1000
        state = features_from_hits(query, initial)  # frozen BEFORE second retrieval
        start = time.perf_counter()
        extra = second.search(query, top_k=10)
        extra_ms = (time.perf_counter() - start) * 1000
        merged = fuse(initial, extra)
        relevant = {key for key, value in dataset.qrels()[qid].items() if value > 0}
        top = initial[0].document.document_id if initial else None
        evidence = tuple(
            dict.fromkeys((*state.evidence_ids, *(h.document.document_id for h in extra)))
        )
        stop = Outcome(
            Action.ANSWER,
            top in relevant,
            Costs(retrieval_calls=1, documents=len(initial), latency_ms=first_ms),
            state.evidence_ids,
        )
        action = Outcome(
            Action.EXPLORE,
            bool(merged and merged[0] in relevant),
            Costs(
                retrieval_calls=2,
                documents=len(initial) + len(extra),
                latency_ms=first_ms + extra_ms,
            ),
            evidence,
        )
        cases.append(
            Case(
                qid,
                query,
                getattr(dataset, "groups", {}).get(qid, qid),
                dataset.metadata()["dataset"],
                dataset.split(qid),
                state,
                stop,
                action,
                language=getattr(dataset, "languages", {}).get(qid, "en"),
                open_set=not relevant,
            )
        )
        ids = [h.document.document_id for h in initial]
        gain = lambda ids: sum(
            (2 ** dataset.qrels()[qid].get(doc, 0) - 1) / math.log2(i + 2)
            for i, doc in enumerate(ids[:10])
        )
        ideal = sum(
            (2**v - 1) / math.log2(i + 2)
            for i, v in enumerate(sorted(dataset.qrels()[qid].values(), reverse=True)[:10])
        )
        retrieval.append(
            {
                "query_id": qid,
                "recall_at_10": len(set(ids) & relevant) / len(relevant) if relevant else None,
                "mrr": next((1 / (i + 1) for i, key in enumerate(ids) if key in relevant), 0),
                "ndcg_at_10": gain(ids) / ideal if ideal else None,
                "initial_ms": first_ms,
                "additional_ms": extra_ms,
            }
        )
    meta = {
        "dataset": dataset.metadata()["dataset"],
        "source_manifest": dataset.metadata(),
        "query_provenance": dataset.metadata()["source"]["query_provenance"],
        "retriever": retriever,
        "additional": additional,
        "n_corpus": len(corpus),
        "limit": limit,
        "correctness": "qrels top-1 relevance surrogate, NOT answer correctness",
        "counterfactuals": "OBSERVED; both retrieval arms executed from same pre-action state",
        "timing": "one warmup/backend; measured retrieval only, index construction excluded",
        "retrieval_metrics": retrieval,
    }
    return tuple(cases), meta


def save_cases(path, cases, metadata):
    rows = [case.to_dict() for case in cases]
    payload = {"schema_version": "v03.1", "metadata": metadata, "cases": rows}
    payload["dataset_hash"] = digest(payload)
    write_json(path, payload)
    return payload


def load_cases(path):
    import gzip

    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as stream:
            data = stream.read(100_000_001)
        if len(data) > 100_000_000:
            raise IntegrityError("Expanded case dataset exceeds limit")
        payload = json.loads(data)
    else:
        payload = json.loads(path.read_text())
    expected = payload.pop("dataset_hash")
    if digest(payload) != expected:
        raise IntegrityError("R* dataset hash mismatch")
    return tuple(Case.from_dict(row) for row in payload["cases"]), payload["metadata"], expected


def synthetic_cases(n=600, seed=42):
    rng = random.Random(seed)
    cases = []
    for i in range(n):
        high_uncertainty = (i % 4) // 2
        high_recovery = i % 2
        uncertainty = 0.7 + 0.25 * rng.random() if high_uncertainty else 0.05 + 0.2 * rng.random()
        latent = 0.7 if high_recovery else 0.02
        # Pre-action proxy is noisy and imperfect; outcome uses independent draws.
        proxy = max(0, min(1, latent + rng.gauss(0, 0.25)))
        relevant = rng.random() > 0.25
        before = rng.random() > uncertainty * 0.7
        after = (before and rng.random() > 0.08) or (
            not before and rng.random() < latent and relevant
        )
        if i % 17 == 0:
            before = after = False
        values = dict.fromkeys(FEATURES, 0.0)
        values.update(
            entropy=uncertainty,
            confidence=1 - uncertainty,
            margin=1 - uncertainty,
            recoverability=proxy,
            decision_relevance=0.8 if relevant else 0.2,
            coverage=0.5,
            novelty=0.5,
            unknown_mass=0.7 if i % 17 == 0 else 0.1,
            evidence_count=1,
            previous_calls=1,
            query_length=5,
            estimated_cost=0.05,
        )
        state = RuntimeState(values, (f"initial-{i}",))
        qid = f"synthetic-{i}"
        cases.append(
            Case(
                qid,
                f"controlled observation case {i}",
                qid,
                "synthetic",
                assign_split(qid),
                state,
                Outcome(
                    Action.ANSWER, before, Costs(retrieval_calls=1), state.evidence_ids, "SIMULATED"
                ),
                Outcome(
                    Action.EXPLORE,
                    after,
                    Costs(retrieval_calls=2),
                    (f"initial-{i}", f"new-{i}"),
                    "SIMULATED",
                ),
                open_set=i % 17 == 0,
                regime=f"R{high_uncertainty * 2 + high_recovery + 1}",
            )
        )
    return tuple(cases), {
        "dataset": "synthetic",
        "query_provenance": "SYNTHETIC",
        "source_provenance": "SYNTHETIC",
        "seed": seed,
        "n": n,
        "limit": None,
        "correctness": "simulated terminal correctness; not external evidence",
        "regime_note": "four controlled uncertainty/recoverability regimes; decision relevance independently varied",
    }
