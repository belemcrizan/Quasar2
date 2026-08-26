"""Build benchmark states: natural schema records + controlled degradations.

Gold never enters deployment features. Cluster id is the object, not the variant.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from quasar2.cycle2.observation import finite_entropy
from quasar2.external.provenance import deployment_view
from quasar2.external.snapshots import esa_gaia_records, jwst_fixture_overlay, nasa_exo_records, obs_alma_records
from quasar2.external.taxonomy import DEGRADATION_KINDS
from quasar2.retrieval.base import Document
from quasar2.theory.kernels import bernoulli_pair, near_identical_pair

ETA = {
    "clean": 0.0,
    "lexical": 0.2,
    "missing_context": 0.35,
    "entity_removed": 0.45,
    "temporal_removed": 0.4,
    "conflicting": 0.7,
    "partial": 0.55,
    "severe": 0.9,
}


def _uid(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def degrade_query(q: str, kind: str, gold: str) -> str:
    if kind == "clean":
        return q
    if kind == "lexical":
        return q.replace("periodic", "repeating").replace("dips", "drops").replace("Gaia", "astrometric")
    if kind == "missing_context":
        tokens = q.split()
        return " ".join(tokens[: max(4, len(tokens) // 2)])
    if kind == "entity_removed":
        for token in ("Kepler", "TESS", "kepler", "tess", "Gaia", "ALMA", "JWST"):
            q = q.replace(token, "the instrument")
        return q
    if kind == "temporal_removed":
        return q + " (epoch unspecified)"
    if kind == "conflicting":
        return q + " but also consistent with an alternative astrophysical class"
    if kind == "partial":
        return q.split(",")[0]
    if kind == "severe":
        return "unidentified source variability"
    return q


def true_kernels(
    recoverability: str,
    gold: str,
    n_h: int,
    hyps: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    if hyps is None:
        hyps = ["H1", "H2"] + [f"H{i}" for i in range(3, n_h + 1)]
    if recoverability == "non_recoverable" or gold == "H_unknown":
        pair = near_identical_pair()
    else:
        pair = bernoulli_pair(0.88 if recoverability != "mismatch_sensitive" else 0.62)
    primary = gold if gold in hyps else hyps[0]
    secondary = next((h for h in hyps if h != primary), hyps[-1])
    out: dict[str, dict[str, float]] = {h: {"0": 0.5, "1": 0.5} for h in hyps}
    out[primary] = pair["H1"]
    out[secondary] = pair["H2"]
    return out


def proxy_kernels(
    recoverability: str,
    mismatch: float,
    n_h: int,
    hyps: list[str] | None = None,
    gold: str = "H1",
) -> dict[str, dict[str, float]]:
    true = true_kernels(recoverability, gold, n_h, hyps=hyps)
    if mismatch <= 0:
        return true
    keys = list(true)
    if len(keys) < 2:
        return true
    a, b = keys[0], keys[1]
    mixed = dict(true)
    mixed[a] = {
        o: (1.0 - mismatch) * true[a][o] + mismatch * true[b][o] for o in true[a]
    }
    mixed[b] = {
        o: (1.0 - mismatch) * true[b][o] + mismatch * true[a][o] for o in true[b]
    }
    return mixed


def document_for(hyp_id: str, domain: str, text: str, extra: str) -> Document:
    return Document(
        document_id=_uid(hyp_id, text[:40], extra),
        domain=domain,
        title=hyp_id,
        text=f"{hyp_id} {text} {extra}",
        hypothesis_ids=(hyp_id,),
        tags=(domain,),
        metadata={"hypothesis": hyp_id},
    )


def distractor_documents(domain: str, n: int, seed_key: str) -> list[Document]:
    docs = []
    for i in range(n):
        docs.append(
            Document(
                document_id=_uid("dist", domain, seed_key, str(i)),
                domain=domain,
                title=f"unrelated {i}",
                text=f"calibration logbook weather seeing humidity entry {i} unrelated to the science target",
                hypothesis_ids=(),
                tags=("distractor",),
            )
        )
    return docs


def records_for_source(source: str, *, n_objects: int) -> tuple[dict[str, Any], ...]:
    if source == "nasa_exo_schema":
        return nasa_exo_records(n_objects=n_objects)
    if source == "esa_gaia_schema":
        return esa_gaia_records(n_objects=n_objects)
    if source == "obs_alma_schema":
        return obs_alma_records(n_objects=n_objects)
    if source == "jwst_mast_fixture":
        return jwst_fixture_overlay()
    raise KeyError(source)


def expand_states(
    records: tuple[dict[str, Any], ...],
    *,
    degradations: tuple[str, ...] = ("clean", "lexical", "missing_context", "severe"),
    include_conflicting: bool = False,
) -> list[dict[str, Any]]:
    kinds = list(degradations)
    if include_conflicting:
        kinds.append("conflicting")
    states = []
    for rec in records:
        hyps = list(rec["candidate_hypotheses"])
        n_h = len(hyps)
        recov = str(rec["recoverability_class"])
        gold = str(rec["gold_hypothesis"])
        mismatch = 0.45 if recov == "mismatch_sensitive" else (0.25 if "misleading_proxy_evidence" in rec["ambiguity_class"] else 0.0)
        for kind in kinds:
            if kind not in DEGRADATION_KINDS:
                continue
            q = degrade_query(str(rec["q_obs"]), kind, gold)
            eta = ETA[kind]
            belief = _prior_belief(hyps, gold, eta, rec.get("open_set_status", False))
            state = {
                "state_id": _uid(rec["source_record_id"], kind),
                "source": rec["source_archive"],
                "source_record_id": rec["source_record_id"],
                "source_archive": rec["source_archive"],
                "observation_timestamp": rec["observation_timestamp"],
                "source_url": rec["source_url"],
                "persistent_id": rec["persistent_id"],
                "transformation": kind,
                "eta": eta,
                "q_obs": q,
                "candidate_hypotheses": hyps,
                "ambiguity_class": list(rec["ambiguity_class"]) + ([kind] if kind != "clean" else []),
                "recoverability_class": recov,
                "open_set_status": bool(rec["open_set_status"]),
                "channel": rec["channel"],
                "mission": rec.get("mission"),
                "instrument": rec.get("instrument"),
                "cluster_id": rec["cluster_id"],
                "object_id": rec["object_id"],
                "year": int(str(rec["observation_timestamp"])[:4]),
                "provenance_kind": rec["provenance_kind"],
                "belief": belief,
                "entropy": finite_entropy(belief),
                "unknown_mass": float(belief.get("H_unknown", 0.0)),
                "proxy_kernels": proxy_kernels(recov, mismatch, n_h, hyps=hyps, gold=gold),
                "true_kernels": true_kernels(recov, gold, n_h, hyps=hyps),
                "mismatch_mu": mismatch,
                "gold_hypothesis": gold,
                "hidden_evidence": rec["hidden_evidence"],
                "evidence_available": rec["evidence_available"],
                "ground_truth_method": "constructed_from_schema_template_or_fixture",
                "split_role": "unassigned",
            }
            states.append(state)
    return states


def _prior_belief(hyps: list[str], gold: str, eta: float, open_set: bool) -> dict[str, float]:
    n = len(hyps)
    if gold not in hyps:
        gold = "H_unknown" if "H_unknown" in hyps else hyps[0]
    # Higher eta -> flatter / more wrong mass.
    peak = max(0.2, 0.72 - 0.45 * eta)
    rest = (1.0 - peak) / max(1, n - 1)
    belief = {h: rest for h in hyps}
    belief[gold] = peak
    if open_set:
        belief["H_unknown"] = min(0.55, belief.get("H_unknown", 0.0) + 0.15 + 0.2 * eta)
        total = sum(belief.values())
        belief = {k: v / total for k, v in belief.items()}
    return belief


def corpus_for_records(
    records: tuple[dict[str, Any], ...],
    *,
    distractors: int = 20,
) -> tuple[Document, ...]:
    docs: list[Document] = []
    domain = records[0]["source_archive"] if records else "external"
    for rec in records:
        gold = rec["gold_hypothesis"]
        for hyp in rec["candidate_hypotheses"]:
            extra = rec["hidden_evidence"] if hyp == gold else "generic catalog note overlapping phenomenology"
            docs.append(document_for(hyp, domain, rec["q_obs"], extra))
        docs.append(
            document_for(
                "shared.overlap",
                domain,
                "periodic flux or compact continuum can arise from several physical classes",
                "shared",
            )
        )
    docs.extend(distractor_documents(domain, distractors, domain))
    # Unique by id
    seen: set[str] = set()
    unique = []
    for doc in docs:
        if doc.document_id in seen:
            continue
        seen.add(doc.document_id)
        unique.append(doc)
    return tuple(unique)


def freeze_state_for_policy(state: Mapping[str, Any]) -> dict[str, Any]:
    return deployment_view(
        {
            "q_obs": state["q_obs"],
            "belief": state["belief"],
            "entropy": state["entropy"],
            "unknown_mass": state["unknown_mass"],
            "proxy_kernels": state["proxy_kernels"],
            "channel": state["channel"],
            "evidence_available": state.get("evidence_available", []),
            "eta": state["eta"],
        }
    )


def assign_splits(
    states: list[dict[str, Any]],
    *,
    temporal_cutoff: int = 2020,
) -> list[dict[str, Any]]:
    """Development is astronomy-like NASA Kepler channel pre-cutoff; others are transfer."""

    for state in states:
        src = state["source"]
        year = int(state["year"])
        channel = str(state["channel"])
        if src == "nasa_exo_schema" and channel == "kepler" and year <= temporal_cutoff and state["transformation"] == "clean":
            state["split_role"] = "development"
        elif src == "nasa_exo_schema" and year > temporal_cutoff:
            state["split_role"] = "temporal_holdout"
        elif src == "nasa_exo_schema" and channel == "tess":
            state["split_role"] = "cross_instrument"
        elif src == "esa_gaia_schema":
            state["split_role"] = "external_esa"
        elif src == "obs_alma_schema":
            state["split_role"] = "external_observatory"
        elif src == "jwst_mast_fixture":
            state["split_role"] = "external_mast_fixture"
        else:
            state["split_role"] = "external_nasa"
    return states
