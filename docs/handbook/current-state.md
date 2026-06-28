# Current State

Status: draft

This is the quick handoff for a fresh Macro Observatory session. It records the current architecture, implemented checkpoints, verified commands, local data sizes, and the next likely checkpoint.

## Project Direction

Macro Observatory is a Python-first, Pandas-friendly data pipeline plus static-site frontend for macroeconomic and financial data.

The first hosting target is GitHub Pages. The core commands should stay platform-neutral enough that the same project can later run under cron, another static host, or a managed hosted instance.

Current implementation priorities:

- keep source data inspectable in Pandas,
- keep source caches provenance-rich and reusable,
- publish smaller browser-facing artifacts per page,
- keep future frontend experiments isolated by page or interface directory,
- document useful commands as checkpoints land.

## Completed Design Docs

- `docs/design/00-intro.md`
- `docs/design/01-fed-net-liquidity-milestone.md`
- `docs/design/02-data-layer-and-cache.md`
- `docs/design/03-static-site-interfaces.md`
- `docs/design/04-tga-explorer-milestone.md`
- `docs/design/05-github-pages-deployment.md`
- `docs/design/06-github-actions-cache-persistence.md`
- `docs/design/07-scheduled-refresh-policy.md`
- `docs/design/08-treasury-securities-net-issuance-milestone.md`
- `docs/design/90-future-deployment-options.md`
- `docs/design/91-browser-data-formats.md`

## Completed Handbook Docs

- `docs/handbook/commands.md`
- `docs/handbook/current-state.md`

## Completed Implementation Checkpoints

- FRED `WALCL` source dataset: `fred_walcl`.
- FRED `RESPPLLOPNWW` source dataset: `fred_resppllopnww`.
- New York Fed RRP source dataset: `nyfed_rrp`.
- Treasury Fiscal Data Operating Cash Balance source dataset: `treasury_dts_operating_cash_balance`.
- Derived Treasury General Account dataset: `treasury_tga`.
- Derived Fed Net Liquidity dataset: `fed_net_liquidity`.
- Fed Net Liquidity published browser artifacts under `site/data/`.
- Cross-platform storage diagnostics via `storage-report`.
- Static site shell and Fed Net Liquidity Plotly page under `site/`.
- Treasury Fiscal Data Deposits and Withdrawals source dataset: `treasury_dts_deposits_withdrawals_operating_cash`.
- Treasury Fiscal Data Auctions Query source dataset: `treasury_od_auctions_query`.
- Derived Treasury Securities Net Issuance dataset: `treasury_securities_net_issuance`.
- Derived TGA Explorer dataset: `treasury_dts_deposits_withdrawals_operating_cash_explorer`.
- TGA Explorer published browser artifacts under `site/data/`.
- TGA Explorer static page UI under `site/pages/tga-explorer/`.
- Treasury Securities Net Issuance published browser artifacts under `site/data/`.
- Treasury Securities Net Issuance static page UI under `site/pages/treasury-securities-net-issuance/`.
- Aggregate static-site build command via `build-site`, including targeted source-update mode.
- GitHub Pages deployment workflow at `.github/workflows/pages.yml`.
- GitHub Actions data-cache persistence for `data/cache/` with explicit cold-build guardrail.
- Push-triggered cache-only GitHub Pages deployment via `build-site --from-cache`.
- Targeted source-update support via repeated `build-site --source-dataset ...` flags.
- Scheduled data refresh workflow at `.github/workflows/scheduled-refresh.yml`.

The TGA Explorer page UI checkpoint, Treasury Securities Net Issuance page UI checkpoint, initial GitHub Pages deployment checkpoint, Actions cache persistence checkpoint, push-triggered cache-only deployment checkpoint, targeted source-update checkpoint, and scheduled refresh workflow implementation checkpoint are complete. Live schedule validation remains next.

## Implemented Architecture

Current package files:

