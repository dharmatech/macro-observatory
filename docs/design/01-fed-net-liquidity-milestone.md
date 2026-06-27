# Fed Net Liquidity Milestone

Status: draft

This document defines the first implementation milestone for Macro Observatory: build one complete Fed Net Liquidity pipeline and render one static web presentation from it.

The purpose of this milestone is to prove the architecture end to end without porting the full existing Streamlit application.

## Target Outcome

The milestone is complete when Macro Observatory can:

- fetch the required source datasets,
- update them incrementally,
- store them in a durable local cache,
- reload them as Pandas dataframes,
- combine them into a derived Fed Net Liquidity dataframe,
- publish compact static data artifacts,
- render an interactive Fed Net Liquidity chart on GitHub Pages or a local static preview,
- expose a simple user path for inspecting the underlying data.

The first chart should be intentionally modest. It should prove the source-to-chart pipeline before we expand to more Streamlit-style pages.

## First Chart

The first presentation should be a Fed Net Liquidity time-series chart similar in spirit to the existing Streamlit line chart.

Expected visible series:

- `WALCL`
- `RRP`
- `TGA`
- `REM`, if retained in the formula
- `NL`

The first version may use Plotly.js because the existing Streamlit app already uses Plotly and the interaction model is familiar. The published data should remain presentation-neutral so that another charting library can be tested later.

## Source Datasets

### FRED `WALCL`

`WALCL` provides Federal Reserve balance sheet data used as the main positive component in the net liquidity calculation.

Sub-milestone requirements:

- fetch `WALCL` from FRED,
- support configured FRED API credentials,
- cache the dataset locally,
- reload it as a Pandas dataframe,
- perform an incremental update with overlap,
- expose basic dataset metadata: row count, date range, last update time,
- provide a simple user-facing way to preview or load the dataset.

### FRED `RESPPLLOPNWW`

The existing `fed_net_liquidity.py` code loads `RESPPLLOPNWW` and names it `REM`.

This source should be included if the milestone keeps the existing code formula:

```text
NL = WALCL - RRP - TGA - REM
```

Sub-milestone requirements are the same as `WALCL`.

This source also requires a checkpoint to confirm the intended economic interpretation, display label, units, and whether it belongs in the canonical formula.

### New York Fed RRP

The RRP source provides reverse repo operation data.

The existing code uses:

- `operationDate`
- `totalAmtAccepted`
- `note`

Existing behavior to review and likely preserve:

- filter out rows where `note` contains small-value markers,
- when multiple rows share an `operationDate`, keep the row with the highest `totalAmtAccepted`,
- sort by operation date before merging.

Sub-milestone requirements:

- fetch RRP data from the New York Fed source,
- cache the dataset locally,
- reload it as a Pandas dataframe,
- perform an incremental update with overlap,
- normalize the date and amount columns,
- apply reviewed filtering and duplicate-date behavior,
- expose metadata and preview/load commands.

### Treasury Fiscal Data TGA

The TGA source comes from the Treasury Fiscal Data API endpoint for Daily Treasury Statement operating cash balance data:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance
```

The existing code extracts rows from several account types:

- `Federal Reserve Account`
- `Treasury General Account (TGA)`
- `Treasury General Account (TGA) Closing Balance`

Existing behavior to review:

- use `close_today_bal` for some account types,
- use `open_today_bal` for `Treasury General Account (TGA) Closing Balance`,
- combine those rows into a normalized `TGA` series.

Sub-milestone requirements:

- fetch the operating cash balance dataset from Treasury Fiscal Data,
- support any required contact metadata without committing secrets,
- cache the dataset locally,
- reload it as a Pandas dataframe,
- perform an incremental update with overlap,
- normalize account/date/balance fields,
- expose metadata and preview/load commands.

## Derived Dataset

After the source datasets are available, build a derived `fed_net_liquidity` dataframe.

Expected columns:

- `date`
- `WALCL`
- `RRP`
- `TGA`
- `REM`, if retained
- `NL`
- component diff columns, if useful for the first table

Expected transform behavior:

- normalize source date columns to a common `date` column,
- outer-join source series by date,
- sort by date,
- forward-fill component values,
- convert numeric source columns safely,
- normalize units,
- compute `NL`,
- compute first differences if the first table needs them.

The derived dataframe should be compared against the current `fed_net_liquidity.py` output before the milestone is considered complete.

## Formula Decision

There is an existing mismatch that must be resolved before treating the output as canonical.

The existing README says:

```text
Fed Net Liquidity = WALCL - RRP - TGA
```

The existing code computes:

```text
NL = WALCL - RRP - TGA - REM
```

For implementation, it is acceptable to reproduce the existing code formula first, but the milestone should keep this as an explicit checkpoint. The final chart and metadata must say which formula is being used.

## Units

Unit handling must be verified source by source.

The existing code multiplies `WALCL`, `TGA`, and `REM` by `1_000_000`, while leaving `RRP` unchanged. The milestone should confirm the source units before freezing the transform.

Dataset metadata should record display units and source units where practical.

## Cache And Published Artifacts

The milestone should distinguish between internal cache files and browser-facing files.

Internal cache files are for repeatable incremental updates and Pandas inspection. Parquet is the likely v1 format, but this remains open until implementation.

Published artifacts are for the static site. Likely first artifacts:

- `fed-net-liquidity.json` for the chart,
- `fed-net-liquidity.csv` for download,
- `fed-net-liquidity.parquet` or an equivalent Pandas-friendly artifact, if practical,
- dataset metadata with formula, source names, row count, date range, and build timestamp.

The browser should not need to load large raw source caches for the first chart.

## User Inspection Requirements

Each maintained dataset should be inspectable by name.

The exact command-line interface is not decided yet, but the user experience should support operations like:

```text
datasets
update walcl
info walcl
show walcl
export walcl --format csv
```

The Python inspection path should be simple:

```python
from macro_observatory.data import load_dataset

df = load_dataset("fed_net_liquidity")
```

The first chart should eventually show a small "open in Pandas" or "inspect data" affordance with a snippet like the above.

## Secrets

Secrets must be available to the data-update step but must not appear in generated public artifacts.

Expected secret-like values:

- FRED API key,
- Treasury contact email or equivalent request metadata, if used,
- any future API tokens.

Local development can use environment variables or a local uncommitted `.env` file. GitHub Actions should use repository secrets.

## Checkpoint Sequence

Implementation should stop for review after each checkpoint:

1. FRED `WALCL` fetch, cache, reload, incremental update, inspect.
2. FRED `RESPPLLOPNWW` fetch, cache, reload, incremental update, inspect, if retained.
3. New York Fed RRP fetch, cache, reload, normalization, incremental update, inspect.
4. Treasury TGA fetch, cache, reload, normalization, incremental update, inspect.
5. Derived Fed Net Liquidity dataframe and comparison against the existing implementation.
6. Published static data artifacts.
7. First static chart and simple data table.

## Non-Goals

- Recreate all Streamlit pages.
- Build the full site navigation.
- Implement every Treasury dataset.
- Optimize large Treasury browser payloads.
- Decide the final charting library for all future pages.
- Build production DigitalOcean deployment scripts.

## Open Questions

- Which formula should be canonical?
- What exact source label should be used for `REM`?
- Should `RESPPLLOPNWW` be visible in the first chart by default?
- What cache format should be selected for v1?
- Should source caches be committed, stored as generated artifacts, or handled another way?
- What exact CLI command name should the project expose?
- What update schedule should be used for each source in GitHub Actions?
- What validation tolerances should be used when comparing to the existing `fed_net_liquidity.py` output?
