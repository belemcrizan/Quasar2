"""Explicit bounded acquisition. No network during dataset loading/reproduction."""

from __future__ import annotations
import csv
import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from quasar2.v03.contracts import IntegrityError
from quasar2.v03.registry import file_hash, write_json

DATASETS = {
    name: {
        "url": f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{name}.zip",
        "kind": "BEIR",
        "card": f"https://huggingface.co/datasets/BeIR/{name}",
        "provenance": "REAL",
        "query_provenance": "EXTERNAL_NATIVE",
        "redistribution": "not bundled; consult original dataset terms",
    }
    for name in ("scifact", "nfcorpus", "fiqa", "trec-covid")
}
DATASETS.update(
    {
        "nasa-exoplanet": {
            "url": "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
            "kind": "NASA_TAP",
            "card": "https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html",
            "provenance": "REAL",
            "query_provenance": "GENERATED",
            "redistribution": "not bundled; acknowledge archive and source literature",
        },
        "inspire": {
            "url": "https://inspirehep.net/api/literature",
            "kind": "INSPIRE",
            "card": "https://github.com/inspirehep/rest-api-doc",
            "provenance": "REAL",
            "query_provenance": "GENERATED",
            "redistribution": "CC0 metadata subject to field-specific restrictions; not bundled",
        },
    }
)
NASA_COLUMNS = ("pl_name", "hostname", "discoverymethod", "disc_year", "pl_orbper", "pl_rade")


class BoundedClient:
    def __init__(self, *, timeout=15, retries=1, interval=0.2, max_bytes=100_000_000, opener=None):
        import math

        if (
            isinstance(retries, bool)
            or not isinstance(retries, int)
            or isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or not math.isfinite(timeout)
            or not math.isfinite(interval)
            or timeout <= 0
            or retries < 0
            or retries > 5
            or max_bytes <= 0
            or interval < 0
        ):
            raise ValueError("Invalid acquisition bounds")
        self.timeout, self.retries, self.interval, self.max_bytes = (
            timeout,
            retries,
            interval,
            max_bytes,
        )
        self.opener = opener or urlopen

    def fetch(self, url):
        if urlparse(url).scheme != "https" or urlparse(url).username:
            raise IntegrityError("Acquisition requires HTTPS without credentials")
        error = None
        for attempt in range(self.retries + 1):
            if attempt:
                time.sleep(min(2**attempt, 8))
            try:
                time.sleep(self.interval)
                with self.opener(
                    Request(
                        url, headers={"User-Agent": "QUASAR2-v03-research/1.0", "Accept": "*/*"}
                    ),
                    timeout=self.timeout,
                ) as response:
                    data = response.read(self.max_bytes + 1)
                    if len(data) > self.max_bytes:
                        raise IntegrityError("Download exceeds configured byte limit")
                    return data
            except HTTPError as exc:
                error = exc
                if exc.code < 500 and exc.code != 429:
                    raise
            except (URLError, TimeoutError, OSError) as exc:
                error = exc
        raise RuntimeError(
            f"Acquisition failed after {self.retries + 1} attempts ({type(error).__name__})"
        ) from error


def nasa_query(limit=1000):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100000:
        raise ValueError("NASA row limit must be 1..100000")
    return f"select top {limit} {','.join(NASA_COLUMNS)} from pscomppars order by pl_name"


def validate_nasa(rows):
    if not rows:
        raise IntegrityError("Empty NASA snapshot")
    names = set()
    for row in rows:
        if not set(NASA_COLUMNS) <= set(row):
            raise IntegrityError("NASA schema mismatch")
        if not row["pl_name"] or not row["hostname"] or str(row["pl_name"]).startswith("SYN-"):
            raise IntegrityError("Missing/fixture NASA identity")
        if row["pl_name"] in names:
            raise IntegrityError("Duplicate planet in composite table")
        names.add(row["pl_name"])
        for key in ("disc_year", "pl_orbper", "pl_rade"):
            if row[key] not in ("", None):
                import math

                if not math.isfinite(float(row[key])):
                    raise IntegrityError("Non-finite NASA parameter")
    return {"ok": True, "rows": len(rows), "schema": list(NASA_COLUMNS), "table": "pscomppars"}


