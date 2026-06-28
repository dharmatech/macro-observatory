# TGA Explorer Milestone

Status: draft

This document defines the next Macro Observatory implementation milestone: build a static TGA Explorer page inspired by the legacy Streamlit `TGA Explorer` page.

The goal is not a line-by-line port. The goal is to preserve the useful exploratory behavior while adapting the implementation to Macro Observatory's static-site architecture.

## Why This Page Next

TGA Explorer is a strong second page because it exercises a much larger Treasury Fiscal Data dataset than the Fed Net Liquidity chart.

It should help validate whether the current architecture handles larger browser-facing artifacts, including:

- source cache size,
- reduced site artifact size,
- JSON fetch and parse time,
- browser-side filtering time,
- Plotly rendering time,
- practical guardrails for large chart renders.

The same source dataset should also support future pages such as TGA Explorer variants, TGA Top, and TGA Taxes Year Compare.

## Source Dataset

The raw source comes from the Treasury Fiscal Data Daily Treasury Statement endpoint for deposits and withdrawals of operating cash:

```text
/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash
```

The source cache should use a provenance-first, endpoint-derived name even if it is long. The exact filename can be adjusted to match existing project conventions, but the intent is clear traceability from local file to source endpoint.

Expected source cache shape:

```text
data/cache/sources/treasury_dts_deposits_withdrawals_operating_cash.parquet
data/cache/metadata/treasury_dts_deposits_withdrawals_operating_cash.json
```

The source cache should retain all columns from the Treasury endpoint so users can inspect the full dataset in Pandas and future pages can derive other views from it.

## Browser Artifact

The browser should not load the full raw source dataset for the first TGA Explorer page.

Publish a reduced artifact with only the fields needed by the base explorer page:

```text
record_date
transaction_catg
transaction_type
transaction_today_amt
transaction_mtd_amt
transaction_fytd_amt
```

Expected site artifacts:

```text
site/data/tga-explorer.json
site/data/tga-explorer.csv
site/data/tga-explorer-metadata.json
```

The JSON artifact is the v1 browser contract for this page. It should use a compact JSON `split` shape with `columns` and `data` fields so row data does not repeat field names hundreds of thousands of times. Compact binary formats such as Arrow or Parquet remain future research until JSON performance has been measured against this larger page.

## Data Artifact Checkpoint Result

The first data artifact checkpoint is complete.

Local result at checkpoint time:

```text
source rows: 472,569
derived rows: 453,385
date range: 2005-10-03 to 2026-06-25
source parquet: 3,831.5 KB
derived parquet: 3,502.6 KB
site JSON: 32,359.0 KB
site CSV: 29,275.6 KB
metadata JSON: 2.6 KB
```

A local comparison showed row-record JSON would have been about 85.9 MB. The compact JSON `split` orientation reduced the browser JSON artifact to about 32.4 MB while keeping the artifact simple JSON for the first page implementation.

## Controls

The static page should preserve the core Streamlit sidebar controls in browser form.

Initial controls:

- metric select: `transaction_today_amt`, `transaction_mtd_amt`, `transaction_fytd_amt`
- category filter toggle and multiselect
- deposits toggle
- withdrawals toggle
- public debt toggle
- year start input
- minimum amount input

Initial defaults should match the Streamlit page unless local testing shows a clear reason to adjust them:

```text
metric: transaction_fytd_amt
category filter: off
deposits: on
withdrawals: on
public debt: off
year start: 2022
minimum amount: 100000
```

The minimum amount default should continue to depend on the selected metric:

```text
transaction_today_amt: 1000
transaction_mtd_amt: 10000
transaction_fytd_amt: 100000
```

## Filter Semantics

The browser implementation should reproduce the base Streamlit semantics in spirit:

