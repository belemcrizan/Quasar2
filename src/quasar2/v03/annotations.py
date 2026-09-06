"""Independent annotation exchange; fixtures cannot establish human agreement."""

from collections import Counter
from quasar2.v03.contracts import IntegrityError


def validate(row):
    required = {
        "query_id",
        "annotator_id",
        "provenance",
        "acceptable_answers",
        "abstain",
        "rationale",
    }
    if set(row) != required or not row["query_id"] or not row["annotator_id"]:
        raise IntegrityError("Invalid annotation schema")
    if row["provenance"] not in {"HUMAN", "FIXTURE"} or not isinstance(row["abstain"], bool):
        raise IntegrityError("Invalid annotation provenance/abstention")
    if not isinstance(row["acceptable_answers"], list) or any(
        not isinstance(x, str) or not x for x in row["acceptable_answers"]
    ):
        raise IntegrityError("Answers must be nonempty strings")
    if not row["abstain"] and not row["acceptable_answers"]:
        raise IntegrityError("Non-abstaining annotations need acceptable answers")
    if not isinstance(row["rationale"], str) or not row["rationale"].strip():
        raise IntegrityError("Rationale is required")
    return row


def agreement(first, second):
    for row in [*first, *second]:
        validate(row)
    if any(row["provenance"] != "HUMAN" for row in [*first, *second]):
        raise IntegrityError("Fixture annotations cannot establish human agreement")

    def index(rows):
        result = {r["query_id"]: r for r in rows}
        if len(result) != len(rows):
            raise IntegrityError("Duplicate annotated query")
        if len({r["annotator_id"] for r in rows}) != 1:
            raise IntegrityError("One annotator per batch required")
        return result

    a, b = index(first), index(second)
    if not a or set(a) != set(b):
        raise IntegrityError("Annotation batches must cover the same nonempty queries")
    if any(a[k]["annotator_id"] == b[k]["annotator_id"] for k in a):
        raise IntegrityError("Independent annotators required")
    label = lambda r: (r["abstain"], tuple(sorted(set(r["acceptable_answers"]))))
    left = [label(a[k]) for k in sorted(a)]
    right = [label(b[k]) for k in sorted(a)]
    observed = sum(x == y for x, y in zip(left, right)) / len(left)
    ca, cb = Counter(left), Counter(right)
    chance = sum(n * cb[key] for key, n in ca.items()) / len(left) ** 2
    return {
        "n": len(left),
        "exact_agreement": observed,
        "cohen_kappa": (observed - chance) / (1 - chance) if chance < 1 else None,
        "needs_adjudication": [k for k in sorted(a) if label(a[k]) != label(b[k])],
        "limitation": "provenance is declared, not proof of human identity or independence",
    }