def sync(name, destination, *, limit=1000, dry_run=False, client=None):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100000:
        raise ValueError("Acquisition limit must be 1..100000")
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset: {name}")
    spec = dict(DATASETS[name])
    url = spec["url"]
    if name == "nasa-exoplanet":
        url += "?" + urlencode({"query": nasa_query(limit), "format": "csv"})
    if name == "inspire":
        url += "?" + urlencode(
            {
                "q": "date > 2020 and keyword neutrino",
                "size": min(limit, 250),
                "page": 1,
                "fields": "titles,abstracts,dois,document_type",
            }
        )
    plan = {"dataset": name, "url": url, "limit": limit, "source": spec, "status": "DRY_RUN"}
    if dry_run:
        return plan
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        data = (client or BoundedClient()).fetch(url)
        raw = destination / (
            "source.zip"
            if spec["kind"] == "BEIR"
            else "source.csv"
            if spec["kind"] == "NASA_TAP"
            else "source.json"
        )
        raw.write_bytes(data)
        if spec["kind"] == "BEIR":
            # Extract only expected text records. Never use extractall on remote ZIPs.
            total = 0
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                allowed = {
                    f"{name}/corpus.jsonl": "corpus.jsonl",
                    f"{name}/queries.jsonl": "queries.jsonl",
                    **{f"{name}/qrels/{s}.tsv": f"qrels/{s}.tsv" for s in ("train", "dev", "test")},
                }
                written = set()
                for item in archive.infolist():
                    if item.filename not in allowed:
                        continue
                    if item.filename in written:
                        raise IntegrityError("Duplicate ZIP member")
                    written.add(item.filename)
                    total += item.file_size
                    if total > 500_000_000:
                        raise IntegrityError("Expanded archive exceeds limit")
                    target = destination / allowed[item.filename]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(item))
            if (
                not (destination / "corpus.jsonl").is_file()
                or not (destination / "queries.jsonl").is_file()
                or not list((destination / "qrels").glob("*.tsv"))
            ):
                raise IntegrityError("BEIR archive missing corpus/queries/qrels")
        elif spec["kind"] == "NASA_TAP":
            rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
            validation = validate_nasa(rows)
            write_json(destination / "validation.json", validation)
        else:
            payload = json.loads(data)
            if (
                not isinstance(payload.get("hits", {}).get("hits"), list)
                or not payload["hits"]["hits"]
            ):
                raise IntegrityError("Invalid/empty INSPIRE response")
        manifest = {
            **plan,
            "status": "COMPLETE",
            "acquired_at": datetime.now(timezone.utc).isoformat(),
            "source_version": "mutable endpoint; frozen content hash identifies snapshot",
            "hashes": {
                str(p.relative_to(destination)): file_hash(p)
                for p in sorted(destination.rglob("*"))
                if p.is_file()
            },
        }
        write_json(destination / "dataset_manifest.json", manifest)
        return manifest
    except Exception as error:
        write_json(
            destination / "NOT_RUN.json",
            {
                **plan,
                "status": "NOT_RUN",
                "error_type": type(error).__name__,
                "reason": str(error)[:300],
            },
        )
        raise


def validate_snapshot(root):
    root = Path(root)
    manifest = json.loads((root / "dataset_manifest.json").read_text())
    if manifest.get("status") != "COMPLETE":
        raise IntegrityError("Snapshot incomplete")
    from quasar2.v03.registry import safe_path

    for name, expected in manifest["hashes"].items():
        if file_hash(safe_path(root, name)) != expected:
            raise IntegrityError(f"Dataset checksum mismatch: {name}")
    return manifest
