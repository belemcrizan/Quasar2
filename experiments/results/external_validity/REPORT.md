# QUASAR2 — External validity, scale, replication, and regime discovery

schema_version: external.1
run_id: external_validity
git_sha: 2170646474483bd8b818740da08fe4301111ab3d
seed: 0
snapshot_id: ext-schema-2026-08-26-offline
timestamp: 2026-08-26T21:14:07.898414+00:00
smoke: False
policy_stage: SHADOW
gate1: FAIL (locked)
T2_is_not_Q: true
live_official_dump: false

This cycle does **not** replace the frozen v0.1.1 loop, does not retune Gate 1, and does not promote the experimental policy.

Negative results remain visible. Schema-faithful snapshots are **not** live NASA/ESA TAP dumps.

---

## 1. Repository Audit

Preserved: frozen v0.1.1 sanity table; Gate 1 FAIL; Cycle 2 recoverability/action-value path; WDI snapshots; OPS fixture; BM25/hybrid/hashing; V2.4 WDI policy; JWST/CERN/INSPIRE metadata fixtures; claim ledger.

Added: `src/quasar2/external/` source audit, schema snapshots, leakage tests, scale/budget/regime/transfer, `external-validity` and `reproduce-paper` CLI, Dockerfile.

Not modified: `experiments/results/frozen/v0.1.1/`.

---

## 2. Existing Evidence Preserved

- Gate 1 FAIL: deployment-observable recoverability did not add stable incremental value beyond uncertainty.
- Recoverability is a matched-kernel mechanism variable more than a deployment router.
- T2 bound is not Q(s, EXPLORE).
- Experimental policy remains shadow.
- Entropy, BM25, and Hybrid remain serious baselines.
- Extra retrieval can reduce utility (sanity FULL vs noExplore; Cycle 2 OPS equal-budget).
- Anti-QUASAR regimes remain in Cycle 2 families.
- Synthetic evidence is already strong; deployment-like evidence remains limited.

---

## 3. External Source Audit

Counts: `{
  "HIGH_PRIORITY": 4,
  "USEFUL": 5,
  "AUXILIARY": 3,
  "NOT_SUITABLE": 3
}`

Full table: `source_audit.json` in this artifact directory.

---

## 4. NASA Source Assessment

HIGH_PRIORITY selected: NASA Exoplanet Archive TAP schema (KOI/TOI dispositions) and MAST metadata (in-repo JWST fixture).

ADS: USEFUL, not selected (token; abstracts ≠ claims).

HEASARC / IRSA: USEFUL, deferred to keep 2–3 sources.

Image of the Day: NOT_SUITABLE.

**This run did not fetch TAP.** Records are `SCHEMA_FAITHFUL_SYNTHETIC` with `SYN-` ids, plus official fixture overlay for JWST.

---

## 5. ESA Source Assessment

HIGH_PRIORITY selected: Gaia Archive TAP schema (single vs binary vs spurious).

XMM-Newton: USEFUL, not selected in the first trio.

**Not a live Gaia dump.**

---

## 6. Observatory Source Assessment

HIGH_PRIORITY selected: ALMA Science Archive schema (disk/envelope/outflow/artifact).

ESO SAF: USEFUL; ALMA chosen as the first independent observatory family because metadata-scale ambiguity is closer to the scientific question.

---

## 7. Selected Sources and Rationale

`[
  {
    "source": "NASA Exoplanet Archive (KOI/TOI/PS TAP)",
    "recommendation": "HIGH_PRIORITY",
    "rationale": "Naturally instantiates Q_obs -> competing physical hypotheses with extra evidence of unequal decision value."
  },
  {
    "source": "MAST (HST/JWST/TESS observation metadata)",
    "recommendation": "HIGH_PRIORITY",
    "rationale": "Cross-instrument/mission channel for recoverability mismatch; fixture exists but scientific_benchmark_complete=false."
  },
  {
    "source": "ESA Gaia Archive (DR3 TAP)",
    "recommendation": "HIGH_PRIORITY",
    "rationale": "Independent ESA source; cross-identification and observational degeneracy are native."
  },
  {
    "source": "ALMA Science Archive",
    "recommendation": "HIGH_PRIORITY",
    "rationale": "Independent observatory family; instrument-channel mismatch (bands) maps to Cycle-2 recoverability result."
  }
]`

---

## 8. Rejected Sources and Rationale

`[
  {
    "source": "Unofficial astronomy blogs / scraped HTML / social dumps",
    "rationale": "Fails provenance, license, and official-archive hierarchy. Explicitly rejected."
  },
  {
    "source": "NASA Image of the Day / public-relations captions",
    "rationale": "Prestige without epistemic structure; would fake a scientific bench."
  },
  {
    "source": "Wikipedia / informal aggregators as primary evidence",
    "rationale": "Secondary aggregation below official archive hierarchy for this program."
  }
]`

---

## 9. Data Provenance

snapshot_id: `ext-schema-2026-08-26-offline`

manifests: `{
  "nasa": {
    "snapshot_id": "ext-schema-2026-08-26-offline",
    "schema_version": "external.snapshot.1",
    "source_id": "nasa_exo_schema",
    "n": 48,
    "live_fetch": false,
    "content_sha256": "79f9ad1c6c3557feccabafa0aa7388043c6c4118a96385fbd60508ab240ca496",
    "note": "Schema-faithful synthetic unless provenance_kind=OFFICIAL_FIXTURE_METADATA."
  },
  "esa": {
    "snapshot_id": "ext-schema-2026-08-26-offline",
    "schema_version": "external.snapshot.1",
    "source_id": "esa_gaia_schema",
    "n": 48,
    "live_fetch": false,
    "content_sha256": "7d5e3de02290231d73b9b2085e0b91161893aa28706803d8d9766ef76056d67f",
    "note": "Schema-faithful synthetic unless provenance_kind=OFFICIAL_FIXTURE_METADATA."
  },
  "alma": {
    "snapshot_id": "ext-schema-2026-08-26-offline",
    "schema_version": "external.snapshot.1",
    "source_id": "obs_alma_schema",
    "n": 48,
    "live_fetch": false,
    "content_sha256": "04935165dab03f102f33e9427bcdae563bc2ff1447402babf718c080450b2ff5",
    "note": "Schema-faithful synthetic unless provenance_kind=OFFICIAL_FIXTURE_METADATA."
  }
}`

Every derived state carries `source_record_id`, archive, timestamp, URL, transformation, hypotheses, ground-truth method, available vs hidden evidence, ambiguity/recoverability/open-set labels.

SYN- identifiers must not be cited as official catalog rows.

---