- `src/macro_observatory/models.py`: typed dataset, metadata, update-result, and source-adapter models.
- `src/macro_observatory/validation.py`: dataframe validation and normalization helpers.
- `src/macro_observatory/cache.py`: shared Parquet plus metadata JSON cache/update lifecycle.
- `src/macro_observatory/sources/fred.py`: FRED source adapter.
- `src/macro_observatory/sources/nyfed.py`: New York Fed reverse repo source adapter.
- `src/macro_observatory/sources/treasury.py`: Treasury Fiscal Data source adapters.
- `src/macro_observatory/derived.py`: derived builders for `treasury_tga`, `fed_net_liquidity`, TGA Explorer, and Treasury Securities Net Issuance.
- `src/macro_observatory/publish.py`: static artifact publisher for browser-facing data files.
- `src/macro_observatory/diagnostics.py`: cross-platform storage report for known cache, metadata, and site data files.
- `src/macro_observatory/registry.py`: dataset registry for source and derived datasets.
- `src/macro_observatory/data.py`: user-facing `load_dataset(...)` helper.
- `src/macro_observatory/server.py`: local static-site server helper for `serve-site`.
- `src/macro_observatory/site_build.py`: aggregate static-site build orchestration for deployment artifacts, including cache-only rebuild mode and targeted source-update mode.
- `src/macro_observatory/cli.py`: CLI commands for datasets, update, build-derived, publish, build-site, storage-report, serve-site, info, show, and export.

Current static-site files:

- `site/index.html`
- `site/pages/fed-net-liquidity/index.html`
- `site/pages/tga-explorer/index.html`
- `site/pages/treasury-securities-net-issuance/index.html`
- `site/assets/css/site.css`
- `site/assets/js/site.js`
- `site/assets/js/fed-net-liquidity.js`
- `site/assets/js/tga-explorer.js`
- `site/assets/js/treasury-securities-net-issuance.js`

Generated data under `data/cache/` and `site/data/` is ignored by git. Manual GitHub Pages deployment restores `data/cache/` from GitHub Actions cache, refreshes source data from APIs, regenerates derived and browser artifacts, saves a new data-cache snapshot after a successful build, and uploads `site/` as the Pages artifact. Push-triggered deployment restores the same cache, runs `build-site --from-cache`, uploads `site/`, and does not call source APIs or save a new data-cache snapshot. Scheduled refresh deployment restores the same cache, refuses cache misses, runs targeted source updates by refresh group, saves a new cache snapshot after success, and deploys `site/`.

Shared static behavior:

- `site/assets/js/site.js` provides `enableChartExpansion(...)` for in-app viewport-expanded chart mode.
- Current chart pages use a visible `Expand` button and an expanded-view `Restore` button.
- `Escape` also restores the chart on keyboard devices.
- The helper restores scroll position and calls `Plotly.Plots.resize(...)` after expand and restore.

## Tooling

The project uses `uv`.

Important project files:

- `pyproject.toml`
- `uv.lock`
- `.python-version`

Runtime dependencies currently include:

- `pandas`
- `pyarrow`
- `requests`

Development dependencies currently include:

- `pytest`
- `ruff`
- `mypy`
- `pandas-stubs`
- `types-requests`

If PowerShell auto-activates another environment such as `uv-general-3.14`, `uv run` may print a warning that the active `VIRTUAL_ENV` does not match `.venv`. That warning is normally harmless because uv ignores the unrelated active environment. Run `deactivate` first if a clean prompt is desired.

## Verified Commands

Setup:

```powershell
uv sync
```

List datasets:

```powershell
uv run macro-observatory datasets
```

Update source datasets:

```powershell
uv run macro-observatory update fred_walcl
uv run macro-observatory update fred_resppllopnww
uv run macro-observatory update nyfed_rrp
uv run macro-observatory update treasury_dts_operating_cash_balance
uv run macro-observatory update treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory update treasury_od_auctions_query
```

Build derived datasets:

```powershell
uv run macro-observatory build-derived treasury_tga
uv run macro-observatory build-derived fed_net_liquidity
uv run macro-observatory build-derived treasury_dts_deposits_withdrawals_operating_cash_explorer
uv run macro-observatory build-derived treasury_securities_net_issuance
```

Publish browser-facing artifacts:

```powershell
uv run macro-observatory publish fed_net_liquidity
uv run macro-observatory publish treasury_dts_deposits_withdrawals_operating_cash_explorer
uv run macro-observatory publish treasury_securities_net_issuance
```

Inspect data and storage:

```powershell
uv run macro-observatory storage-report
uv run macro-observatory info treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory info treasury_od_auctions_query
uv run macro-observatory info treasury_dts_deposits_withdrawals_operating_cash_explorer
uv run macro-observatory info treasury_securities_net_issuance
uv run macro-observatory show treasury_od_auctions_query --rows 10
uv run macro-observatory show treasury_dts_deposits_withdrawals_operating_cash_explorer --rows 10
uv run macro-observatory show treasury_securities_net_issuance --rows 10
```

Build all current static-site artifacts:

