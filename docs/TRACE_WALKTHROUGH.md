# Trace walkthrough

Run:

```bash
quasar2 demo \
  --domain astronomy \
  --query "The starlight keeps dipping when something crosses the disk" \
  --trace
```

## 1. Observation

The extractor normalizes the query and emits weak tokens such as `starlight`,
`dipping`, `crosses`, and `disk`. The estimated degradation is a descriptive
heuristic, not a calibrated probability that the query is corrupted.

## 2. Competing hypotheses

The catalog scorer can retain:

- exoplanet transit because `starlight`, `crosses`, and `disk` match;
- black-hole accretion because `disk` is compatible;
- protoplanetary disk because `disk` is compatible.

Keeping the latter two is intentional. Pruning every weak candidate immediately
would reduce the method to one rewrite.

## 3. Initial evidence

The pipeline retrieves one core document per hypothesis. The evidence scorer
combines:

- normalized retrieval score;
- coverage of original observation tokens;
- coverage of hypothesis anchors;
- coverage of discriminators;
- an optional penalty when corpus provenance labels another hypothesis.

The belief updater centers support across candidates, so only relative evidence
moves the logits.

## 4. EXPLORE

When confidence or margin is too low, the discriminator contrasts the two
leading hypotheses. It selects terms unique to each and issues follow-up
retrieval. The second round uses a larger top-k so it can discover the separate
diagnostic document.

A candidate-document pair already seen in any earlier round is ignored. v0.1.1
also hashes each `(hypothesis, normalized query)` pair. An identical proposed
follow-up is emitted as `EXPLORATION_PRUNED` and never reaches the retriever. If
a distinct query executes but returns zero novel evidence, `ACQUISITION_STOP`
prevents a further exploration round.

Every retrieval event reports `document_novelty`. Every belief event reports
`total_variation` and `observed_entropy_reduction`; the latter may be negative
when evidence legitimately increases uncertainty.

## 5. ANSWER or ASK

An answer requires all three gates:

1. top probability ≥ `answer_confidence`;
2. top-two margin ≥ `answer_margin`;
3. accumulated evidence ≥ `minimum_evidence`.

If the gates still fail after the exploration budget, the default system emits a
clarification question. `noAsk` removes that safety valve and records the forced
answer as an ablation.

## 6. Reading JSON

Use `--json` to inspect:

- every candidate and its generation rationale;
- every retrieved document and scoring feature;
- probabilities and utilities by round;
- final action, selected hypothesis, extractive answer or clarification;
- calls, avoided calls, rounds, pruning reason, novelty, belief movement,
  elapsed time, and complete ordered trace.

## V2 trajectory sketches (hypothesis, not frozen policy)

These sketches describe intended v2 diagnostics. The v0.1.1 loop still executes
only ANSWER / EXPLORE / ASK. Enable `--v2-shadow` to record
`recommended_action_v2` beside `executed_action_legacy`.

### Caso A

query → hypotheses → confidence sufficient → ANSWER

### Caso B

query → ambiguity → high recoverability → EXPLORE → belief update → ANSWER

### Caso C

query → high ambiguity → low recoverability → EXPLORE has low VoI → ASK or DEFER

### Caso D

query → sufficient evidence → high inference error → ANALYZE → lower inference error → ANSWER

ANALYZE in Caso D MUST leave the evidence set unchanged.
