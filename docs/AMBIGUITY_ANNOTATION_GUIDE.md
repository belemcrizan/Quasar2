# Ambiguity annotation guide (developmental)

Use only when structured WDI truth is insufficient (natural multi-intent questions).

For each query, two annotators independently mark:

1. plausible indicator/entity/period interpretations (multi-label allowed)
2. whether a user preference is required
3. the minimum useful clarification question, if any
4. whether a committed numeric answer is justified from WDI alone

Adjudicate disagreements. Report raw agreement and multi-label Jaccard. Do not show system traces to annotators. Do not encode `expected_action` as primary truth.
