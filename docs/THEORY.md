# Canonical theory (V2)

This document is the **canonical** statement for mode `v2`. Historical wording in
`docs/SCIENTIFIC_THESIS.md` remains the legacy account of the v0.1.1 loop.
Corrections here are `theory_revision`s, not silent replacements.

Language: **THEOREM** (assumptions + proof), **PROPOSITION**, **HYPOTHESIS**,
**EMPIRICAL_OBSERVATION**, **HEURISTIC**. These labels are not interchangeable.

Logs are natural (**nats**) unless a result records `divergence_units=bits`.
Total variation is \(\operatorname{TV}(P,Q)=\tfrac12\|P-Q\|_1\), never raw \(L_1\).

## Definitions

History:

\[
h_t=(Q_{\mathrm{obs}},E_{0:t},a_{0:t-1},o_{1:t},m_{0:t}).
\]

Ideal posterior (oracle / synthetic only):

\[
b_t^*(i)=P(H_i\mid h_t).
\]

Computational belief (live system):

\[
\hat b_t=\mathcal B(z_t).
\]

Inference error, when \(b^*\) exists:

\[
\epsilon_{\mathrm{VI}}=D_{\mathrm{KL}}(\hat b_t\parallel b_t^*).
\]

The direction is never inverted.

Actions in legacy mode remain \(\{ANSWER,EXPLORE,ASK\}\).
Mode v2 MAY enable \(\{ANSWER,ANALYZE,EXPLORE,VERIFY,ASK,DEFER\}\).
`VERIFY` is disabled in legacy traces.

`ANALYZE` MUST NOT add evidence: \(E_{t+1}=E_t\). It updates \(z_t\) only.

Central **HYPOTHESIS** (not a theorem):

> Uncertainty alone does not justify retrieval.

Operational form:

\[
a_t^*=f(\text{uncertainty},\text{recoverability},\text{identifiability},\text{inference error},\text{decision value},\text{interaction value},\text{verification value},\text{graph evidence},\text{cost},\text{risk},\text{budget},\text{model uncertainty}).
\]

## C1 — information difference vs information loss

\[
\Delta_\eta=I(I;Q_{\mathrm{clean}})-I(I;Q_{\mathrm{obs}}).
\]

**PROPOSITION.** If \(I\to Q_{\mathrm{clean}}\to Q_{\mathrm{obs}}\) is Markov, then
\(\Delta_\eta\ge 0\) by the data-processing inequality, and the quantity MAY be
called `information_loss`. Without that chain, record `information_difference`,
which MAY be negative (side information in \(Q_{\mathrm{obs}}\)).

Reference: data processing for mutual information (standard); QUASAR2-specific
naming is in this file.

Harness: `quasar2.theory.harness.check_c1`.

## T1 — variational ANALYZE

For fixed evidence, model, and target posterior \(p\),

\[
\log p(E)=\operatorname{ELBO}(q)+D_{\mathrm{KL}}(q\parallel p(\cdot\mid E)).
\]

**THEOREM** (standard VI algebra). An admissible update that does not decrease
ELBO does not increase \(D_{\mathrm{KL}}(q\parallel p)\), up to declared `atol`.

This **does not** apply automatically to heuristic contradiction propagation.

Reference: Blei, Kucukelbir, McAuliffe, *Variational Inference*, arXiv:1601.00670.

Harness: `check_t1` (mixture projection toward a fixed target).

## T2 — binary VoI identity and bounds

