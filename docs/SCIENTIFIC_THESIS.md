# Scientific thesis and formalization

## 1. Scope

QUASAR2 studies information retrieval when a user's observed query is an
incomplete, noisy, or partially misleading measurement of an unobserved
information need. The method does not claim that every query has one objectively
correct interpretation; the benchmark defines a latent intent only to make the
POC falsifiable.

## 2. Variables

- \(I\): latent intent defined by the evaluation fixture;
- \(Q_{obs}\): observed, possibly degraded query;
- \(S(Q_{obs})\): extracted weak signals;
- \(H=\{H_1,\dots,H_k\}\): explicit candidate interpretations;
- \(E_t\): novel evidence acquired at round \(t\);
- \(b_t(H_i)\): normalized belief assigned to \(H_i\);
- \(a_t\in\{ANSWER,EXPLORE,ASK\}\): selected action.

The implemented loop approximates:

\[
b_t(H_i) \propto b_{t-1}(H_i)
\exp\left(\lambda\,[s(E_t,H_i)-\bar{s}(E_t)]\right),
\]

where \(s\) is a transparent evidence-support function and \(\bar{s}\) centers
support across hypotheses. It is a posterior-like update, not a claim that the
feature score is a calibrated likelihood.

The action policy applies quality gates and compares auditable utilities:

\[
U_{answer}=p^* - c_w(1-p^*) + \alpha e^*,
\]

\[
U_{explore}=\widehat{IG}(H;E_{t+1})-c_e,
\qquad
U_{ask}=\rho(1-p^*)-c_a.
\]

Here \(p^*\) is the leading belief, \(e^*\) its strongest accumulated evidence,
and \(\widehat{IG}\) is an entropy-and-separation proxy. The proxy must be
calibrated or replaced before interpreting it as real expected information gain.

## 3. Primary POC hypotheses

### H1 — competing interpretations

At matched corpus and retrieval budget, `Full` should recover more latent intents
than `noHyp`, especially as query degradation increases.

### H2 — discriminative exploration

At matched answer-quality requirements, `Full` should improve correct autonomous
resolution over `noExplore`, with a measurable cost in extra retrieval calls.

### H3 — iterative belief fusion

`Full` should outperform `noUpdate` when independently useful evidence arrives
across rounds.

### H4 — calibrated abstention

`Full` should exhibit a better wrong-answer/coverage tradeoff than `noAsk`; raw
answer rate alone is not a success metric.

### H5 — strong compatible baselines

Any general performance claim requires `Full` to beat or trade favorably against
strong compatible retrieval and rewrite systems, not only its own ablations.

## 4. Falsification conditions

The hypothesis is weakened or falsified for a tested regime when any of the
following persists with paired uncertainty excluding a practically meaningful
benefit:

- `Full` does not improve intent recovery over `noHyp`;
- exploration consumes more calls without improving the correct-resolution
  frontier over `noExplore`;
- strong direct or single-rewrite baselines dominate accuracy, cost, and
  abstention;
- results disappear under unseen seeds, real corpora, or leakage controls;
- gains require duplicated or label-derived evidence;
- threshold changes reverse conclusions across reasonable calibration choices.

## 5. What is frozen and what is not

Frozen for v0.1:

- observation → hypotheses → evidence → belief → decision loop;
- three actions `ANSWER`, `EXPLORE`, and `ASK`;
- explicit, competing hypotheses rather than one hidden rewrite;
- inference-time belief updates only;
- mechanism comparisons through baselines and ablations.

Not frozen:

- the specific evidence feature weights;
- the hashing-vector proxy;
- decision thresholds and utility coefficients;
- corpus size and domain choice;
- the method used by a future Mode-B backend.

Changing non-frozen parameters after observing test results requires a new
version and a new untouched test partition.

