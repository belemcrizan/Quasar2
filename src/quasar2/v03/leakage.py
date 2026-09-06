"""Fail-closed identity audits and disclosed lexical paraphrase screening."""

from collections import defaultdict
import re
import unicodedata
from quasar2.v03.contracts import IntegrityError, reject_hidden


def normalize_query(query):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", query).casefold()))


def audit(cases, *, holdout_axes=(), document_disjoint=False):
    errors, warnings = [], []
    identities = set()
    groups, queries, entities, templates, documents = (defaultdict(set) for _ in range(5))
    for case in cases:
        reject_hidden(case.state.to_dict())
        if case.query_id in identities:
            errors.append(f"duplicate query ID: {case.query_id}")
        identities.add(case.query_id)
        groups[case.group_id].add(case.split)
        queries[normalize_query(case.query)].add(case.split)
        if case.entity:
            entities[case.entity].add(case.split)
        if case.template:
            templates[case.template].add(case.split)
        for doc in case.state.evidence_ids:
            documents[doc].add(case.split)
    for name, table in [
        ("group", groups),
        ("query", queries),
        *([("entity", entities)] if "entity" in holdout_axes else []),
        *([("template", templates)] if "template" in holdout_axes else []),
        *([("document", documents)] if document_disjoint else []),
    ]:
        errors.extend(
            f"{name} overlap across splits: {key}"
            for key, splits in table.items()
            if len(splits) > 1
        )
    # Bounded screening is explicit: never imply an embedding-level audit occurred.
    candidates = list(queries.items())[:500]
    near = 0
    for index, (text, splits) in enumerate(candidates):
        tokens = set(text.split())
        for other, other_splits in candidates[index + 1 :]:
            if splits == other_splits:
                continue
            other_tokens = set(other.split())
            union = tokens | other_tokens
            if union and len(tokens & other_tokens) / len(union) >= 0.9:
                near += 1
    if near:
        warnings.append(f"{near} cross-split lexical near-duplicate pairs require review")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "n": len(cases),
        "n_groups": len(groups),
        "holdout_axes": list(holdout_axes),
        "document_overlap_count": sum(len(v) > 1 for v in documents.values()),
        "document_overlap_policy": "disjoint"
        if document_disjoint
        else "shared corpus explicitly permitted",
        "paraphrase_audit": "lexical screening only; first 500 unique queries",
        "semantic_contamination": "NOT_IDENTIFIABLE_WITH_THIS_AUDIT",
    }


def require_clean(report):
    if not report["ok"]:
        raise IntegrityError("Leakage audit failed: " + "; ".join(report["errors"][:5]))
