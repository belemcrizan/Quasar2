# Experiment plan — P0 recoverability, tightness, shadow, T4 near-zero

Status: **pre-registered for this development cycle**. Primary experiments run after implementation. Changing the primary metric after looking at results must be logged.

## Recoverability vs empirical VoI

- Research question: Do deployment-safe recoverability scores predict empirical 0-1 VoI better than entropy?
- Primary hypothesis: on synthetic holdout kernel families, Spearman(R, VoI_empirical) for JSD or DRS exceeds Spearman(entropy, VoI_empirical).
- Primary metric: Spearman correlation on holdout families (HeavyOverlap, NearIdentical, Multimodal, MisspecifiedTrue).
- Secondary: Pearson, R², AUROC for 1[VoI>0], Brier, T2 tightness counts, Bayes retrieval-harm rate.
- Baselines: TV, KL, symmetric KL, JSD, MI, empirical discrimination, belief margin, entropy, retriever-score margin, embedding-separation proxy, learned ridge.
- Sample: deterministic kernel × prior grid (not a random sample of queries).
- Stopping rule: single predeclared grid; no sequential peeking.
- Known confounds: Bayes 0-1 VoI is nonnegative, so harm rate under true kernels is expected ~0; proxy kernels for MisspecifiedTrue are HeavyOverlap; learned fit uses train families only; no gold-intent features.

## T2 tightness

- Question: is the Lipschitz bound tight, useful, loose, or vacuous on the kernel grid?
- Primary metric: counts of tightness labels; identity_holds must remain true.
- Bound violations, if any, are recorded and do not auto-refute T2 when the identity holds under a different utility.

## T4 near-zero

- Question: does easy-Gaussian T4 (mean 0.15) transfer to means near zero?
- Primary metric: false-stop rate vs α with Wilson interval, by estimator and mean.
- Predeclared state: INCONCLUSIVE (diagnostic). Sequential validity not claimed.
- Methods: NormalUCB, percentile bootstrap, BCa, Empirical Bernstein.
- Families in the companion check remain T4_families.

## 120-query shadow study

- Question: how often does recommended_action_v2 diverge from executed legacy action, and why?
- Primary metric: transition matrix counts; agreement rate; divergence taxonomy.
- Counterfactual v2 correctness is **not** the primary metric (EXPLORE/ASK not executed).
- Artifact path: `experiments/runs/` only. Frozen `experiments/results/benchmark.json` is not overwritten.
- Confounds: Bernoulli support proxy kernels; quadrant thresholds are heuristics.

## Synthetic policy comparison

- Question: does a learned imitator or myopic VoI reduce one-step regret vs threshold relative to a tabular oracle?
- Primary metric: mean oracle regret on a held-out synthetic split.
- Equal-budget slices: NEU by explore_cost ∈ {0.02, 0.10, 0.25, 0.40}.
- Not WDI. Oracle kernels are the simulation kernels.