## 10. Data Cards

`[
  {
    "source": "nasa_exo_schema",
    "ownership": "NASA/IPAC NExScI (schema); records are SYN- prefixed",
    "public_access": "Official TAP is public; this snapshot is not a TAP dump",
    "license_terms": "Do not cite SYN- ids as archive rows. Archive terms: exoplanetarchive.ipac.caltech.edu",
    "snapshot": "ext-schema-2026-08-26-offline",
    "retrieval_date": "not_a_live_fetch",
    "filtering": "bounded constructed KOI/TOI-like rows",
    "transformations": "controlled query degradations",
    "exclusions": "no FITS light curves",
    "known_biases": "uniform gold rotation; not Kepler occurrence rates",
    "ambiguity_construction": "transit vs EB vs activity vs blend vs unknown",
    "ground_truth": "constructed gold_hypothesis; ORACLE_ONLY",
    "limitations": "Not live NASA data. Zero-shot tests schema transfer, not catalog-version transfer.",
    "live_nasa_esa_dump": false
  },
  {
    "source": "esa_gaia_schema",
    "ownership": "ESA/Gaia/DPAC (schema); SYN-Gaia ids",
    "public_access": "Gaia Archive is public; this snapshot is not an ADQL dump",
    "license_terms": "Credit ESA/Gaia/DPAC for the real archive; do not cite SYN ids as source_id",
    "snapshot": "ext-schema-2026-08-26-offline",
    "retrieval_date": "not_a_live_fetch",
    "filtering": "bounded constructed sources",
    "transformations": "channel astrometry vs XP",
    "exclusions": "no 1.8e9-source dump",
    "known_biases": "synthetic RUWE grid",
    "ambiguity_construction": "single vs binary vs spurious vs unknown",
    "ground_truth": "constructed",
    "limitations": "Not live Gaia DR3 rows.",
    "live_nasa_esa_dump": false
  },
  {
    "source": "obs_alma_schema",
    "ownership": "ALMA/JAO partners (schema); SYN-ALMA ids",
    "public_access": "Archive is public after proprietary period; snapshot is not Request Handler output",
    "license_terms": "Cite real project codes only when using official products",
    "snapshot": "ext-schema-2026-08-26-offline",
    "retrieval_date": "not_a_live_fetch",
    "filtering": "metadata-like constructed projects",
    "transformations": "band6 vs band7",
    "exclusions": "no visibilities",
    "known_biases": "equal class prior",
    "ambiguity_construction": "disk vs envelope vs outflow vs artifact vs unknown",
    "ground_truth": "constructed",
    "limitations": "Independent observatory family at schema level only.",
    "live_nasa_esa_dump": false
  },
  {
    "source": "jwst_mast_fixture",
    "ownership": "STScI MAST fixture already in this repository",
    "public_access": "Metadata fixture; scientific_benchmark_complete=false",
    "license_terms": "Cite JWST data per STScI rules when using real products",
    "snapshot": "data/sources/fixtures/jwst_mast",
    "retrieval_date": "in-repo fixture",
    "filtering": "three observation metadata rows",
    "transformations": "none beyond overlay",
    "exclusions": "no FITS",
    "known_biases": "tiny N",
    "ambiguity_construction": "calibrated vs reprocessed product lineage",
    "ground_truth": "fixture supersedes field",
    "limitations": "Cannot support H_EXT alone.",
    "live_nasa_esa_dump": false
  }
]`

---

## 11. Natural Ambiguity Taxonomy

Multi-label: lexical, semantic, observational degeneracy, missing/conflicting/incomplete, temporal, cross-source disagreement, open-set, recoverable/non-recoverable, misleading proxy.

Performance by label: `[
  {
    "ambiguity_label": "incomplete_context",
    "n": 43,
    "mean_delta_myopic_minus_answer": -0.5197674418604651
  },
  {
    "ambiguity_label": "lexical",
    "n": 144,
    "mean_delta_myopic_minus_answer": 0.21208333333333332
  },
  {
    "ambiguity_label": "lexical_ambiguity",
    "n": 1,
    "mean_delta_myopic_minus_answer": 0.0
  },
  {
    "ambiguity_label": "misleading_proxy_evidence",
    "n": 154,
    "mean_delta_myopic_minus_answer": 0.30805194805194797
  },
  {
    "ambiguity_label": "missing_context",
    "n": 144,
    "mean_delta_myopic_minus_answer": -0.065
  },
  {
    "ambiguity_label": "missing_evidence",
    "n": 192,
    "mean_delta_myopic_minus_answer": -0.06734375000000004
  },
  {
    "ambiguity_label": "non_recoverable_ambiguity",
    "n": 122,
    "mean_delta_myopic_minus_answer": 1.905573770491803
  },
  {
    "ambiguity_label": "observational_degeneracy",
    "n": 579,
    "mean_delta_myopic_minus_answer": -0.01984455958549225
  },
  {
    "ambiguity_label": "open_set",
    "n": 121,
    "mean_delta_myopic_minus_answer": 1.9299999999999997
  },
  {
    "ambiguity_label": "recoverable_ambiguity",
    "n": 456,
    "mean_delta_myopic_minus_answer": -0.5299999999999999
  },
  {
    "ambiguity_label": "semantic_ambiguity",
    "n": 192,
    "mean_delta_myopic_minus_answer": -0.07015624999999999
  },
  {
    "ambiguity_label": "severe",
    "n": 144,
    "mean_delta_myopic_minus_answer": -0.42916666666666675
  },
  {
    "ambiguity_label": "temporal_ambiguity",
    "n": 3,
    "mean_delta_myopic_minus_answer": -0.3599999999999999
  }
]`

---

## 12. Controlled Degradation Design

Kinds: clean, lexical, missing_context, entity_removed, temporal_removed, conflicting, partial, severe with eta in [0,1]. Parent object `cluster_id` is shared so variants are not independent N.

---

## 13. External Benchmark Construction

n_states: 587
n_clusters: 58
splits: development (NASA Kepler clean, year<=2020), temporal holdout (year>2020), cross-instrument (TESS), external ESA, external observatory, MAST fixture, adversarial constructs, OPS structured.

Zero-shot is recorded before any adaptation (adaptation rungs marked NOT_RUN).

---

## 14. Leakage Audit

`{
  "n_states": 683,
  "n_issues": 0,
  "issues": [],
  "ok": true,
  "oracle_only_fields": [
    "gold_hypothesis",
    "hidden_evidence",
    "true_kernel",
    "oracle_q",
    "r_star",
    "future_observation",
    "answer_key",
    "manually_curated_discriminator_not_in_query"
  ],
  "forbidden_feature_tokens": [
    "gold",
    "correct_hypothesis",
    "future",
    "oracle_q",
    "delta_u",
    "voi_oracle",
    "r_star",
    "true_kernel",
    "family",
    "mismatch_mu_true"
  ],
  "deployment_view_used": true
}`

