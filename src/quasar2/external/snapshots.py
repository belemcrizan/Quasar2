"""Schema-faithful frozen snapshots. Not live NASA/ESA bulk dumps.

Official identifiers appear only for in-repo MAST fixtures (already present).
All other object ids are prefixed SYN- and must not be cited as archive rows.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from quasar2.sources.fixtures import JWST_FIXTURE_RECORDS

SNAPSHOT_ID = "ext-schema-2026-08-26-offline"
SCHEMA_VERSION = "external.snapshot.1"


def _hid(prefix: str, n: int) -> str:
    return f"{prefix}.{n:03d}"


def nasa_exo_records(*, n_objects: int = 48) -> tuple[dict[str, Any], ...]:
    """KOI/TOI-like schema. Dispositions are constructed, not TAP-fetched."""

    hypotheses = (
        "nasa.transit_planet",
        "nasa.eclipsing_binary",
        "nasa.stellar_activity",
        "nasa.background_blend",
        "H_unknown",
    )
    channels = ("kepler", "tess")
    records = []
    for i in range(n_objects):
        gold = hypotheses[i % 5]
        channel = channels[i % 2]
        year = 2014 + (i % 10)
        depth_ppm = 200 + (i * 37) % 8000
        period = 0.8 + (i % 29) * 0.41
        odd_even = 0.02 + (i % 7) * 0.08
        ruwe_like = 0.9 + (i % 5) * 0.35
        records.append(
            {
                "source_record_id": f"SYN-KOI-{80000 + i}",
                "source_archive": "nasa_exoplanet_archive_schema",
                "organization": "NASA/IPAC NExScI",
                "provenance_kind": "SCHEMA_FAITHFUL_SYNTHETIC",
                "live_fetch": False,
                "observation_timestamp": f"{year}-06-15",
                "source_url": "https://exoplanetarchive.ipac.caltech.edu/",
                "persistent_id": f"SYN-KOI-{80000 + i}",
                "instrument": "Kepler" if channel == "kepler" else "TESS",
                "mission": channel,
                "schema_fields": {
                    "koi_period": round(period, 4),
                    "koi_depth": depth_ppm,
                    "koi_disposition": "CANDIDATE" if gold != "H_unknown" else "NOT_DISPOSITIONED",
                    "odd_even_depth_ratio": round(odd_even, 3),
                    "centroid_offset": round((i % 3) * 0.4, 3),
                },
                "q_obs": _nasa_query(gold, channel, depth_ppm, period),
                "candidate_hypotheses": list(hypotheses),
                "gold_hypothesis": gold,
                "ambiguity_class": _nasa_amb(gold, i),
                "recoverability_class": "non_recoverable" if gold == "H_unknown" or i % 11 == 0 else "recoverable",
                "open_set_status": gold == "H_unknown",
                "hidden_evidence": _nasa_hidden(gold, odd_even, ruwe_like),
                "evidence_available": ["period", "depth", "mission_photometry_summary"],
                "channel": channel,
                "cluster_id": f"nasa-obj-{i // 3}",
                "object_id": f"nasa-obj-{i // 3}",
            }
        )
    return tuple(records)


def esa_gaia_records(*, n_objects: int = 48) -> tuple[dict[str, Any], ...]:
    hypotheses = (
        "esa.single_star",
        "esa.unresolved_binary",
        "esa.spurious_astrometry",
        "H_unknown",
    )
    channels = ("gaia_edr3_astrometry", "gaia_xp_bp_rp")
    records = []
    for i in range(n_objects):
        gold = hypotheses[i % 4]
        channel = channels[i % 2]
        year = 2016 + (i % 6)
        ruwe = 0.95 + (i % 9) * 0.22
        records.append(
            {
                "source_record_id": f"SYN-Gaia-{410000000 + i}",
                "source_archive": "esa_gaia_archive_schema",
                "organization": "ESA/ESAC",
                "provenance_kind": "SCHEMA_FAITHFUL_SYNTHETIC",
                "live_fetch": False,
                "observation_timestamp": f"{year}-09-01",
                "source_url": "https://gea.esac.esa.int/archive/",
                "persistent_id": f"SYN-Gaia-{410000000 + i}",
                "instrument": "Gaia",
                "mission": "Gaia",
                "schema_fields": {
                    "ruwe": round(ruwe, 3),
                    "astrometric_excess_noise": round((i % 8) * 0.15, 3),
                    "phot_g_mean_mag": round(12.0 + (i % 11) * 0.4, 2),
                    "channel": channel,
                },
                "q_obs": _gaia_query(gold, channel, ruwe),
                "candidate_hypotheses": list(hypotheses),
                "gold_hypothesis": gold,
                "ambiguity_class": _gaia_amb(gold, channel),
                "recoverability_class": "mismatch_sensitive" if channel.endswith("xp_bp_rp") else (
                    "non_recoverable" if gold == "H_unknown" else "recoverable"
                ),
                "open_set_status": gold == "H_unknown",
                "hidden_evidence": _gaia_hidden(gold, ruwe),
                "evidence_available": ["ruwe_summary", "g_mag"],
                "channel": channel,
                "cluster_id": f"gaia-obj-{i // 3}",
                "object_id": f"gaia-obj-{i // 3}",
            }
        )
    return tuple(records)


def obs_alma_records(*, n_objects: int = 48) -> tuple[dict[str, Any], ...]:
    hypotheses = (
        "obs.disk",
        "obs.envelope",
        "obs.outflow",
        "obs.calibration_artifact",
        "H_unknown",
    )
    channels = ("band6", "band7")
    records = []
    for i in range(n_objects):
        gold = hypotheses[i % 5]
        channel = channels[i % 2]
        year = 2015 + (i % 9)
        records.append(
            {
                "source_record_id": f"SYN-ALMA-{2015 + i:04d}.1.00{i % 90:02d}.S",
                "source_archive": "alma_science_archive_schema",
                "organization": "JAO / ESO / NRAO / NAOJ",
                "provenance_kind": "SCHEMA_FAITHFUL_SYNTHETIC",
                "live_fetch": False,
                "observation_timestamp": f"{year}-03-20",
                "source_url": "https://almascience.eso.org/aq/",
                "persistent_id": f"SYN-ALMA-PROJ-{i:04d}",
                "instrument": "ALMA",
                "mission": "ALMA",
                "schema_fields": {
                    "band": 6 if channel == "band6" else 7,
                    "array": "12m" if i % 3 else "7m",
                    "continuum_peak_mjy": round(0.4 + (i % 15) * 0.11, 3),
                },
                "q_obs": _alma_query(gold, channel),
                "candidate_hypotheses": list(hypotheses),
                "gold_hypothesis": gold,
                "ambiguity_class": _alma_amb(gold),
                "recoverability_class": "mismatch_sensitive" if channel == "band7" else (
                    "non_recoverable" if gold in {"obs.calibration_artifact", "H_unknown"} and i % 4 == 0 else "recoverable"
                ),
                "open_set_status": gold == "H_unknown",
                "hidden_evidence": _alma_hidden(gold),
                "evidence_available": ["band", "continuum_peak"],
                "channel": channel,
                "cluster_id": f"alma-obj-{i // 3}",
                "object_id": f"alma-obj-{i // 3}",
            }
        )
    return tuple(records)


def jwst_fixture_overlay() -> tuple[dict[str, Any], ...]:
    """Existing MAST fixture: official-fixture metadata, not a completed JWST bench."""

    out = []
    for rec in JWST_FIXTURE_RECORDS:
        out.append(
            {
                "source_record_id": rec["record_id"],
                "source_archive": "jwst_mast_fixture",
                "organization": "STScI/NASA",
                "provenance_kind": "OFFICIAL_FIXTURE_METADATA",
                "live_fetch": False,
                "observation_timestamp": rec.get("observed_at"),
                "source_url": "https://mast.stsci.edu/",
                "persistent_id": rec["record_id"],
                "instrument": rec.get("instrument"),
                "mission": "JWST",
                "schema_fields": {k: rec[k] for k in rec if k != "record_id"},
                "q_obs": f"JWST {rec.get('instrument')} observation of {rec.get('target')} program {rec.get('program')}",
                "candidate_hypotheses": ["jwst.calibrated_product", "jwst.reprocessed_product", "H_unknown"],
                "gold_hypothesis": "jwst.reprocessed_product" if rec.get("supersedes") else "jwst.calibrated_product",
                "ambiguity_class": ["incomplete_context", "temporal_ambiguity"],
                "recoverability_class": "recoverable",
                "open_set_status": False,
                "hidden_evidence": rec.get("crds_context"),
                "evidence_available": ["instrument", "program", "target"],
                "channel": str(rec.get("instrument")),
                "cluster_id": f"jwst-{rec.get('target')}",
                "object_id": str(rec.get("target")),
            }
        )
    return tuple(out)


def _nasa_query(gold: str, channel: str, depth: int, period: float) -> str:
    if gold == "nasa.transit_planet":
        return f"{channel} light curve shows periodic {depth} ppm dips every {period:.2f} days"
    if gold == "nasa.eclipsing_binary":
        return f"{channel} photometry: V-shaped dips {depth} ppm, period {period:.2f} d, possible secondary"
    if gold == "nasa.stellar_activity":
        return f"{channel} quasi-periodic dimming {depth} ppm near {period:.2f} d, spotted star language"
    if gold == "nasa.background_blend":
        return f"{channel} shallow {depth} ppm events at {period:.2f} d in a crowded pixel"
    return f"{channel} unexplained periodic flux drop {depth} ppm timescale {period:.2f} d"


def _nasa_hidden(gold: str, odd_even: float, ruwe: float) -> str:
    if gold == "nasa.transit_planet":
        return f"odd-even consistent ({odd_even:.2f}); no secondary; centroid on target"
    if gold == "nasa.eclipsing_binary":
        return f"odd-even {odd_even:.2f}; secondary eclipse detected"
    if gold == "nasa.stellar_activity":
        return "spot phase evolution; chromatic amplitude"
    if gold == "nasa.background_blend":
        return "centroid offset significant; neighbor EB"
    return f"no catalog match; ruwe-like {ruwe:.2f}"


def _nasa_amb(gold: str, i: int) -> list[str]:
    labels = ["observational_degeneracy", "semantic_ambiguity"]
    if gold == "H_unknown":
        labels.extend(["open_set", "non_recoverable_ambiguity"])
    else:
        labels.append("recoverable_ambiguity")
    if i % 11 == 0:
        labels.append("misleading_proxy_evidence")
    if i % 5 == 0:
        labels.append("incomplete_context")
    return labels


def _gaia_query(gold: str, channel: str, ruwe: float) -> str:
    if gold == "esa.single_star":
        return f"Gaia source with RUWE {ruwe:.2f} on {channel}; astrometry looks ordinary"
    if gold == "esa.unresolved_binary":
        return f"Gaia source RUWE {ruwe:.2f} on {channel}; excess noise, possible NSS"
    if gold == "esa.spurious_astrometry":
        return f"Gaia {channel} solution with RUWE {ruwe:.2f} in a crowded field"
    return f"Gaia {channel} object RUWE {ruwe:.2f} without class"


def _gaia_hidden(gold: str, ruwe: float) -> str:
    if gold == "esa.unresolved_binary":
        return f"NSS orbital table hit; RUWE {ruwe:.2f}"
    if gold == "esa.spurious_astrometry":
        return "scan-angle dependent residuals; duplicated source"
    if gold == "esa.single_star":
        return "NSS null; excess noise consistent with zero"
    return "not in NSS or single-star gold set"


def _gaia_amb(gold: str, channel: str) -> list[str]:
    labels = ["observational_degeneracy"]
    if "xp" in channel:
        labels.append("misleading_proxy_evidence")
    if gold == "H_unknown":
        labels.extend(["open_set", "non_recoverable_ambiguity"])
    else:
        labels.append("recoverable_ambiguity")
    return labels


def _alma_query(gold: str, channel: str) -> str:
    if gold == "obs.disk":
        return f"ALMA {channel} compact continuum around a young star, possible disk"
    if gold == "obs.envelope":
        return f"ALMA {channel} extended dusty emission, infalling envelope language"
    if gold == "obs.outflow":
        return f"ALMA {channel} bipolar residual, possible molecular outflow"
    if gold == "obs.calibration_artifact":
        return f"ALMA {channel} stripe-like residual after selfcal"
    return f"ALMA {channel} unidentified mm source"


def _alma_hidden(gold: str) -> str:
    mapping = {
        "obs.disk": "Keplerian CO gradient",
        "obs.envelope": "infall asymmetry in thick tracer",
        "obs.outflow": "high-velocity SiO wings",
        "obs.calibration_artifact": "phase-cal leak; disappears in independent EB",
        "H_unknown": "no kinematic discriminator in band",
    }
    return mapping[gold]


def _alma_amb(gold: str) -> list[str]:
    labels = ["observational_degeneracy", "missing_evidence"]
    if gold == "obs.calibration_artifact":
        labels.append("misleading_proxy_evidence")
    if gold == "H_unknown":
        labels.extend(["open_set", "non_recoverable_ambiguity"])
    else:
        labels.append("recoverable_ambiguity")
    return labels


def snapshot_manifest(records: tuple[dict[str, Any], ...], source_id: str) -> dict[str, Any]:
    blob = json.dumps(
        [{"id": r["source_record_id"], "gold": r["gold_hypothesis"]} for r in records],
        sort_keys=True,
    )
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return {
        "snapshot_id": SNAPSHOT_ID,
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "n": len(records),
        "live_fetch": False,
        "content_sha256": digest,
        "note": "Schema-faithful synthetic unless provenance_kind=OFFICIAL_FIXTURE_METADATA.",
    }