- Exclude categories equal to `null`, `Sub-Total Withdrawals`, and `Sub-Total Deposits`.
- Exclude transfer categories that are implementation noise in the legacy page.
- When public debt is off, exclude categories containing `public debt`, case-insensitive.
- When deposits is off, exclude rows with `transaction_type == "Deposits"`.
- When withdrawals is off, exclude rows with `transaction_type == "Withdrawals"`.
- Convert withdrawal amounts to negative values before charting.
- Filter to `record_date >= "{year}-10-01"`.
- Filter to rows where `abs(selected_metric) > minimum_amount`.

The exact transfer-category exclusion list should be centralized so future TGA pages can review or reuse it.

## Chart

The first static page should use Plotly as the baseline renderer.

Expected chart behavior:

- stacked/relative bar chart,
- x-axis: `record_date`,
- y-axis: selected metric,
- color/grouping: `transaction_catg`,
- withdrawals shown as negative values,
- responsive width similar to the Fed Net Liquidity page.

Plotly is the practical baseline, not a permanent commitment. If this page exposes rendering limits, future work can evaluate WebGL, canvas, Arrow, Parquet, DuckDB-Wasm, chunked artifacts, or pre-aggregation.

## Render Guardrail

The page should avoid freezing the browser when filters produce too many rows.

Initial guardrail:

```text
max render rows: 10000
```

If the filtered row count exceeds the threshold:

- update the record count,
- do not redraw the chart,
- show a concise warning asking the user to narrow filters,
- keep the controls responsive.

The threshold is a tuning value. It can be raised or lowered after testing on the actual JSON artifact and chart shape.

## Performance Diagnostics

The page should display subtle, local-only timing diagnostics. These should help distinguish data loading bottlenecks from chart rendering bottlenecks.

Initial metrics:

- data fetch time,
- JSON parse time,
- filter time,
- trace preparation time,
- Plotly render time,
- filtered row count.

A compact display is enough, for example:

```text
Rows 4,812 | Data 420 ms | Parse 80 ms | Filter 12 ms | Render 910 ms
```

Diagnostics should be computed in the browser with `performance.now()`. They should not be sent anywhere or treated as analytics.

## Metadata

Publish metadata next to the browser artifact.

Useful metadata fields:

- artifact name,
- source dataset ID,
- source endpoint,
- generated timestamp,
- row count,
- date range,
- category count,
- transaction types,
- field list,
- source cache filename,
- notes about units and sign handling.

The metadata should make it easy to inspect file freshness and reason about browser artifact size.

## Checkpoint Sequence

Implementation should proceed in two checkpoints.

### 1. Data Artifact Checkpoint

Complete when Macro Observatory can:

- fetch/update the full Treasury source endpoint,
- cache it as Parquet,
- reload it as a Pandas dataframe,
- publish the reduced `tga-explorer.json` artifact,
- publish companion metadata,
- report file sizes with the storage report command.

Stop after this checkpoint to inspect the Parquet, JSON, metadata, and file sizes before building the page UI.

### 2. Page Checkpoint

Complete when the static site can:

- show a TGA Explorer page from `site/data/tga-explorer.json`,
- render the baseline Plotly chart,
- provide the controls listed above,
- show total filtered row count,
- enforce the render guardrail,
- display subtle timing diagnostics,
- link from the site index to the new page.

## Non-Goals

- Port every TGA Explorer variant in this checkpoint.
- Build TGA Diff, TGA Net, or Year Compare immediately.
- Replace JSON with Arrow or Parquet in the browser.
- Replace Plotly before measuring the baseline.
- Build a general browser dataframe console.
- Optimize all Treasury datasets before the first TGA Explorer page works.

## Open Questions

- Is the first performance limit data transfer, JSON parsing, filtering, trace construction, or Plotly rendering?
- Is `10000` rows the right initial render threshold?
- Should public debt be controlled by category text matching only, or should a reviewed category list be maintained?
- Should the category multiselect include search behavior for large category lists?
- Should future TGA Explorer variants share the same browser artifact or publish separate derived artifacts?