Document issues: `[]`

---

## 15. Baselines

Retrieval: BM25, hashing-dense (not neural), hybrid, query-expansion BM25. HyDE NOT_RUN. Neural: `{
  "available": true,
  "executed": false,
  "reason": "optional extra present but full neural sweep not in default stdlib run"
}`

Decision: immediate ANSWER, entropy-only, empirical myopic (shadow). Oracle action is a bound, not a competitor.

Retrieval table: `{
  "table": [
    {
      "backend": "bm25",
      "class": "retrieval_baseline",
      "n": 48,
      "intent_top1": 0.20833333333333334,
      "mean_label_recall_at_k": 1.0,
      "mean_latency_ms": 0.5784958339063451,
      "note": "dense_hash is hashing cosine, not neural"
    },
    {
      "backend": "dense_hash",
      "class": "retrieval_baseline",
      "n": 48,
      "intent_top1": 0.1875,
      "mean_label_recall_at_k": 0.8177083333333334,
      "mean_latency_ms": 3.0184208323286534,
      "note": "dense_hash is hashing cosine, not neural"
    },
    {
      "backend": "hybrid",
      "class": "retrieval_baseline",
      "n": 48,
      "intent_top1": 0.1875,
      "mean_label_recall_at_k": 0.9947916666666666,
      "mean_latency_ms": 4.968760411429685,
      "note": "dense_hash is hashing cosine, not neural"
    }
  ]
}`

Query expansion: `{
  "baseline": "query_expansion_bm25",
  "class": "retrieval_baseline",
  "n": 48,
  "intent_top1": 0.2708333333333333,
  "mean_calls": 1.0,
  "note": "HyDE not run (requires a generator model)."
}`

---

## 16. Scale Design

Axes: documents, |H|, queries (clustered), eta, p_unknown, calls/cost. 10^5 TAP protocol is documented, not executed.

Power: `{
  "minimum_effect_size_utility": 0.05,
  "desired_ci_half_width": 0.04,
  "clustering": "object_or_intent family, not degradation variants",
  "ops_n12": "underpowered; variants of the same intent are not independent",
  "ci_width_plan": {
    "desired_half_width": 0.04,
    "sigma": 0.35,
    "icc": 0.25,
    "mean_cluster_size": 6.0,
    "design_effect": 2.25,
    "n_effective_independent": 295,
    "n_rows": 662,
    "n_clusters": 111,
    "z": 1.96
  },
  "min_effect_plan": {
    "min_effect": 0.05,
    "sigma": 0.35,
    "power": 0.8,
    "alpha": 0.05,
    "design_effect": 2.25,
    "n_effective_independent": 385,
    "n_rows": 866,
    "n_clusters": 145,
    "note": "Approximation; not a sequential design. N=12 OPS is underpowered for |\u0394U|=0.05."
  },
  "executed_this_cycle": "schema-faithful hundreds of states with clustered inference; not live TAP 10^5"
}`

Query scale: `{
  "n_states": 587,
  "n_clusters": 58,
  "pseudo_replication": "degradations share cluster_id with the parent object",
  "ops_note": "OPS N=12 remains underpowered; variants are clustered, not independent."
}`

---

## 17. Corpus-Scale Results

`{
  "table": [
    {
      "n_documents": 50,
      "retrieval": [
        {
          "backend": "bm25",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.0,
          "mean_label_recall_at_k": 1.0,
          "mean_latency_ms": 0.1023291697492823,
          "note": "dense_hash is hashing cosine, not neural"
        },
        {
          "backend": "dense_hash",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.0,
          "mean_label_recall_at_k": 0.9895833333333334,
          "mean_latency_ms": 0.6441375250384832,
          "note": "dense_hash is hashing cosine, not neural"
        },
        {
          "backend": "hybrid",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.0,
          "mean_label_recall_at_k": 1.0,
          "mean_latency_ms": 0.8857791787401462,
          "note": "dense_hash is hashing cosine, not neural"
        }
      ]
    },
    {
      "n_documents": 200,
      "retrieval": [
        {
          "backend": "bm25",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.16666666666666666,
          "mean_label_recall_at_k": 1.0,
          "mean_latency_ms": 0.30091250664554536,
          "note": "dense_hash is hashing cosine, not neural"
        },
        {
          "backend": "dense_hash",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.16666666666666666,
          "mean_label_recall_at_k": 0.9479166666666666,
          "mean_latency_ms": 1.0968666708019252,
          "note": "dense_hash is hashing cosine, not neural"
        },
        {
          "backend": "hybrid",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.16666666666666666,
          "mean_label_recall_at_k": 1.0,
          "mean_latency_ms": 1.5108208511567984,
          "note": "dense_hash is hashing cosine, not neural"
        }
      ]
    },
    {
      "n_documents": 800,
      "retrieval": [
        {
          "backend": "bm25",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.16666666666666666,
          "mean_label_recall_at_k": 1.0,
          "mean_latency_ms": 1.2677833340906848,
          "note": "dense_hash is hashing cosine, not neural"
        },
        {
          "backend": "dense_hash",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.16666666666666666,
          "mean_label_recall_at_k": 0.9479166666666666,
          "mean_latency_ms": 4.243737494107336,
          "note": "dense_hash is hashing cosine, not neural"
        },
        {
          "backend": "hybrid",
          "class": "retrieval_baseline",
          "n": 24,
          "intent_top1": 0.16666666666666666,
          "mean_label_recall_at_k": 1.0,
          "mean_latency_ms": 5.356737504674432,
          "note": "dense_hash is hashing cosine, not neural"
        }
      ]
    }
  ],
  "note": "10^5 protocol-ready via TAP snapshot; this run stays offline and bounded.",
  "latency_is_not_the_only_question": true
}`

---

## 18. Hypothesis-Scale Results