```powershell
uv run macro-observatory build-site
uv run macro-observatory build-site --require-fred-api-key
uv run macro-observatory build-site --from-cache
uv run macro-observatory build-site --source-dataset nyfed_rrp
uv run macro-observatory build-site --source-dataset treasury_dts_operating_cash_balance --source-dataset treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory build-site --source-dataset fred_walcl --source-dataset fred_resppllopnww --require-fred-api-key
```

Serve the static site locally:

```powershell
uv run macro-observatory serve-site
```

Run verification:

```powershell
uv run pytest
uv run ruff check .
uv run mypy .
node --check site/assets/js/site.js
node --check site/assets/js/fed-net-liquidity.js
node --check site/assets/js/tga-explorer.js
node --check site/assets/js/treasury-securities-net-issuance.js
```

## Current Data Checkpoints

### Fed Net Liquidity

Derived from:

```text
fred_walcl, fred_resppllopnww, nyfed_rrp, treasury_tga
```

Current formula:

```text
fed_net_liquidity = walcl - rrp - tga - rem
```

Transform policy:

- `walcl`, `rem`, and `tga` are converted from millions of dollars to dollars.
- `rrp` is already in dollars.
- Components are outer-merged by date, sorted, forward-filled, and then formula and diff columns are computed.

Current cache paths:

```text
data/cache/derived/fed_net_liquidity.parquet
data/cache/metadata/fed_net_liquidity.json
```

Published artifacts:

```text
site/data/fed-net-liquidity.json
site/data/fed-net-liquidity.csv
site/data/fed-net-liquidity-metadata.json
```

The JSON artifact uses record orientation. The current Fed Net Liquidity static page loads this artifact, renders the Plotly chart and recent-observations table, and supports shared viewport-expanded chart mode.

### Treasury Deposits And Withdrawals Operating Cash

Source endpoint:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash
```

Current dataset ID:

```text
treasury_dts_deposits_withdrawals_operating_cash
```

Current cache paths:

```text
data/cache/sources/treasury_dts_deposits_withdrawals_operating_cash.parquet
data/cache/metadata/treasury_dts_deposits_withdrawals_operating_cash.json
```

The source cache preserves the full endpoint columns for Pandas inspection and future page reuse. Transaction amounts are stored in Treasury's published units: millions of U.S. dollars.

Latest local metadata at this checkpoint:

```text
rows: 472,569
date range: 2005-10-03 to 2026-06-25
```

### Treasury Auctions Query

Source endpoint:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query
```

Current dataset ID:

```text
treasury_od_auctions_query
```

Current cache paths:

```text
data/cache/sources/treasury_od_auctions_query.parquet
data/cache/metadata/treasury_od_auctions_query.json
```

The source cache preserves the full 113-column endpoint for Pandas inspection and future Treasury securities pages. The checkpoint uses `record_date` for incremental updates, sorts by `record_date,cusip,auction_date,issue_date,maturity_date`, and uses that same tuple as the primary key. The current implementation parses `total_accepted` as U.S. dollars; additional numeric fields can be added when a derived page needs them.

Latest local metadata at this checkpoint:

```text
rows: 11,022
columns: 113
date range: 1979-11-15 to 2026-07-02
issue date range: 1979-11-15 to 2026-07-02
maturity date range: 1980-04-03 to 2056-05-15
duplicate primary keys: 0
total_accepted null rows: 4
source parquet: 1,958.3 KB
metadata JSON: 18.5 KB
```

An immediate second update fetched the 14-day overlap window and merged back to the same row count:

```text
rows before: 11,022
rows fetched: 21
rows after: 11,022
```

This source dataset is wired into aggregate `build-site` and GitHub Pages deployment so the Treasury Securities Net Issuance page can publish from cache. Scheduled auctions refresh is intentionally still a future checkpoint.

### Treasury Securities Net Issuance Derived Dataset

Derived from:

```text
treasury_od_auctions_query
```

Current dataset ID:

```text
treasury_securities_net_issuance
```

Current cache paths:

```text
data/cache/derived/treasury_securities_net_issuance.parquet
data/cache/metadata/treasury_securities_net_issuance.json
```

Current derived columns:

```text
frequency, date, security_type, issued, maturing, net_issuance
```

The derived cache matches the legacy Streamlit page's pandas semantics by normalizing security types, grouping issued amounts by `issue_date`, grouping maturing amounts by `maturity_date`, and precomputing `D`, `W`, `ME`, `QE`, and `YE` resampled rows. `W` uses pandas' default `W-SUN` boundary. `ME` values are summed at month end and then labeled with month-start dates to match the legacy page. Future maturities are intentionally preserved.

