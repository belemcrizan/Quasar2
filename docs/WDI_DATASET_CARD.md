# WDI dataset card (V2.4 developmental)

## Identity

- Source: World Bank World Development Indicators (API V2, source=2)
- CI snapshot: `wdi-ci-2026-08-26-6ead85fe` (8 countries + LCN aggregate, 12 indicators, 1152 observation rows, 981 observed / 171 missing)
- Pilot snapshot: `wdi-pilot-2026-08-26-b6ddb672` (20 countries + aggregate, 30 indicators, 15120 rows, 12889 observed / 2231 missing)
- Period coverage (pilot): 2000–2023
- Brazil is included.

## Sampling (frozen before method comparison)

Indicators were listed in `src/quasar2/wdi/catalog.py` to cover national accounts, poverty, prices, labor, health, education, energy, emissions, trade, connectivity, finance, gender, and institutions. Two originally requested codes were invalid on source 2 (`EN.ATM.CO2E.PC`, `IS.ROD.DNST.K2`, `CC.EST`) and were replaced with currently valid series (`EN.GHG.CO2.PC.CE.AR5`, `IT.NET.BBND.P2`, `SP.POP.GROW`). Replacement was for API validity, not QUASAR2 accuracy.

## Intended use

Offline structured intent and observation evaluation. Not a global WDI census. Not for macroeconomic publication without citing World Bank vintage.

## Known biases

- English metadata dominates retrieval documents.
- Annual series only in this slice.
- Literacy and some social indicators have high missingness.
- Entity list is a convenience sample, not a probability sample of all WDI economies.