`{
  "table": [
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": -0.12,
      "neu_ci": {
        "point": -0.12,
        "ci_low": -0.12,
        "ci_high": -0.12,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "n_hypotheses": 2
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": -0.12,
      "neu_ci": {
        "point": -0.12,
        "ci_low": -0.12,
        "ci_high": -0.12,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "n_hypotheses": 2
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": -1.4,
      "neu_ci": {
        "point": -1.4,
        "ci_low": -1.4,
        "ci_high": -1.4,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 1.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "n_hypotheses": 2
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.6400000000000001,
        "ci_high": 0.6400000000000001,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "n_hypotheses": 5
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.6400000000000001,
        "ci_high": 0.6400000000000001,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "n_hypotheses": 5
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "n_hypotheses": 5
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": -0.05,
      "neu_ci": {
        "point": -0.05,
        "ci_low": -0.05,
        "ci_high": -0.05,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 1.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "n_hypotheses": 10
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.6400000000000001,
        "ci_high": 0.6400000000000001,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "n_hypotheses": 10
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "n_hypotheses": 10
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": -0.05,
      "neu_ci": {
        "point": -0.05,
        "ci_low": -0.05,
        "ci_high": -0.05,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 1.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "n_hypotheses": 20
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.6400000000000001,
        "ci_high": 0.6400000000000001,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "n_hypotheses": 20
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 40,
      "effective_clustered_n": 5,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 5,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "n_hypotheses": 20
    }
  ],
  "note": "Do not force |H|=100 when candidates would be artificial."
}`

---

## 19. Query-Scale Results

Cluster-aware N is `n_clusters=58`, not the degradation-expanded row count.

OPS historical N=12 remains underpowered and is not re-interpreted as confirmatory.

---

## 20. Ambiguity-Scale Results

`{
  "table": [
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.64,
        "ci_high": 0.6400000000000001,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "eta": 0.1,
      "band": "low"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.64,
        "ci_high": 0.6400000000000001,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "eta": 0.1,
      "band": "low"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "eta": 0.1,
      "band": "low"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.64,
        "ci_high": 0.6400000000000001,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "eta": 0.35,
      "band": "moderate"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.64,
        "ci_high": 0.6400000000000001,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "eta": 0.35,
      "band": "moderate"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "eta": 0.35,
      "band": "moderate"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.64,
        "ci_high": 0.6400000000000001,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "eta": 0.65,
      "band": "high"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.64,
        "ci_high": 0.6400000000000001,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "eta": 0.65,
      "band": "high"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "eta": 0.65,
      "band": "high"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": -0.05,
      "neu_ci": {
        "point": -0.05,
        "ci_low": -0.05,
        "ci_high": -0.05,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 1.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "eta": 0.9,
      "band": "extreme"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 0.19000000000000006,
      "neu_ci": {
        "point": 0.19000000000000006,
        "ci_low": 0.19000000000000006,
        "ci_high": 0.19000000000000009,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 1.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "eta": 0.9,
      "band": "extreme"
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 60,
      "effective_clustered_n": 8,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 8,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "eta": 0.9,
      "band": "extreme"
    }
  ],
  "note": "Monotonicity of EXPLORE vs eta is tested, not assumed."
}`

Monotonicity is not assumed.

---

## 21. Open-Set Results

`{
  "table": [
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.6400000000000001,
        "ci_high": 0.6400000000000001,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "p_unknown": 0.0
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.6400000000000001,
      "neu_ci": {
        "point": 0.6400000000000001,
        "ci_low": 0.6400000000000001,
        "ci_high": 0.6400000000000001,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "p_unknown": 0.0
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "p_unknown": 0.0
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.6145000000000002,
      "neu_ci": {
        "point": 0.6145000000000002,
        "ci_low": 0.5953750000000001,
        "ci_high": 0.6336250000000001,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.95,
      "defer_rate": 0.05,
      "ask_rate": 0.0,
      "mean_calls": 0.95,
      "p_unknown": 0.05
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.5895000000000001,
      "neu_ci": {
        "point": 0.5895000000000001,
        "ci_low": 0.5516250000000001,
        "ci_high": 0.6273750000000001,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "p_unknown": 0.05
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.86,
      "neu_ci": {
        "point": 0.86,
        "ci_low": 0.755,
        "ci_high": 0.9650000000000001,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.05,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "p_unknown": 0.05
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.5890000000000002,
      "neu_ci": {
        "point": 0.5890000000000002,
        "ci_low": 0.5507500000000001,
        "ci_high": 0.6272500000000001,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.9,
      "defer_rate": 0.1,
      "ask_rate": 0.0,
      "mean_calls": 0.9,
      "p_unknown": 0.1
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.5390000000000001,
      "neu_ci": {
        "point": 0.5390000000000001,
        "ci_low": 0.4632500000000001,
        "ci_high": 0.6147500000000001,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "p_unknown": 0.1
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.72,
      "neu_ci": {
        "point": 0.72,
        "ci_low": 0.51,
        "ci_high": 0.93,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.1,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "p_unknown": 0.1
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.5125000000000001,
      "neu_ci": {
        "point": 0.5125000000000001,
        "ci_low": 0.44221562500000006,
        "ci_high": 0.59569375,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.75,
      "defer_rate": 0.25,
      "ask_rate": 0.0,
      "mean_calls": 0.75,
      "p_unknown": 0.25
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.38750000000000007,
      "neu_ci": {
        "point": 0.38750000000000007,
        "ci_low": 0.2483093750000001,
        "ci_high": 0.5522562499999999,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "p_unknown": 0.25
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.30000000000000004,
      "neu_ci": {
        "point": 0.30000000000000004,
        "ci_low": -0.08587499999999992,
        "ci_high": 0.7567499999999994,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.25,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "p_unknown": 0.25
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "empirical_myopic",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.38500000000000006,
      "neu_ci": {
        "point": 0.38500000000000006,
        "ci_low": 0.29511250000000006,
        "ci_high": 0.47488749999999985,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.5,
      "defer_rate": 0.5,
      "ask_rate": 0.0,
      "mean_calls": 0.5,
      "p_unknown": 0.5
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "entropy_only",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": 0.13500000000000006,
      "neu_ci": {
        "point": 0.13500000000000006,
        "ci_low": -0.04301249999999995,
        "ci_high": 0.31301249999999964,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0,
      "p_unknown": 0.5
    },
    {
      "source": "scale_synthetic",
      "split_role": "scale",
      "policy": "immediate_answer",
      "n": 80,
      "effective_clustered_n": 10,
      "mean_neu": -0.3999999999999999,
      "neu_ci": {
        "point": -0.3999999999999999,
        "ci_low": -0.8934999999999998,
        "ci_high": 0.09349999999999886,
        "n_clusters": 10,
        "samples": 80,
        "n_successful_draws": 80
      },
      "false_answer_rate": 0.5,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0,
      "p_unknown": 0.5
    }
  ]
}`

---

## 22. Equal-Call Results

