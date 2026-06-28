# Treasury Securities Net Issuance Milestone

Status: browser artifact and static page checkpoint implemented

This document defines the next Macro Observatory implementation milestone: build a static Treasury Securities Net Issuance page inspired by the legacy Streamlit `Treasury Securities Net Issuance Resample` page.

The goal is not a line-by-line port. The goal is to preserve the useful behavior while adapting the implementation to Macro Observatory's source-cache, derived-cache, browser-artifact, and static-page architecture.

## Why This Page Next

This page adds a new Treasury Fiscal Data endpoint and a new derived dataset shape. The current pages cover Fed Net Liquidity and TGA Explorer. This page adds Treasury auction data and derives issuance and maturity flows by security type.

It should validate:

- another Treasury Fiscal Data source dataset,
- full-source endpoint caching for exploratory Pandas use,
- a compact derived dataset for browser rendering,
- precomputed pandas grouping by day, week, month end, quarter end, and year end,
- a third dashboard page on the static site.

The same source dataset should support future Treasury securities pages, including cumulative issuance views and the SPX comparison variant.

## Legacy Page

Legacy Streamlit page:

```text
C:\Users\dharm\Dropbox\Documents\fed_net_liquidity_streamlit.py\pages\5_Treasury_Securities_Net_Issuance_Resample.py
```

Original source project file:

```text
C:\Users\dharm\Dropbox\Documents\treasury-securities-net-issuance.py\treasury-securities-net-issuance-resample-after.py
```

The legacy page loads Treasury auction rows, computes net issuance by security type, and lets the user choose a pandas resample frequency:

```text
D, W, ME, QE, YE
```

The default legacy grouping is `ME`, month end.

## Source Dataset

