# External validity protocol (Cycle 3)

This is a **protocol and offline map**, not a completed NASA/ESA confirmatory paper.

Official sources were audited. The executed benchmark uses:

- `SCHEMA_FAITHFUL_SYNTHETIC` records with `SYN-` identifiers (not TAP dumps);
- the existing JWST/MAST **metadata fixture**;
- OPS structured states clustered by incident class;
- frozen v0.1.1 and Cycle 2 artifacts reconstructed, not retuned.

Commands:

```bash
quasar2 external-validity --output experiments/results/external_validity --overwrite
quasar2 external-validity --smoke --overwrite
quasar2 reproduce-paper --output experiments/results/paper_reproduce --overwrite
```

Container:

```bash
docker build -t quasar2-repro .
docker run --rm quasar2-repro
```

Do not cite `SYN-KOI-*` / `SYN-Gaia-*` / `SYN-ALMA-*` as archive rows.

Gate 1 remains FAIL. The experimental policy remains shadow.