`[
  {
    "policy": "immediate_answer",
    "budget": 1.0,
    "mean_calls": 0.0,
    "mean_neu": 0.4187393526405452,
    "within_budget": true
  },
  {
    "policy": "entropy_only",
    "budget": 1.0,
    "mean_calls": 0.8432708688245315,
    "mean_neu": 0.4298637137989779,
    "within_budget": true
  },
  {
    "policy": "empirical_myopic",
    "budget": 1.0,
    "mean_calls": 0.3969335604770017,
    "mean_neu": 0.3982112436115844,
    "within_budget": true
  }
]`

---

## 23. Equal-Latency Results

Offline stdlib run: hashing/BM25 latencies only. Neural/cross-encoder equal-latency matching NOT_RUN. Composite cost keeps latency as a raw component (`budget.composite_cost_example`).

---

## 24. Equal-Cost Results

Monetary tokens are zero unless a billed API is used. Lambdas are explicit. Cloud cost: NOT_RUN.

---

## 25. Pareto Frontier

`[
  {
    "policy": "immediate_answer",
    "budget": 1.0,
    "mean_calls": 0.0,
    "mean_neu": 0.4187393526405452,
    "within_budget": true,
    "on_frontier": true
  },
  {
    "policy": "entropy_only",
    "budget": 1.0,
    "mean_calls": 0.8432708688245315,
    "mean_neu": 0.4298637137989779,
    "within_budget": true,
    "on_frontier": true
  }
]`

---

## 26. NASA Results

See transfer matrix rows `development`, `external_nasa`, `cross_instrument`, `temporal_holdout`.

`[
  {
    "split_role": "adversarial",
    "n": 8,
    "n_clusters": 8,
    "delta_vs_answer": {
      "left": "empirical_myopic",
      "right": "immediate_answer",
      "n": 8,
      "n_clusters": 8,
      "mean_delta": -0.11125000000000002,
      "ci": {
        "point": -0.11125000000000002,
        "ci_low": -0.615,
        "ci_high": 0.6337499999999999,
        "n_clusters": 8,
        "samples": 200,
        "n_successful_draws": 200
      }
    },
    "delta_vs_entropy": {
      "left": "empirical_myopic",
      "right": "entropy_only",
      "n": 8,
      "n_clusters": 8,
      "mean_delta": -0.15749999999999997,
      "ci": {
        "point": -0.15749999999999997,
        "ci_low": -0.535125,
        "ci_high": 0.17812500000000017,
        "n_clusters": 8,
        "samples": 200,
        "n_successful_draws": 200
      }
    }
  },
  {
    "split_role": "external_mast_fixture",
    "n": 3,
    "n_clusters": 2,
    "delta_vs_answer": {
      "left": "empirical_myopic",
      "right": "immediate_answer",
      "n": 3,
      "n_clusters": 2,
      "mean_delta": -0.3599999999999999,
      "ci": {
        "point": -0.3599999999999999,
        "ci_low": -0.3599999999999999,
        "ci_high": -0.3599999999999999,
        "n_clusters": 2,
        "samples": 200,
        "n_successful_draws": 200
      }
    },
    "delta_vs_entropy": {
      "left": "empirical_myopic",
      "right": "entropy_only",
      "n": 3,
      "n_clusters": 2,
      "mean_delta": 0.0,
      "ci": {
        "point": 0.0,
        "ci_low": 0.0,
        "ci_high": 0.0,
        "n_clusters": 2,
        "samples": 200,
        "n_successful_draws": 200
      }
    }
  },
  {
    "split_role": "external_nasa",
    "n": 576,
    "n_clusters": 48,
    "delta_vs_answer": {
      "left": "empirical_myopic",
      "right": "immediate_answer",
      "n": 576,
      "n_clusters": 48,
      "mean_delta": -0.017500000000000022,
      "ci": {
        "point": -0.017500000000000022,
        "ci_low": -0.12026041666666666,
        "ci_high": 0.08562152777777783,
        "n_clusters": 48,
        "samples": 200,
        "n_successful_draws": 200
      }
    },
    "delta_vs_entropy": {
      "left": "empirical_myopic",
      "right": "entropy_only",
      "n": 576,
      "n_clusters": 48,
      "mean_delta": -0.03006944444444449,
      "ci": {
        "point": -0.03006944444444449,
        "ci_low": -0.05271093750000005,
        "ci_high": -0.0040716145833333784,
        "n_clusters": 48,
        "samples": 200,
        "n_successful_draws": 200
      }
    }
  }
]`

---

## 27. ESA Results

Split `external_esa` in the transfer matrix. Schema-faithful only.

---

## 28. Observatory Results

Split `external_observatory` (ALMA schema). JWST fixture is overlay-only and too small for H_EXT.

---

## 29. Cross-Source Transfer

Shifts: `{
  "adversarial": {
    "policy": "empirical_myopic",
    "n_dev": 0,
    "n_other": 8,
    "neu_dev": null,
    "neu_other": 0.23875000000000005,
    "neu_shift": null,
    "entropy_dev": null,
    "entropy_other": 0.8411120627895559,
    "entropy_shift": null,
    "R_hat_dev": null,
    "R_hat_other": 0.24975999999999998,
    "R_hat_shift": null,
    "explore_rate_shift": null,
    "false_answer_shift": null,
    "performance_drop_neu": null,
    "recoverability_shift": null,
    "regret_shift_proxy": null,
    "action_distribution_shift_explore": null,
    "calibration_shift_entropy": null
  },
  "external_mast_fixture": {
    "policy": "empirical_myopic",
    "n_dev": 0,
    "n_other": 3,
    "neu_dev": null,
    "neu_other": 0.6400000000000001,
    "neu_shift": null,
    "entropy_dev": null,
    "entropy_other": 1.1354508105601309,
    "entropy_shift": null,
    "R_hat_dev": null,
    "R_hat_other": 0.22640000000000002,
    "R_hat_shift": null,
    "explore_rate_shift": null,
    "false_answer_shift": null,
    "performance_drop_neu": null,
    "recoverability_shift": null,
    "regret_shift_proxy": null,
    "action_distribution_shift_explore": null,
    "calibration_shift_entropy": null
  },
  "external_nasa": {
    "policy": "empirical_myopic",
    "n_dev": 0,
    "n_other": 576,
    "neu_dev": null,
    "neu_other": 0.39916666666666667,
    "neu_shift": null,
    "entropy_dev": null,
    "entropy_other": 1.754515140630573,
    "entropy_shift": null,
    "R_hat_dev": null,
    "R_hat_other": 0.10953472222222221,
    "R_hat_shift": null,
    "explore_rate_shift": null,
    "false_answer_shift": null,
    "performance_drop_neu": null,
    "recoverability_shift": null,
    "regret_shift_proxy": null,
    "action_distribution_shift_explore": null,
    "calibration_shift_entropy": null
  }
}`