Latest local metadata at this checkpoint:

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

Non-zero `net_issuance` chart points by frequency:

```text
D      5,474
W      4,508
ME     1,666
QE       680
YE       181
```

Published artifacts:

```text
site/data/treasury-securities-net-issuance.json
site/data/treasury-securities-net-issuance.csv
site/data/treasury-securities-net-issuance-metadata.json
```

The Treasury Securities Net Issuance JSON artifact uses compact JSON `split` orientation and is currently about 4.0 MB. The page defaults to `ME`, filters by frequency and security type in JavaScript, sends only non-zero `net_issuance` points to Plotly, shows a visible `Today` marker, reports timing diagnostics, and supports shared viewport-expanded chart mode.

Static page:

```text
site/pages/treasury-securities-net-issuance/index.html
site/assets/js/treasury-securities-net-issuance.js
```

This derived dataset is wired into aggregate `build-site`, GitHub Pages deployment, and browser artifact publishing. Scheduled auctions refresh is intentionally still a future checkpoint.

### TGA Explorer Derived Dataset

Derived from:

```text
treasury_dts_deposits_withdrawals_operating_cash
```

Current dataset ID:

```text
treasury_dts_deposits_withdrawals_operating_cash_explorer
```

Current cache paths:

```text
data/cache/derived/treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet
data/cache/metadata/treasury_dts_deposits_withdrawals_operating_cash_explorer.json
```

Current derived columns:

```text
record_date, account_type, transaction_type, transaction_catg, src_line_nbr, transaction_today_amt, transaction_mtd_amt, transaction_fytd_amt
```

The derived cache keeps `src_line_nbr` for traceability, applies the baseline category exclusions from the legacy Streamlit TGA Explorer page, and records the sign policy in metadata. Amounts remain in Treasury's published sign; the browser page renders withdrawals as negative values.

Latest local metadata at this checkpoint:

```text
source rows: 472,569
derived rows: 453,385
date range: 2005-10-03 to 2026-06-25
```

Published artifacts:

```text
site/data/tga-explorer.json
site/data/tga-explorer.csv
site/data/tga-explorer-metadata.json
```

The TGA Explorer JSON artifact uses compact JSON `split` orientation:

```json
{"columns":[...],"data":[...]}
```

This was chosen after a local comparison showed row-record JSON would be about 85.9 MB, while split JSON is about 32.4 MB for the same reduced browser fields.

Published metadata includes:

- `json_orientation: split`
- `source_endpoint`
- `source_cache_file`
- `source_row_count`
- `category_count`
- `transaction_types`
- `metric_columns`
- `excluded_categories`
- `sign_policy`
- `render_guardrail: { max_rows: 10000 }`

Static page:

```text
site/pages/tga-explorer/index.html
site/assets/js/tga-explorer.js
```

The page lazy-loads `tga-explorer.json`, keeps the split payload in array form, provides the base legacy controls, renders a relative Plotly bar chart, enforces the metadata render guardrail, shows timing diagnostics for data fetch, JSON parse, filtering, trace preparation, and Plotly rendering, and supports shared viewport-expanded chart mode.

The legacy default `transaction_fytd_amt` minimum of `100000` currently filters to `10,606` rows, slightly above the `10,000` row guardrail. The static page therefore starts the FYTD minimum at `115000`, which filters the current artifact to `9,806` rows and `24` categories so the first load can render. Users can still enter `100000` manually to test the legacy threshold and guardrail behavior.

## Current Storage Snapshot

A live `uv run macro-observatory storage-report` after the Treasury Securities Net Issuance page checkpoint showed:

```text
source cache         6,140.5 KB
derived cache        4,522.6 KB
metadata                34.1 KB
site data           71,062.2 KB
overall             81,759.4 KB
```

Notable generated artifact sizes:

```text
data/cache/sources/treasury_dts_deposits_withdrawals_operating_cash.parquet           3,831.5 KB
data/cache/sources/treasury_od_auctions_query.parquet                                1,958.3 KB
data/cache/derived/treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet  3,502.6 KB
data/cache/derived/treasury_securities_net_issuance.parquet                            635.8 KB
site/data/tga-explorer.json                                                          32,359.0 KB
site/data/tga-explorer.csv                                                           29,275.6 KB
site/data/tga-explorer-metadata.json                                                      2.6 KB
site/data/treasury-securities-net-issuance.json                                       4,033.4 KB
site/data/treasury-securities-net-issuance.csv                                        3,351.7 KB
site/data/treasury-securities-net-issuance-metadata.json                                  2.7 KB
```

