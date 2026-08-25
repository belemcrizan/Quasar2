# Ablations

The `ablation=` switch on `QuasarPipeline.run` supports:

- `full`: complete POC;
- `noHyp`: retain only the first hypothesis (single commitment);
- `noExplore`: disable autonomous discriminative retrieval;
- `noUpdate`: freeze beliefs after hypothesis generation;
- `noAsk`: disable the clarification action and force an answer after exploration.

These are mechanism ablations, not separate tuned systems. Shared thresholds are
intentional, but a publication-quality study should additionally report tuned
and untuned variants so threshold sensitivity is visible.