Adaptation ladder: calibration_only / limited / full are NOT_RUN after recording zero-shot.

---

## 30. OPS Cross-Domain Results

`{
  "left": "empirical_myopic",
  "right": "immediate_answer",
  "n": 96,
  "n_clusters": 8,
  "mean_delta": -1.05,
  "ci": {
    "point": -1.05,
    "ci_low": -1.05,
    "ci_high": -1.05,
    "n_clusters": 8,
    "samples": 200,
    "n_successful_draws": 200
  }
}`

Summaries: `{
  "summaries": [
    {
      "source": "ops_structured",
      "split_role": "ops_cross_domain",
      "policy": "empirical_myopic",
      "n": 96,
      "effective_clustered_n": 8,
      "mean_neu": -0.05000000000000001,
      "neu_ci": {
        "point": -0.05000000000000001,
        "ci_low": -0.05000000000000001,
        "ci_high": -0.05000000000000001,
        "n_clusters": 8,
        "samples": 200,
        "n_successful_draws": 200
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 1.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0
    },
    {
      "source": "ops_structured",
      "split_role": "ops_cross_domain",
      "policy": "entropy_only",
      "n": 96,
      "effective_clustered_n": 8,
      "mean_neu": 0.5884375000000001,
      "neu_ci": {
        "point": 0.5884375000000001,
        "ci_low": 0.5743750000000001,
        "ci_high": 0.5978125000000002,
        "n_clusters": 8,
        "samples": 200,
        "n_successful_draws": 200
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.11458333333333333,
      "explore_rate": 1.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 1.0
    },
    {
      "source": "ops_structured",
      "split_role": "ops_cross_domain",
      "policy": "immediate_answer",
      "n": 96,
      "effective_clustered_n": 8,
      "mean_neu": 1.0,
      "neu_ci": {
        "point": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "n_clusters": 8,
        "samples": 200,
        "n_successful_draws": 200
      },
      "false_answer_rate": 0.0,
      "false_explore_rate": 0.0,
      "explore_rate": 0.0,
      "defer_rate": 0.0,
      "ask_rate": 0.0,
      "mean_calls": 0.0
    }
  ]
}`

The framework (uncertainty × recoverability × cost) can transfer while a specific R_hat estimator does not. Cycle 2 OPS equal-budget negative result is retained.

---

## 31. Regime Discovery

`{
  "features": [
    "entropy",
    "R_hat",
    "mismatch_mu",
    "eta",
    "open_set",
    "unknown_mass",
    "entropy*R_hat",
    "R_hat*(1-mismatch)"
  ],
  "train_roles": [
    "development"
  ],
  "weights": null,
  "train": {
    "n": 0
  },
  "heldout": {
    "n": 587,
    "n_predicted_Rstar": 233,
    "mean_delta_in_Rstar": -0.3629613733905578,
    "mean_delta_outside": 0.20485875706214676,
    "mean_delta_all": -0.020528109028960836,
    "simple_rule_mean_signed_error": 0.9058091993185688,
    "flexible_mean_signed_error": 0.9058091993185688
  },
  "n_delta_states": 587,
  "leakage": "gold/true_kernels not in features",
  "qualitative_structure": "Candidate R*: high entropy AND sufficient R_hat AND low mismatch AND not open-set. Clear queries and high-mismatch channels are baseline-favoring."
}`

Boundaries fit on `development` only.

---

## 32. Regime Validation

Held-out cell in the same object. Cross-source qualitative structure is the scientific target, not coefficient equality.

---

## 33. Crossover Surface

`[
  {
    "kappa": 0.02,
    "rho_star_myopic_gt_answer": 0.5
  },
  {
    "kappa": 0.1,
    "rho_star_myopic_gt_answer": 0.5
  },
  {
    "kappa": 0.25,
    "rho_star_myopic_gt_answer": 0.5
  },
  {
    "kappa": 0.5,
    "rho_star_myopic_gt_answer": 0.5
  }
]`

Grid: `[
  {
    "rho": 0.5,
    "kappa": 0.02,
    "mean_neu": {
      "immediate_answer": 0.5962500000000001,
      "entropy_only": 0.547125,
      "empirical_myopic": 0.636625
    }
  },
  {
    "rho": 1.0,
    "kappa": 0.02,
    "mean_neu": {
      "immediate_answer": 0.49000000000000005,
      "entropy_only": 0.547125,
      "empirical_myopic": 0.636625
    }
  },
  {
    "rho": 1.4,
    "kappa": 0.02,
    "mean_neu": {
      "immediate_answer": 0.4050000000000001,
      "entropy_only": 0.547125,
      "empirical_myopic": 0.636625
    }
  },
  {
    "rho": 2.0,
    "kappa": 0.02,
    "mean_neu": {
      "immediate_answer": 0.2775,
      "entropy_only": 0.547125,
      "empirical_myopic": 0.636625
    }
  },
  {
    "rho": 4.0,
    "kappa": 0.02,
    "mean_neu": {
      "immediate_answer": -0.14750000000000008,
      "entropy_only": 0.547125,
      "empirical_myopic": -0.01175
    }
  },
  {
    "rho": 0.5,
    "kappa": 0.1,
    "mean_neu": {
      "immediate_answer": 0.5962500000000001,
      "entropy_only": 0.484125,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 1.0,
    "kappa": 0.1,
    "mean_neu": {
      "immediate_answer": 0.49000000000000005,
      "entropy_only": 0.484125,
      "empirical_myopic": 0.5856250000000001
    }
  },
  {
    "rho": 1.4,
    "kappa": 0.1,
    "mean_neu": {
      "immediate_answer": 0.4050000000000001,
      "entropy_only": 0.484125,
      "empirical_myopic": 0.5856250000000001
    }
  },
  {
    "rho": 2.0,
    "kappa": 0.1,
    "mean_neu": {
      "immediate_answer": 0.2775,
      "entropy_only": 0.484125,
      "empirical_myopic": 0.5856250000000001
    }
  },
  {
    "rho": 4.0,
    "kappa": 0.1,
    "mean_neu": {
      "immediate_answer": -0.14750000000000008,
      "entropy_only": 0.484125,
      "empirical_myopic": -0.01175
    }
  },
  {
    "rho": 0.5,
    "kappa": 0.25,
    "mean_neu": {
      "immediate_answer": 0.5962500000000001,
      "entropy_only": 0.36600000000000005,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 1.0,
    "kappa": 0.25,
    "mean_neu": {
      "immediate_answer": 0.49000000000000005,
      "entropy_only": 0.36600000000000005,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 1.4,
    "kappa": 0.25,
    "mean_neu": {
      "immediate_answer": 0.4050000000000001,
      "entropy_only": 0.36600000000000005,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 2.0,
    "kappa": 0.25,
    "mean_neu": {
      "immediate_answer": 0.2775,
      "entropy_only": 0.36600000000000005,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 4.0,
    "kappa": 0.25,
    "mean_neu": {
      "immediate_answer": -0.14750000000000008,
      "entropy_only": 0.36600000000000005,
      "empirical_myopic": -0.01175
    }
  },
  {
    "rho": 0.5,
    "kappa": 0.5,
    "mean_neu": {
      "immediate_answer": 0.5962500000000001,
      "entropy_only": 0.16912500000000003,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 1.0,
    "kappa": 0.5,
    "mean_neu": {
      "immediate_answer": 0.49000000000000005,
      "entropy_only": 0.16912500000000003,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 1.4,
    "kappa": 0.5,
    "mean_neu": {
      "immediate_answer": 0.4050000000000001,
      "entropy_only": 0.16912500000000003,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 2.0,
    "kappa": 0.5,
    "mean_neu": {
      "immediate_answer": 0.2775,
      "entropy_only": 0.16912500000000003,
      "empirical_myopic": 0.8151249999999999
    }
  },
  {
    "rho": 4.0,
    "kappa": 0.5,
    "mean_neu": {
      "immediate_answer": -0.14750000000000008,
      "entropy_only": 0.16912500000000003,
      "empirical_myopic": -0.01175
    }
  }
]`