## Secrets

Source caches are ignored by git.

The FRED adapter uses `FRED_API_KEY` when present. For the current FRED datasets, it can fall back to FRED's public CSV endpoint when no key is configured.

The current New York Fed and Treasury Fiscal Data datasets do not require API keys.

Do not commit real API keys, personal contact information, or generated local cache files.

## Next Likely Checkpoint

The next likely checkpoints are verifying that the next push-triggered Pages deployment restores the refreshed cache without source API calls, watching the first live Monday RRP and Treasury scheduled runs from `.github/workflows/scheduled-refresh.yml`, and then adding a scheduled auctions refresh group after the preferred Treasury auctions update time is confirmed.

Manual cache validation completed on June 28, 2026. Bootstrap run `28315964925` cold-built once and saved the first cache in 132 seconds. Normal run `28316049169` restored that cache and completed `build-site` in 9 seconds.

Push-triggered cache-only validation completed on June 28, 2026. Push run `28316672934` restored cache key `macro-observatory-data-cache-v1-Linux-28316049169`, ran `build-site --from-cache`, updated `0` source datasets, completed the build in 8 seconds, skipped secret validation, skipped cache saving, deployed successfully, and returned HTTP 200 for the root page, both current dashboard pages, and sampled JSON data artifacts.

Deploy-on-push is re-enabled as a cache-only path. Push runs restore the existing Actions data cache, run `build-site --from-cache`, deploy `site/`, and skip source API updates and cache saving.

Targeted source-update mode is implemented. `build-site --source-dataset ...` validates the full current source cache first, updates only selected source datasets, rebuilds all derived and browser artifacts, and rejects `--from-cache` conflicts, derived dataset IDs, and unknown dataset IDs.

Local targeted validation completed on June 28, 2026. `uv run macro-observatory build-site --source-dataset nyfed_rrp` ran successfully, reported `source update mode: targeted`, selected `nyfed_rrp`, updated `1` source dataset, rebuilt `3` derived datasets, and published `2` browser artifacts. After the Treasury Securities page checkpoint, local `uv run macro-observatory build-site --from-cache` rebuilt `4` derived datasets and published `3` browser artifacts with `0` source updates.

Manual scheduled refresh validation completed on June 28, 2026. Workflow run `28318271888` dispatched `rrp_daily`, restored matched cache key `macro-observatory-data-cache-v1-Linux-28316049169`, selected `nyfed_rrp`, ran `build-site` in targeted mode, updated `1` source dataset, completed `build-site` in 9 seconds, saved new cache key `macro-observatory-data-cache-v1-Linux-28318271888`, deployed successfully, and returned HTTP 200 for the root page, both current dashboard pages, and sampled JSON data artifacts.

Scheduled refresh workflow implementation is now present. Manual `rrp_daily` dispatch validation completed successfully. Live Monday schedule validation is the next check.


## Known Open Questions

- The old README says `Fed Net Liquidity = WALCL - RRP - TGA`, while the old implementation computes `NL = WALCL - RRP - TGA - REM`. The current implementation intentionally reproduces the old code formula and records it in metadata, but the public label should still be reviewed.
- The final chart label for `RESPPLLOPNWW` should be reviewed if it remains the `REM` term.
- The first static page uses Plotly from a CDN; long-term vendoring or a frontend build system remains undecided.
- The TGA Explorer browser artifact is much larger than Fed Net Liquidity. The page now reports fetch, JSON parse, filtering, trace construction, and Plotly render timing, but those numbers still need browser testing on real machines.
- `10000` rows is the initial render guardrail for TGA Explorer. It should be tuned after browser testing.
- Future large-data research could evaluate Arrow, browser-readable Parquet, DuckDB-Wasm, compressed JSON, chunked artifacts, pre-aggregation, WebGL, or canvas renderers. See `docs/design/91-browser-data-formats.md`.
- Scheduled refresh workflow timing should be validated with live runs on the next market day. The workflow uses UTC cron entries with Pacific/Eastern comments; daylight-saving behavior should be reviewed after observing several weeks of runs.
- Treasury Securities Net Issuance now shows a visible `Today` marker. The remaining Treasury securities workflow gap is scheduled auctions refresh timing.
