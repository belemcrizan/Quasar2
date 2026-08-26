# World Bank WDI in QUASAR2

**API:** Indicators API V2, source ID `2` (World Development Indicators).  
**Docs accessed:** 2026-08-26, https://datahelpdesk.worldbank.org/knowledgebase/articles/889392 and 898581.  
**Terms:** datasets generally CC BY 4.0 plus dataset terms at https://www.worldbank.org/ext/en/legal/terms-conditions/datasets

## Commands

```powershell
quasar2 wdi-sync --source 2 --stage ci --output data/wdi/snapshots/ci-live
quasar2 wdi-validate --snapshot data/wdi/snapshots/ci-live
quasar2 wdi-build-corpus --snapshot data/wdi/snapshots/ci-live
```

Network is used only in `wdi-sync`. Experiments read the local snapshot and fail if hashes change.

## Layout

See `snapshot_manifest.json` plus `raw/`, `normalized/*.jsonl`, `validation_report.json`, `LICENSE_AND_ATTRIBUTION.md`.

Completed snapshots are immutable (`FileExistsError` on overwrite).

## Semantics

- Country endpoint aggregates are typed (`COUNTRY` vs `REGION`/`AGGREGATE`/`INCOME_GROUP`).
- Missing observations stay `NOT_AVAILABLE`; they are never coerced to zero.
- Exact year requests are not replaced by another year. `latest` discloses the resolved period.