---

## 34. Failure Regions

Adversarial summaries: `[
  {
    "source": "adversarial_construct",
    "split_role": "adversarial",
    "policy": "empirical_myopic",
    "n": 8,
    "effective_clustered_n": 8,
    "mean_neu": 0.23875000000000005,
    "neu_ci": {
      "point": 0.23875000000000005,
      "ci_low": -0.14487499999999992,
      "ci_high": 0.7354374999999994,
      "n_clusters": 8,
      "samples": 80,
      "n_successful_draws": 80
    },
    "false_answer_rate": 0.125,
    "false_explore_rate": 0.0,
    "explore_rate": 0.25,
    "defer_rate": 0.375,
    "ask_rate": 0.0,
    "mean_calls": 0.25
  },
  {
    "source": "adversarial_construct",
    "split_role": "adversarial",
    "policy": "entropy_only",
    "n": 8,
    "effective_clustered_n": 8,
    "mean_neu": 0.39625000000000005,
    "neu_ci": {
      "point": 0.39625000000000005,
      "ci_low": 0.07875000000000001,
      "ci_high": 0.7887500000000001,
      "n_clusters": 8,
      "samples": 80,
      "n_successful_draws": 80
    },
    "false_answer_rate": 0.0,
    "false_explore_rate": 0.25,
    "explore_rate": 0.75,
    "defer_rate": 0.0,
    "ask_rate": 0.0,
    "mean_calls": 0.75
  },
  {
    "source": "adversarial_construct",
    "split_role": "adversarial",
    "policy": "immediate_answer",
    "n": 8,
    "effective_clustered_n": 8,
    "mean_neu": 0.35000000000000003,
    "neu_ci": {
      "point": 0.35000000000000003,
      "ci_low": -0.6012499999999998,
      "ci_high": 1.0,
      "n_clusters": 8,
      "samples": 80,
      "n_successful_draws": 80
    },
    "false_answer_rate": 0.25,
    "false_explore_rate": 0.0,
    "explore_rate": 0.0,
    "defer_rate": 0.0,
    "ask_rate": 0.0,
    "mean_calls": 0.0
  }
]`

Expected losses: clear/cheap ANSWER; non-recoverable EXPLORE waste; mismatch; open-set false ANSWER; high kappa.

---

## 35. Strongest Baseline

On clear/low-eta states: immediate ANSWER / BM25-style top-1. Entropy remains the serious uncertainty baseline. Do not declare myopic globally strongest.

---

## 36. Cases Where Baselines Win

Clear query, perfect top-1, high retrieval cost, anti-QUASAR cost-dominated, sanity Hybrid IRR, WDI BM25 top-1, Cycle 2 OPS equal-budget.

---

## 37. Cases Where QUASAR2 Wins

Only where held-out ΔQ in predicted R* is positive under clustered intervals. Region characterization: Candidate empirical R*: high entropy, recoverable class, low mismatch_mu, not open-set. Observed fraction with ΔQ>0 vs immediate ANSWER: 121/587.

---

## 38. Negative Results

- Live official dumps were **not** used (claim C3-live-official-dumps REFUTED as a completed confirmatory test).
- HyDE / strong neural / cross-encoder full N NOT_RUN.
- Cloud replication NOT_RUN.
- Gate 1 remains FAIL.
- Cycle 2 G-R recoverability beyond uncertainty remains NOT_SUPPORTED.
- Schema transfer is weaker evidence than catalog-version transfer.

---

## 39. Statistical Inference

Cluster bootstrap on `cluster_id` (object / incident class). Pooled and source-specific summaries both reported. Effect sizes are ΔNEU, not p-values. Seeds: 0.

---

## 40. Replication Results

Environment: `{
  "python": "3.13.3",
  "platform": "Windows-11-10.0.26200-SP0",
  "os": "win32",
  "package_versions": {
    "numpy": "2.2.6",
    "torch": "2.7.1+cpu",
    "sentence_transformers": "3.4.1",
    "pytest": "8.4.2"
  },
  "embedding_models": "NOT_LOADED_IN_DEFAULT_STDLIB_RUN",
  "git_sha": "2170646474483bd8b818740da08fe4301111ab3d",
  "timestamp_utc": "2026-08-26T21:14:41.556624+00:00",
  "cpu": "Intel64 Family 6 Model 186 Stepping 2, GenuineIntel",
  "note": "Hashing dense is not a neural encoder. Neural extras absent unless installed."
}`

Cloud: `{
  "status": "NOT_RUN",
  "reason": "No cloud credentials in this research checkout. Independent Linux container is the provided path.",
  "compare": null,
  "level": "independent_execution_ready_not_external_replication"
}`

Frozen reconstruct: `{
  "status": "RECONSTRUCTED_FROM_IMMUTABLE_SNAPSHOT",
  "path": "experiments/results/frozen/v0.1.1/benchmark.json",
  "sha256": "78084ace9907e300f923c65109debe242e7d53a88d670148dc93c982f29c8c83",
  "n_records": null,
  "note": "Not a new run. Frozen v0.1.1 is not modified."
}`

