# Source registry (current cycle)

Typed source families live in `quasar2.sources.registry`. Offline metadata fixtures live under `data/sources/fixtures/`.

| Family | Role this cycle | Official docs |
|---|---|---|
| WORLD_BANK_WDI | Frozen numeric/temporal ground truth | https://datahelpdesk.worldbank.org/knowledgebase/articles/889392 |
| JWST_MAST | Metadata-only fixture, not a completed JWST benchmark | https://outerspace.stsci.edu/spaces/MASTDOCS/pages/153686876/API+Advanced+Search |
| JWST_CRDS | Descriptor only; calibration context is not “newer is better” | https://jwst-docs.stsci.edu/accessing-jwst-data/citing-jwst-data |
| NASA_ADS | Descriptor; abstracts are not full claims | https://ui.adsabs.harvard.edu/help/api/ |
| CERN_OPEN_DATA | Metadata-only fixture; data levels are not interchangeable | https://opendata.cern.ch/docs/about |
| INSPIRE_HEP | Metadata-only fixture; not event data | https://github.com/inspirehep/rest-api-doc |

Cross-source answer synthesis is out of scope. Time-travel evaluation must use cutoff-filtered local records, not a live current index.

Cycle 3 source audit (NASA Exoplanet Archive, Gaia, ALMA selected; ADS/HEASARC/ESO useful; scrape/PR/Wikipedia rejected as primary) lives in `quasar2.external.source_audit` and `docs/EXTERNAL_VALIDITY.md`. Executed snapshots are schema-faithful, not TAP dumps.

```text
quasar2 source-validate --family jwst_mast
quasar2 jwst-validate
quasar2 cern-validate
quasar2 source-validate --family worldbank_wdi --snapshot data/wdi/snapshots/ci-offline
```
