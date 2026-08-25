# External collections

The bundled ops fixture is a closed overlapping-runbook case. It is harder than
the astronomy/AI sanity set and still too small for a general IR claim.

To attach a private or public corpus:

1. Write JSONL documents with `id`, `domain`, `title`, `text`, `hypothesis_ids`.
2. Write a hypothesis catalog JSON and an intents JSON (`q0` required).
3. Point `configs/*.yaml` `paths` at those directories.
4. Keep the v0.1.1 loop frozen; only swap `retrieval.backend`.

Do not mix an external corpus into `data/corpus/` next to the sanity JSONL files.