Cycle 2 reconstruct: `{
  "status": "RECONSTRUCTED_FROM_EXISTING_ARTIFACT",
  "path": "experiments/results/cycle2_maturity/cycle2.json",
  "answers": {
    "A_operational_recoverability_beyond_uncertainty": "NO",
    "B_policy_beyond_shadow": "NO",
    "C_synthetic_generalizes": "PARTIAL",
    "D_deployment_like_positive_value": "PARTIAL"
  },
  "gate1": "FAIL locked",
  "note": "Reproduction of Cycle 2 numbers uses existing artifacts; this command does not retune Gate 1."
}`

Levels: this checkout supports computational reproducibility of the **offline** program. That is **not** external replication of NASA/ESA science archives.

---

## 41. Reproducibility Audit

- `quasar2 reproduce-paper` reconstructs frozen tables from immutable JSON and reruns the offline external program without silent mutable downloads.
- Dockerfile provided for independent Linux execution.
- Clean-checkout: `pip install -e .` then `quasar2 validate` and `quasar2 reproduce-paper`.

---

## 42. Claim Ledger Changes

New hypothesis ids H_EXT…H_REPLICATION registered as HYPOTHESIS. No SUPPORTED_IN_SCOPE promotions. C3-live-official-dumps REFUTED as completed.

`[
  {
    "claim_id": "H_EXT",
    "text": "Adaptive epistemic action transfers across independent scientific sources.",
    "status": "HYPOTHESIS",
    "result": "NO",
    "scope": "schema-faithful NASA/ESA/ALMA snapshots, not live TAP dumps"
  },
  {
    "claim_id": "H_DOMAIN",
    "text": "Decision-theoretic acquisition principles transfer across astronomy and OPS.",
    "status": "HYPOTHESIS",
    "result": "NO",
    "scope": "ops_structured states clustered by incident class"
  },
  {
    "claim_id": "H_SCALE",
    "text": "Advantage region remains detectable as corpus and hypothesis spaces scale.",
    "status": "HYPOTHESIS",
    "result": "PARTIAL"
  },
  {
    "claim_id": "H_BUDGET",
    "text": "QUASAR2 occupies part of the utility-cost Pareto frontier in ambiguity/risk regimes.",
    "status": "HYPOTHESIS",
    "result": "NO",
    "detail": [
      {
        "policy": "immediate_answer",
        "budget": 1.0,
        "mean_calls": 0.0,
        "mean_neu": 0.4187393526405452,
        "within_budget": true,
        "on_frontier": true
      },
      {
        "policy": "entropy_only",
        "budget": 1.0,
        "mean_calls": 0.8432708688245315,
        "mean_neu": 0.4298637137989779,
        "within_budget": true,
        "on_frontier": true
      }
    ]
  },
  {
    "claim_id": "H_REGIME",
    "text": "QUASAR2 advantage can be predicted from observable regime variables.",
    "status": "HYPOTHESIS",
    "result": "NO",
    "heldout_mean_delta_in_Rstar": -0.3629613733905578
  },
  {
    "claim_id": "H_MISMATCH",
    "text": "Observation-model mismatch explains a substantial portion of recoverability and policy failure.",
    "status": "HYPOTHESIS",
    "result": "TESTED_ON_CHANNEL_SHIFTS"
  },
  {
    "claim_id": "H_REPLICATION",
    "text": "Major findings reproduce across independent compute environments.",
    "status": "NOT_TESTED",
    "result": "PARTIAL"
  },
  {
    "claim_id": "C3-live-official-dumps",
    "text": "Live NASA/ESA/ALMA TAP dumps were used as confirmatory evidence.",
    "status": "REFUTED",
    "result": "This cycle uses schema-faithful offline snapshots plus in-repo fixtures."
  }
]`

---

## 43. New Supported Claims

None at SUPPORTED_IN_SCOPE. Schema-offline results may be PARTIALLY_SUPPORTED only as mechanism maps, not as NASA/ESA confirmation.

---

## 44. Claims Not Supported

H_EXT, H_DOMAIN, H_SCALE, H_BUDGET, H_REGIME, H_MISMATCH, H_REPLICATION as confirmatory scientific claims on official dumps.

---

## 45. Refuted Claims

"Live NASA/ESA/ALMA TAP dumps were used as confirmatory evidence in this cycle."

Universal average superiority of QUASAR2 is still not claimed and remains inconsistent with frozen sanity Hybrid and WDI top-1.

---

## 46. Remaining Threats

Leakage via constructed language overlap; schema ≠ live catalog; pseudo-replication if cluster_id ignored; compute advantage if neural added later without budget match; tuning on holdout; observation-model mismatch reversing R_hat; weak hashing-dense "neural" confusion (explicitly not neural).

---

## 47. Scientific Maturity Assessment

Moved from internally mature prototype toward an **auditable external-validity protocol**. Confirmatory external validity on official dumps is **not** complete. Quality bar in the program statement is not met by "NASA schema loaded successfully."

---

## 48. Highest-Information Next Experiment

Frozen TAP/ADQL snapshots of a **versioned** KOI/TOI slice and a **versioned** Gaia NSS/source slice, with pre-registered clustered ΔNEU vs BM25+entropy under equal retrieval-call budget, zero-shot from Kepler-era development to TESS-era and Gaia, **before** any source-specific threshold search.

---

## Final questions

A. Does QUASAR2 generalize across independent public scientific sources? **NO**

B. Does the decision principle transfer outside astronomy? **NO**

C. Does QUASAR2 retain useful behavior as corpus/hypothesis/query scale grows? **PARTIAL**

D. Can the main results be reproduced from a clean independent environment? **PARTIAL**

E. Does QUASAR2 beat strong baselines anywhere under equal budget? **NO**

F. If YES/PARTIAL, region: Candidate empirical R*: high entropy, recoverable class, low mismatch_mu, not open-set. Observed fraction with ΔQ>0 vs immediate ANSWER: 121/587.

G. If NO, failed assumption: See negative results; schema-offline R* may be empty or unstable.

H. Does a stable empirical advantage regime exist? **NO**

Formal target: R* = { s : E[U_QUASAR2(s) - U_best_baseline(s) | s] > 0 }. Identifiable in development features: attempted. Stable across official dumps: **not demonstrated**. Economically meaningful: **unknown** without monetary traces.

Every important cell should be read with: source, snapshot `ext-schema-2026-08-26-offline`, N / clustered N, regime, policy, baseline, budget, utility (rho/kappa), effect size, CI, seed `0`, run_id `external_validity`, git SHA `2170646474483bd8b818740da08fe4301111ab3d`, artifact `experiments\results\external_validity`.
