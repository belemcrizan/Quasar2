"""Paired clustered uncertainty, calibration, rank metrics and Pareto frontiers."""

import math
import random
from collections import defaultdict

from quasar2.math.association import spearman
from quasar2.v03.contracts import IntegrityError


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * q
    lo = int(index)
    hi = math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def paired_interval(left, right, groups, *, samples=1000, seed=42, alpha=0.05):
    if len(left) != len(right) or len(left) != len(groups) or not 0 < alpha < 1 or samples < 1:
        raise IntegrityError("Invalid paired bootstrap configuration")
    if any(not math.isfinite(x) for x in [*left, *right]):
        raise IntegrityError("Nonfinite metric")
    buckets = defaultdict(list)
    for a, b, g in zip(left, right, groups):
        buckets[g].append(a - b)
    if not buckets:
        return {
            "n": 0,
            "n_clusters": 0,
            "mean": None,
            "ci_low": None,
            "ci_high": None,
            "status": "NO_DATA",
        }
    rng = random.Random(seed)
    keys = sorted(buckets)
    draws = []
    for _ in range(samples):
        selected = [v for _ in keys for v in buckets[rng.choice(keys)]]
        draws.append(sum(selected) / len(selected))
    return {
        "n": len(left),
        "n_clusters": len(keys),
        "mean": sum(a - b for a, b in zip(left, right)) / len(left),
        "ci_low": percentile(draws, alpha / 2),
        "ci_high": percentile(draws, 1 - alpha / 2),
        "confidence": 1 - alpha,
        "samples": samples,
        "seed": seed,
        "status": "UNDERPOWERED" if len(keys) < 30 else "ESTIMATED",
    }


def stratified_interval(left, right, strata, *, samples=1000, seed=42):
    if len(left) != len(right) or len(left) != len(strata) or not left:
        raise IntegrityError("Misaligned/empty strata")
    buckets = defaultdict(list)
    for a, b, s in zip(left, right, strata):
        if not math.isfinite(a - b):
            raise IntegrityError("Nonfinite metric")
        buckets[s].append(a - b)
    rng = random.Random(seed)
    draws = [
        sum(rng.choice(values) for values in buckets.values() for _ in values) / len(left)
        for _ in range(samples)
    ]
    return {
        "n": len(left),
        "mean": sum(a - b for a, b in zip(left, right)) / len(left),
        "ci_low": percentile(draws, 0.025),
        "ci_high": percentile(draws, 0.975),
    }


def classification(scores, labels):
    if len(scores) != len(labels) or any(y not in (0, 1) for y in labels):
        raise IntegrityError("Misaligned/bad labels")
    if any(not math.isfinite(s) or not 0 <= s <= 1 for s in scores):
        raise IntegrityError("Invalid probabilities")
    if not scores:
        return {
            "n": 0,
            "auroc": None,
            "auprc": None,
            "brier": None,
            "ece": None,
            "nll": None,
            "reliability": [],
        }
    positive = sum(labels)
    negative = len(labels) - positive
    auc = None
    if positive and negative:
        ordered = sorted(zip(scores, labels))
        negative_seen = 0
        numerator = 0
        i = 0
        while i < len(ordered):
            j = i + 1
            while j < len(ordered) and ordered[j][0] == ordered[i][0]:
                j += 1
            pos = sum(y for _, y in ordered[i:j])
            neg = j - i - pos
            numerator += pos * (negative_seen + neg / 2)
            negative_seen += neg
            i = j
        auc = numerator / (positive * negative)
    grouped = defaultdict(list)
    for score, label in zip(scores, labels):
        grouped[score].append(label)
    tp = fp = 0
    ap = 0
    for score in sorted(grouped, reverse=True):
        hits = sum(grouped[score])
        tp += hits
        fp += len(grouped[score]) - hits
        if positive:
            ap += hits / positive * tp / (tp + fp)
    reliability = []
    ece = 0
    for i in range(10):
        pairs = [(s, y) for s, y in zip(scores, labels) if min(9, int(s * 10)) == i]
        if not pairs:
            continue
        n = len(pairs)
        confidence = sum(s for s, _ in pairs) / n
        freq = sum(y for _, y in pairs) / n
        z = 1.96
        den = 1 + z * z / n
        center = (freq + z * z / (2 * n)) / den
        radius = z * math.sqrt(freq * (1 - freq) / n + z * z / (4 * n * n)) / den
        reliability.append(
            {
                "bin": i,
                "n": n,
                "confidence": confidence,
                "frequency": freq,
                "ci_low": center - radius,
                "ci_high": center + radius,
            }
        )
        ece += n / len(scores) * abs(confidence - freq)
    return {
        "n": len(scores),
        "positive": positive,
        "auroc": auc,
        "auprc": ap if positive else None,
        "brier": sum((s - y) ** 2 for s, y in zip(scores, labels)) / len(scores),
        "ece": ece,
        "nll": -sum(
            y * math.log(max(1e-12, s)) + (1 - y) * math.log(max(1e-12, 1 - s))
            for s, y in zip(scores, labels)
        )
        / len(scores),
        "reliability": reliability,
        "spearman": spearman(scores, labels),
    }


def risk_coverage(confidence, correct):
    if len(confidence) != len(correct):
        raise IntegrityError("Misaligned selective metrics")
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in confidence):
        raise IntegrityError("Invalid confidence")
    buckets = defaultdict(list)
    for score, good in zip(confidence, correct):
        buckets[score].append(good)
    result = []
    errors = 0
    n = 0
    for score in sorted(buckets, reverse=True):
        n += len(buckets[score])
        errors += sum(not good for good in buckets[score])
        result.append({"n": n, "coverage": n / len(correct), "risk": errors / n})
    return result


def pareto(rows):
    return [
        row["policy"]
        for row in rows
        if not any(
            other["accuracy"] >= row["accuracy"]
            and other["cost"] <= row["cost"]
            and (other["accuracy"] > row["accuracy"] or other["cost"] < row["cost"])
            for other in rows
        )
    ]
