# Neural retrieval (V2.4)

**Environment recorded:** 2026-08-26, Windows 11, Python 3.13.3, torch 2.13.0+cpu, sentence-transformers 6.0.0, CUDA unavailable.

Install (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[neural]"
quasar2 neural-doctor
```

Do not build PyTorch from source. Official cp313 Windows CPU wheels were used.

## Profiles

| ID | Model | Role | Prefix | Status on this machine |
|---|---|---|---|---|
| H0 | hashing-vector | debug / negative control | none | implemented; **not neural** |
| MiniLM | `sentence-transformers/all-MiniLM-L6-v2` | R0 smoke | none | encoded and retrieved WDI metadata |
| N1 | `intfloat/multilingual-e5-base` | multilingual dense | `query:` / `passage:` | encoded CI WDI docs; GDP query ranked `ind:NY.GDP.PCAP.CD` |
| N2 | `BAAI/bge-m3` | primary strong neural | none (unless card changes) | encoded CI WDI docs; PT query ranked GDP per capita first |
| N3 | BM25 + BGE-M3 hybrid | hybrid | — | factory backend `hybrid_bge` |
| N4 | hybrid + `BAAI/bge-reranker-v2-m3` | rerank | — | class `CrossEncoderReranker` present; full-benchmark N4 **not run** (CPU projection: CrossEncoder over 3k×pool is expensive) |

Embeddings are L2-normalized; scores are cosine/dot-product on the unit sphere.

Cache key: SHA-256 of model id, profile, document ids, and normalization flag.

## Attribution vs hashing

`dense` / `dense_hash` remain `DEBUG_BACKENDS`. Scientific backends: `neural`, `e5`, `bge-m3`, `hybrid_neural`, `hybrid_bge`.