Let \(m_a=bP_1+(1-b)P_2\) and \(b'(o)=b\,dP_1/dm_a\). Then

\[
\mathbb E_{O\sim m_a}|b'(O)-b|=2b(1-b)\operatorname{TV}(P_1,P_2).
\]

If \(|V^*(b')-V^*(b)|\le L_b|b'-b|\) (**scalar_binary**),

\[
\operatorname{VoI}(a)\le 2L_b\,b(1-b)\operatorname{TV}(P_1,P_2).
\]

If \(|V^*(\mathbf b')-V^*(\mathbf b)|\le L_1\|\mathbf b'-\mathbf b\|_1\) (**belief_l1**),
then \(\|\mathbf b'-\mathbf b\|_1=2|b'-b|\) and the factor is \(4L_1\), not \(2L_b\).

Pinsker: \(\operatorname{TV}\le\sqrt{\tfrac12 D_{\mathrm{KL}}}\) when KL is finite.
If both directions are finite, the implementation uses the smaller KL and records
`pinsker_orientation`.

**THEOREM** under the Lipschitz and kernel-correctness assumptions. The bound is
not a claim that JSD is the best empirical predictor of VoI.

For \(K>2\), if \(V^*\) is \(L_U\)-Lipschitz in \(L_1\) on the simplex,

\[
\operatorname{VoI}(a)\le L_U\sqrt{2\operatorname{JSD}_{\mathbf b}(a)},
\qquad
\operatorname{JSD}_{\mathbf b}(a)=I(H;O\mid a,\mathbf b).
\]

Harness: `check_t2`. Family grid: `check_t2_grid` (Bernoulli, Categorical,
HeavyOverlap, NearIdentical, Mixture, discretized Gaussian). The grid compares
0-1 empirical VoI to the Lipschitz bound; a recorded `voi_bound_violated` is
evidence, not an automatic claim promotion.


## T3 — Bellman contraction

For a discounted MDP with bounded rewards and \(\gamma\in[0,1)\), the optimal
Bellman operator \(T\) satisfies

\[
\|TV-TW\|_\infty\le\gamma\|V-W\|_\infty.
\]

If \(V^{(k+1)}=TV^{(k)}\),

\[
\|V^{(k)}-V^*\|_\infty\le\gamma^k\|V^{(0)}-V^*\|_\infty.
\]

When \(V^*\) is not stored, the residual bound

\[
\|V^{(k)}-V^*\|_\infty\le\frac{\gamma^k}{1-\gamma}\|V^{(1)}-V^{(0)}\|_\infty
\]

MUST be used instead of comparing the error to \(\gamma^k\) without the initial
error. The guarantee does **not** automatically transfer to approximate POMDP
solvers.

Reference: standard MDP lecture notes, e.g. Lazaric MVA RL lecture 2.

Harness: `check_t3`.

## T4 — stopping and false stop

If each of \(m\) information-action UCBs is valid at level \(\alpha/m\) at a
**single predeclared look**, Bonferroni controls the fixed-stage false-stop event
at \(\alpha\). This **does not** control repeated sequential inspections.

Sequential modes MUST declare `coverage_scope` in
`{fixed_stage, finite_horizon, anytime}`. Sequential coverage is
`NOT_IMPLEMENTED` in the P0 harness.

NormalUCB, percentile bootstrap, and BCa are **approximate**. Empirical Bernstein
requires a bound on the observation range.

False stop uses `oracle_best_net_voi > delta_positive`. Coverage decisions use a
binomial interval, not a single sample proportion vs \(\alpha\).

Reference: Maurer & Pontil empirical Bernstein (arXiv:0907.3740);
anytime-valid sequences (arXiv:1810.08240) for future sequential work.

Harness: `check_t4`. Family breakdown: `check_t4_families` (Gaussian, Student-t,
Gumbel, skewed, mixture, heavy-tail) at \(\alpha\in\{0.10,0.05,0.01\}\).
Parametric breakdown is recorded as `exceeds_alpha`, not hidden.

Near-zero means \(\mu\in\{-0.05,-0.02,-0.01,0,0.01,0.02,0.05\}\) are checked by
`check_t4_near_zero` comparing Normal, percentile bootstrap, BCa, and Empirical
Bernstein. That check is labeled **INCONCLUSIVE** by design: it is a stress
diagnostic, not a coverage theorem.

Tightness of the T2 Lipschitz bound vs 0-1 empirical VoI is classified
operationally as `tight` / `useful` / `loose` / `vacuous` / `violated` in
`check_t2_grid` and `quasar2 recoverability-bench`. A valid but vacuous bound
does not refute T2.

Decision Recoverability Score (DRS) is \(P_o(\text{0-1 argmax flips})\). It is a
**HYPOTHESIS-level** predictor of empirical VoI, not a theorem.


## Limitations of the bounds

- Lipschitz constants may be unknown on real utilities, producing vacuous bounds.
- Observation kernels on WDI are estimated; kernel error is a separate term.
- Heuristic ANALYZE is not T1.
- Conformal coverage, if used later, is marginal under exchangeability.
- Oracle regret is available only in controlled environments.

## Empirical status

See `docs/THEOREM_STATUS.md` and `artifacts/theorem_checks.json` after
`quasar2 theory-check`. Implementation PASS is not claim SUPPORT.