The raw source comes from the Treasury Fiscal Data auctions query endpoint:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query
```

Proposed source dataset ID:

```text
treasury_od_auctions_query
```

Expected source cache paths:

```text
data/cache/sources/treasury_od_auctions_query.parquet
data/cache/metadata/treasury_od_auctions_query.json
```

The source cache should preserve the full endpoint, not only the columns needed by this first page. That keeps the dataset useful for Pandas inspection and future Treasury securities pages.

Initial required source columns:

```text
record_date
cusip
security_type
auction_date
issue_date
maturity_date
total_accepted
```

The legacy cache had repeated `cusip` values, but no duplicates for this fuller key:

```text
record_date, cusip, auction_date, issue_date, maturity_date
```

## Source Dataset Checkpoint Result

The source dataset checkpoint is implemented and locally validated.

Local result on June 28, 2026:

```text
rows: 11,022
columns: 113
date range: 1979-11-15 to 2026-07-02
issue date range: 1979-11-15 to 2026-07-02
maturity date range: 1980-04-03 to 2056-05-15
duplicate primary keys: 0
source parquet: 1,958.3 KB
metadata JSON: 18.5 KB
```

The immediate second update validated incremental behavior:

```text
rows before: 11,022
rows fetched: 21
rows after: 11,022
```

The live Fiscal Data metadata currently reports `total_accepted` as `NUMBER` with data format `10.2`, and the cached source treats it as U.S. dollars. Four current rows have null `total_accepted`; later derived builders should handle those rows explicitly.

The current endpoint already includes future issue and maturity dates, so the future-maturities note remains part of the page design.

## Derived Dataset

Proposed derived dataset ID:

```text
treasury_securities_net_issuance
```

Expected derived cache paths:

```text
data/cache/derived/treasury_securities_net_issuance.parquet
data/cache/metadata/treasury_securities_net_issuance.json
```

The derived dataset should normalize security types and compute daily issued, maturing, and net change amounts by security type.

Initial normalized security type policy:

```text
TIPS Note -> Note
FRN Note  -> Note
TIPS Bond -> Bond
CMB       -> Bill
```

Initial output columns:

```text
frequency
date
security_type
issued
maturing
net_issuance
```

Formula:

```text
net_issuance = issued - maturing
```

The derived dataset precomputes all legacy pandas frequencies:

```text
D, W, ME, QE, YE
```

`W` uses pandas' default `W-SUN` boundary. `ME` is summed at month end and then labeled with month-start dates to match the legacy Streamlit page. The first chart can render only `net_issuance`, but preserving `issued` and `maturing` keeps the derived dataset useful for later pages.

## Derived Dataset Checkpoint Result

The derived dataset checkpoint is implemented and locally validated.

Local result on June 28, 2026:

```text
source rows: 11,022
valid total_accepted rows: 11,018
null total_accepted rows: 4
issue_date null rows: 0
maturity_date null rows: 0
derived rows: 99,717
date range: 1979-11-01 to 2056-12-31
security types: Bill, Bond, Note
derived parquet: 635.8 KB
metadata JSON: 2.1 KB
```

Rows by frequency:

```text
D     83,826
W     11,979
ME     2,757
QE       921
YE       234
```

The derived cache preserves future maturities through 2056 and keeps all five grouped frequencies in one Pandas-friendly long-form Parquet file.

## Future Maturities

This dataset naturally includes future maturity dates. The legacy cache had maturity dates extending decades beyond the latest issue date.

That behavior is preserved in the derived cache. The page and metadata should make clear that the chart can include scheduled future maturities from already-known Treasury securities, not only historical observations. The page should also include a subtle vertical `Today` marker so the historical/future boundary remains visible while zooming.

## Browser Artifact And Page

The browser should not load the full raw auctions endpoint. Publish a compact artifact from the derived dataset:

```text
site/data/treasury-securities-net-issuance.json
site/data/treasury-securities-net-issuance.csv
site/data/treasury-securities-net-issuance-metadata.json
```

Proposed static page path:

```text
site/pages/treasury-securities-net-issuance/
```

Proposed JavaScript path:

```text
site/assets/js/treasury-securities-net-issuance.js
```

Initial controls:

- grouping select: `D`, `W`, `ME`, `QE`, `YE`
- chart metric fixed to `net_issuance` for the first version
- shared chart expand/restore behavior

Initial chart:

- Plotly bar chart,
- x-axis: grouped date,
- y-axis: net issuance,
- series: `Bill`, `Note`, `Bond`,
- default grouping: `ME`.

The browser artifact should publish the precomputed frequency rows from the derived cache. The page can switch among day, week, month end, quarter end, or year end without reimplementing pandas resampling in JavaScript.

## Browser Artifact And Page Checkpoint Result

The browser artifact and static page checkpoint is implemented and locally validated.

Local result on June 28, 2026:

```text
published rows: 99,717
JSON artifact: 4,033.4 KB
CSV artifact: 3,351.7 KB
metadata JSON: 2.7 KB
default frequency: ME
security types: Bill, Bond, Note
```

Non-zero `net_issuance` chart points by frequency:

```text
D      5,474
W      4,508
ME     1,666
QE       680
YE       181
```

The page uses compact JSON `split` orientation, decodes the artifact once, and filters by frequency and security type in JavaScript. It sends only non-zero `net_issuance` points to Plotly so daily mode remains practical while the artifact and CSV preserve all rows.

Implemented page paths:

```text
site/pages/treasury-securities-net-issuance/index.html
site/assets/js/treasury-securities-net-issuance.js
```

Implemented artifact paths:

```text
site/data/treasury-securities-net-issuance.json
site/data/treasury-securities-net-issuance.csv
site/data/treasury-securities-net-issuance-metadata.json
```

Local `build-site --from-cache` now reports `4` derived datasets, `3` published datasets, and `0` source updates.

## Metadata

Useful metadata fields:

- source endpoint,
- source dataset ID,
- derived dataset ID,
- source row count,
- derived row count,
- date range,
- normalized security type mapping,
- amount columns,
- units,
- future maturity note,
- supported grouping frequencies,
- default grouping,
- pandas resample policy.

## GitHub Actions Cache Sequencing

Adding this dataset to the aggregate static-site pipeline changes the cache contract.

The current GitHub Actions data cache does not yet contain:

```text
treasury_od_auctions_query
treasury_securities_net_issuance
```

If the new source, derived dataset, and page are wired into aggregate `build-site --from-cache` before the Actions cache is intentionally refreshed, push-triggered Pages deployments can fail because the required cache files will be missing.

Implementation should keep this sequence explicit:

1. implement and validate the source dataset locally,
2. implement and validate the derived dataset locally,
3. implement and validate browser artifact publishing locally,
4. implement and validate the static page locally,
5. wire the new datasets/page into aggregate `build-site`,
6. push the code,
7. run an intentional manual source-update workflow to populate the new Actions cache,
8. confirm later push deploys work from cache.

## Scheduled Refresh

The legacy Streamlit project had an auctions cron hint around 2:00 PM Pacific on weekdays.

Scheduled refresh is out of scope for the first page implementation. After the page and cache sequencing are validated, add a Treasury auctions refresh group to `.github/workflows/scheduled-refresh.yml`.

Likely future refresh group:

```text
treasury_auctions_daily -> treasury_od_auctions_query
```

The exact time should be checked against current Treasury publishing behavior before enabling the schedule.

## Checkpoint Sequence

### 1. Source Dataset Checkpoint

Completed. Macro Observatory can register `treasury_od_auctions_query`, fetch the full endpoint with pagination, update incrementally, cache source Parquet and metadata, load the dataset in Pandas, and show it through `datasets`, `info`, `show`, and `storage-report`.

This checkpoint stopped after inspecting schema, row count, date ranges, file size, and primary-key behavior.

### 2. Derived Dataset Checkpoint

Completed. Macro Observatory can build `treasury_securities_net_issuance`, normalize security types, compute issued, maturing, and net issuance by date and security type, preserve future maturity dates, precompute `D`, `W`, `ME`, `QE`, and `YE` with pandas, and cache derived Parquet plus metadata.

This checkpoint stopped after validating row counts, frequency ranges, null handling, future maturity preservation, and file size.

### 3. Browser Artifact Checkpoint

Completed. Macro Observatory can publish JSON, CSV, and metadata companions for `treasury-securities-net-issuance` and report file sizes in `storage-report`.

### 4. Page Checkpoint

Completed. The static site can show the Treasury Securities Net Issuance page, render the Plotly bar chart, switch grouping among `D`, `W`, `ME`, `QE`, and `YE`, default to `ME`, show security-type toggles, show a `Today` marker, report subtle timing diagnostics, use shared chart expand/restore behavior, and link from the site index.

### 5. Aggregate Build And Actions Cache Checkpoint

Remote cache refresh completed. Aggregate `build-site` includes the new source, derived dataset, publish artifact, and page; local `build-site --from-cache` works with the local cache; manual Pages run `28328939575` intentionally refreshed the GitHub Actions data cache with `treasury_od_auctions_query`, rebuilt `4` derived datasets, published `3` browser artifacts, saved cache key `macro-observatory-data-cache-v1-Linux-28328939575`, and deployed the new page. The next push-triggered deployment should now restore the refreshed cache without source API calls.

## Non-Goals

- Port the SPX comparison variant in this milestone.
- Add yfinance or market-data dependencies in this milestone.
- Add cumulative chart mode in the first version.
- Add every Treasury securities view from the legacy project.
- Replace Plotly before testing the baseline page.
- Add scheduled auctions refresh before cache sequencing is validated.

## Open Questions

- Should a later revision expose `issued` and `maturing` as optional chart metrics?
- Should the chart mode later support line and cumulative views from the adjacent legacy page?
- What is the best scheduled refresh time for the auctions endpoint after current Treasury publishing behavior is checked?
