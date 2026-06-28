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
- Derived TGA Explorer dataset: `treasury_dts_deposits_withdrawals_operating_cash_explorer`.
- TGA Explorer published browser artifacts under `site/data/`.
- TGA Explorer static page UI under `site/pages/tga-explorer/`.

The TGA Explorer data artifact checkpoint and first page UI checkpoint are complete.

## Implemented Architecture

Current package files:

- `src/macro_observatory/models.py`: typed dataset, metadata, update-result, and source-adapter models.
- `src/macro_observatory/validation.py`: dataframe validation and normalization helpers.
- `src/macro_observatory/cache.py`: shared Parquet plus metadata JSON cache/update lifecycle.
- `src/macro_observatory/sources/fred.py`: FRED source adapter.
- `src/macro_observatory/sources/nyfed.py`: New York Fed reverse repo source adapter.
- `src/macro_observatory/sources/treasury.py`: Treasury Fiscal Data source adapters.
- `src/macro_observatory/derived.py`: derived builders for `treasury_tga`, `fed_net_liquidity`, and TGA Explorer.
- `src/macro_observatory/publish.py`: static artifact publisher for browser-facing data files.
- `src/macro_observatory/diagnostics.py`: cross-platform storage report for known cache, metadata, and site data files.
- `src/macro_observatory/registry.py`: dataset registry for source and derived datasets.
- `src/macro_observatory/data.py`: user-facing `load_dataset(...)` helper.
- `src/macro_observatory/server.py`: local static-site server helper for `serve-site`.
- `src/macro_observatory/cli.py`: CLI commands for datasets, update, build-derived, publish, storage-report, serve-site, info, show, and export.

Current static-site files:

- `site/index.html`
- `site/pages/fed-net-liquidity/index.html`
- `site/pages/tga-explorer/index.html`
- `site/assets/css/site.css`
- `site/assets/js/site.js`
- `site/assets/js/fed-net-liquidity.js`
- `site/assets/js/tga-explorer.js`

Generated data under `data/cache/` and `site/data/` is ignored by git.

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
```

Build derived datasets:

```powershell
uv run macro-observatory build-derived treasury_tga
uv run macro-observatory build-derived fed_net_liquidity
uv run macro-observatory build-derived treasury_dts_deposits_withdrawals_operating_cash_explorer
```

Publish browser-facing artifacts:

```powershell
uv run macro-observatory publish fed_net_liquidity
uv run macro-observatory publish treasury_dts_deposits_withdrawals_operating_cash_explorer
```

Inspect data and storage:

```powershell
uv run macro-observatory storage-report
uv run macro-observatory info treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory info treasury_dts_deposits_withdrawals_operating_cash_explorer
uv run macro-observatory show treasury_dts_deposits_withdrawals_operating_cash_explorer --rows 10
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

A live `uv run macro-observatory storage-report` after the TGA Explorer data artifact checkpoint showed:

```text
source cache         4,182.2 KB
derived cache        3,886.8 KB
metadata                13.4 KB
site data           63,674.4 KB
overall             71,756.9 KB
```

Notable generated artifact sizes:

```text
data/cache/sources/treasury_dts_deposits_withdrawals_operating_cash.parquet           3,831.5 KB
data/cache/derived/treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet  3,502.6 KB
site/data/tga-explorer.json                                                          32,359.0 KB
site/data/tga-explorer.csv                                                           29,275.6 KB
site/data/tga-explorer-metadata.json                                                      2.6 KB
```

## Secrets

Source caches are ignored by git.

The FRED adapter uses `FRED_API_KEY` when present. For the current FRED datasets, it can fall back to FRED's public CSV endpoint when no key is configured.

The current New York Fed and Treasury Fiscal Data datasets do not require API keys.

Do not commit real API keys, personal contact information, or generated local cache files.

## Next Likely Checkpoint

The next likely checkpoint is manual browser inspection of the TGA Explorer page, followed by GitHub Pages deployment automation if the page behavior is acceptable.

Recommended manual checks:

- Load `http://localhost:8000/pages/tga-explorer/` with `uv run macro-observatory serve-site` running.
- Record the diagnostics line after first render.
- Try the legacy FYTD minimum `100000` and confirm the guardrail refuses to render over `10,000` rows.
- Try narrower category filters and confirm chart updates remain responsive.
- Verify the existing Fed Net Liquidity page still behaves normally.
- Try `Expand`, `Restore`, and `Escape` on both current chart pages.

After manual inspection, GitHub Pages deployment and GitHub Actions refresh workflows are still open.

## Known Open Questions

- The old README says `Fed Net Liquidity = WALCL - RRP - TGA`, while the old implementation computes `NL = WALCL - RRP - TGA - REM`. The current implementation intentionally reproduces the old code formula and records it in metadata, but the public label should still be reviewed.
- The final chart label for `RESPPLLOPNWW` should be reviewed if it remains the `REM` term.
- The first static page uses Plotly from a CDN; long-term vendoring or a frontend build system remains undecided.
- The TGA Explorer browser artifact is much larger than Fed Net Liquidity. The page now reports fetch, JSON parse, filtering, trace construction, and Plotly render timing, but those numbers still need browser testing on real machines.
- `10000` rows is the initial render guardrail for TGA Explorer. It should be tuned after browser testing.
- Future large-data research could evaluate Arrow, browser-readable Parquet, DuckDB-Wasm, compressed JSON, chunked artifacts, pre-aggregation, WebGL, or canvas renderers. See `docs/design/91-browser-data-formats.md`.
- GitHub Actions deployment/update workflows are not implemented yet.
