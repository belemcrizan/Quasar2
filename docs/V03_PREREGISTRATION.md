# v03 preregistration — protocol 1

Status: DESIGN_FROZEN; runs remain exploratory until all release gates pass.
Frozen before v03 outcome evaluation. Amendments require a new protocol hash and
an explanation; a new hash never retroactively makes an exploratory result confirmatory.

Primary question: can pre-action features select EXPLORE states with positive
net utility better than entropy and random allocation at the SAME action count?
Outcome: paired per-query utility difference, macro by domain. Retrieval-only
experiments use relevant top-1 as an explicitly limited surrogate for answer
correctness; they do not measure end-to-end answer correctness.
Reward correct=1, wrong=-1; ASK=0.28, DEFER=0.05. Retrieval cost grid:
0.01, 0.05 (primary), 0.10, 0.25. Tokens/latency/document processing are recorded
separately, not treated as free when not observed. Unmeasured axes are NOT_RUN.

Datasets: retained synthetic control; WDI real snapshot with GENERATED queries;
SciFact and NFCorpus standard relevance queries where acquired; NASA pscomppars
and INSPIRE metadata with GENERATED diagnostics. FiQA/TREC-COVID secondary only.
Use full datasets when bounded acquisition permits; any limit is selected by
query ID before outcomes, recorded, and prevents confirmatory promotion.
Human annotation target 500–1000: NOT_RUN until actual independent annotations.

Splits: canonical-group SHA256, seed 42; train 60%, development 15%, calibration
10%, test 15%. Group all variants of an intent. Dataset-provided test splits remain
test: never reuse them as training. Domain/entity/template/retriever holdouts
require explicit disjoint metadata; shared-corpus IR is disclosed, not mislabeled
as document-held-out. Near-duplicate normalized queries across splits block
confirmation; paraphrase lexical screening is a warning, not proof of no leakage.

Baselines: STOP, ALWAYS, confidence, entropy, margin, recoverability, uncertainty+
recoverability, cost-aware logistic R*, shallow stump, calibrated logistic,
random allocation with exactly the same additional call count; oracle upper
bound labeled nondeployable. Candidate feature subsets are fixed before outcomes.
Logistic optimization steps=250, learning rate=0.1, L2=0.01; threshold candidates
0, .25, .5, .75, 1.01 (never compute). Fit train only; choose threshold on development
utility; calibrate held-out calibration scores only. Test never tunes anything.
Primary model: uncertainty+recoverability+decision relevance+cost logistic.
No automatic model selection based on test performance.

Seeds 11, 29, 42, 73, 101 for stochastic random allocation; deterministic models
are fitted once. Cluster bootstrap 1000 draws by canonical group, seed 42.
Report n, n_clusters, mean, paired 95% CI, action count, acquisition and measured
costs, Brier, ECE, NLL, AUROC/AUPRC, uncertainty and recoverability correlation.
Primary two comparisons: R* vs entropy and R* vs random, Bonferroni 97.5% marginal
intervals (familywise 95%). Other comparisons/ablations are exploratory 95%.
Minimum meaningful utility gain .01. Fewer than 30 test clusters: UNDERPOWERED.
No optional stopping. No exclusions for unfavorable outcomes; schema/transport
failures remain in run status and prevent completion rather than being dropped.

Supported within scope requires positive lower bounds above .01 vs both primary
baselines, honest cost matching, no failed leakage audit, clean tree and immutable
inputs, preregistration verified, external native-query evaluation, all samples
retained and adequate cluster count. Cross-domain claims additionally require an
unseen domain. Otherwise INCONCLUSIVE or REFUTED (upper CI below zero in scope).
Docker/remote CI/unavailable models remain explicit release gates; do not bump
package version to 0.3.0 merely because this infrastructure exists.
