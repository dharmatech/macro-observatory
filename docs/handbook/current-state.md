# Current State

Status: draft

This document is a quick handoff for a fresh Macro Observatory session. It records what has been completed, what is implemented, what commands have been verified, and what the next checkpoint probably is.

## Completed So Far

The project has an initial design and the first Fed Net Liquidity data pipeline through the first static chart checkpoint.

Completed design docs:

- `docs/design/00-intro.md`
- `docs/design/01-fed-net-liquidity-milestone.md`
- `docs/design/02-data-layer-and-cache.md`
- `docs/design/03-static-site-interfaces.md`
- `docs/design/90-future-deployment-options.md`
- `docs/design/91-browser-data-formats.md`

Completed handbook docs:

- `docs/handbook/commands.md`
- `docs/handbook/current-state.md`

Completed implementation checkpoints:

- FRED `WALCL` as dataset ID `fred_walcl`.
- FRED `RESPPLLOPNWW` as dataset ID `fred_resppllopnww`.
- New York Fed RRP as dataset ID `nyfed_rrp`.
- Treasury Fiscal Data Operating Cash Balance as source dataset ID `treasury_dts_operating_cash_balance`.
- Derived Treasury General Account as dataset ID `treasury_tga`.
- Derived Fed Net Liquidity as dataset ID `fed_net_liquidity`.
- Published Fed Net Liquidity static artifacts under `site/data/`.
- Cross-platform storage diagnostics via `storage-report`.
- First multi-page static site shell and Fed Net Liquidity Plotly page under `site/pages/fed-net-liquidity/`.

## Implemented Architecture

Current package files:

- `src/macro_observatory/models.py`: typed dataset, metadata, update-result, and source-adapter models.
- `src/macro_observatory/validation.py`: dataframe validation and normalization helpers.
- `src/macro_observatory/cache.py`: shared Parquet plus metadata JSON cache/update lifecycle.
- `src/macro_observatory/sources/fred.py`: FRED source adapter.
- `src/macro_observatory/sources/nyfed.py`: New York Fed reverse repo source adapter.
- `src/macro_observatory/sources/treasury.py`: Treasury Fiscal Data source adapter.
- `src/macro_observatory/derived.py`: derived dataset builders for `treasury_tga` and `fed_net_liquidity`.
- `src/macro_observatory/diagnostics.py`: cross-platform storage report for known cache, metadata, and site data files.
- `src/macro_observatory/publish.py`: static artifact publisher for browser-facing data files.
- `src/macro_observatory/registry.py`: dataset registry for source and derived datasets.
- `src/macro_observatory/server.py`: local static-site server helper for `serve-site`.
- `src/macro_observatory/data.py`: user-facing `load_dataset(...)` helper.
- `src/macro_observatory/cli.py`: CLI commands for datasets, update, build-derived, publish, storage-report, serve-site, info, show, and export.

Current tests:

- `tests/test_cache.py`: verifies cache writing, metadata, overlap behavior, and deduplication preference for newer rows.
- `tests/test_diagnostics.py`: verifies known-file storage reporting, fixed KB formatting, missing-file reporting, totals, and CLI wiring.
- `tests/test_registry.py`: verifies registry entries and known-ID error messages.
- `tests/test_nyfed.py`: verifies New York Fed RRP fetch parameters, Small Value Exercise filtering, duplicate-date amount selection, and cold-cache start date.
- `tests/test_treasury.py`: verifies Treasury Fiscal Data pagination, date filtering, metadata capture, and cold-cache behavior.
- `tests/test_derived.py`: verifies derived TGA selection, Fed Net Liquidity unit conversion, forward-fill behavior, cache writing, and metadata.
- `tests/test_publish.py`: verifies published JSON, CSV, metadata, missing-cache errors, and deterministic repeated publishes.
- `tests/test_server.py`: verifies static-site directory validation, local URL display, and `serve-site` parser wiring.

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

## Verified Commands

The user successfully ran the initial handbook flow locally after deactivating an unrelated default Python environment.

Current setup command:

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
```

Build derived datasets:

```powershell
uv run macro-observatory build-derived treasury_tga
uv run macro-observatory build-derived fed_net_liquidity
```

Publish browser-facing artifacts:

```powershell
uv run macro-observatory publish fed_net_liquidity
```

Show storage diagnostics:

```powershell
uv run macro-observatory storage-report
```

Serve the static site locally:

```powershell
uv run macro-observatory serve-site
```

Inspect metadata:

```powershell
uv run macro-observatory info fred_walcl
uv run macro-observatory info fred_resppllopnww
uv run macro-observatory info nyfed_rrp
uv run macro-observatory info treasury_dts_operating_cash_balance
uv run macro-observatory info treasury_tga
uv run macro-observatory info fed_net_liquidity
```

Show recent rows:

```powershell
uv run macro-observatory show fred_walcl --rows 10
uv run macro-observatory show fred_resppllopnww --rows 10
uv run macro-observatory show nyfed_rrp --rows 10
uv run macro-observatory show treasury_dts_operating_cash_balance --rows 10
uv run macro-observatory show treasury_tga --rows 10
uv run macro-observatory show fed_net_liquidity --rows 10
```

Load in Pandas:

```powershell
uv run python
```

```python
from macro_observatory.data import load_dataset

df_walcl = load_dataset("fred_walcl")
df_resp = load_dataset("fred_resppllopnww")
df_rrp = load_dataset("nyfed_rrp")
df_treasury_ocb = load_dataset("treasury_dts_operating_cash_balance")
df_tga = load_dataset("treasury_tga")
df_net_liquidity = load_dataset("fed_net_liquidity")
```

Verification commands that passed after the first static-site checkpoint:

```powershell
uv run pytest
uv run ruff check .
uv run mypy .
node --check site/assets/js/site.js
node --check site/assets/js/fed-net-liquidity.js
```

Local HTTP preview checks also passed with `uv run macro-observatory serve-site` running on `http://localhost:8123/` because port `8000` was already occupied:

```text
http://localhost:8123/
http://localhost:8123/pages/fed-net-liquidity/
http://localhost:8123/data/fed-net-liquidity-metadata.json
```

## Current Data Checkpoints

### `fred_walcl`

Source:

```text
FRED series WALCL
```

Current registry label:

```text
Federal Reserve Balance Sheet Assets (WALCL)
```

Current units metadata:

```text
millions of U.S. dollars
```

Current cache paths:

```text
data/cache/sources/fred_walcl.parquet
data/cache/metadata/fred_walcl.json
```

### `fred_resppllopnww`

Source:

```text
FRED series RESPPLLOPNWW
```

Official FRED title verified during the checkpoint:

```text
Liabilities and Capital: Liabilities: Earnings Remittances Due to the U.S. Treasury: Wednesday Level
```

Current registry label:

```text
Earnings Remittances Due to the U.S. Treasury (RESPPLLOPNWW)
```

Current units metadata:

```text
millions of U.S. dollars
```

Current cache paths:

```text
data/cache/sources/fred_resppllopnww.parquet
data/cache/metadata/fred_resppllopnww.json
```

First live update fetched 1,228 rows with date range `2002-12-18` to `2026-06-24`. A second live update fetched 3 overlap rows and preserved 1,228 rows after deduplication.

### `nyfed_rrp`

Source:

```text
New York Fed Markets API reverse repo propositions search endpoint
```

Official endpoint used:

```text
https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json
```

Official OpenAPI documentation was checked before implementation:

```text
https://markets.newyorkfed.org/static/docs/markets-api.html
```

The documentation page referenced an OpenAPI spec last updated `June 12, 2026`.

Current registry label:

```text
New York Fed Reverse Repo Operations (RRP)
```

Current units metadata:

```text
U.S. dollars
```

Current cache paths:

```text
data/cache/sources/nyfed_rrp.parquet
data/cache/metadata/nyfed_rrp.json
```

The cached dataset is flat and operation-level with columns:

```text
operationDate, totalAmtAccepted, operationId, operationType, note
```

The adapter filters Small Value Exercise rows and defensively keeps the highest `totalAmtAccepted` when multiple rows share an `operationDate`.

First live update fetched 3,300 rows with date range `2003-02-07` to `2026-06-26`. A second live update fetched 10 overlap rows and preserved 3,300 rows after deduplication.

### `treasury_dts_operating_cash_balance`

Source:

```text
Treasury Fiscal Data Daily Treasury Statement Operating Cash Balance endpoint
```

Official endpoint used:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance
```

Official documentation entry checked before implementation:

```text
https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/operating-cash-balance
```

Current registry label:

```text
Treasury Daily Treasury Statement Operating Cash Balance
```

Current units metadata:

```text
millions of U.S. dollars
```

Current cache paths:

```text
data/cache/sources/treasury_dts_operating_cash_balance.parquet
data/cache/metadata/treasury_dts_operating_cash_balance.json
```

The source cache preserves the full endpoint fields rather than filtering only for TGA. A live update preserved 16,386 rows with date range `2005-10-03` to `2026-06-25`.

### `treasury_tga`

Derived from:

```text
treasury_dts_operating_cash_balance
```

Current registry label:

```text
Treasury General Account (TGA)
```

Current units metadata:

```text
millions of U.S. dollars
```

Current cache paths:

```text
data/cache/derived/treasury_tga.parquet
data/cache/metadata/treasury_tga.json
```

Current derived columns:

```text
date, tga, source_account_type, source_balance_field
```

Selection rules preserve the legacy account transitions:

```text
Federal Reserve Account -> close_today_bal
Treasury General Account (TGA) -> close_today_bal
Treasury General Account (TGA) Closing Balance -> open_today_bal
```

A live build produced 5,206 rows with date range `2005-10-03` to `2026-06-25`.

### `fed_net_liquidity`

Derived from:

```text
fred_walcl, fred_resppllopnww, nyfed_rrp, treasury_tga
```

Current registry label:

```text
Fed Net Liquidity
```

Current units metadata:

```text
U.S. dollars
```

Current cache paths:

```text
data/cache/derived/fed_net_liquidity.parquet
data/cache/metadata/fed_net_liquidity.json
```

Current derived columns:

```text
date, walcl, rrp, tga, rem, fed_net_liquidity, walcl_diff, rrp_diff, tga_diff, rem_diff, fed_net_liquidity_diff
```

Current formula:

```text
fed_net_liquidity = walcl - rrp - tga - rem
```

Current transform policy:

- `walcl`, `rem`, and `tga` are converted from millions of dollars to dollars.
- `rrp` is already in dollars.
- Components are outer-merged by date, sorted by date, forward-filled, and then formula and diff columns are computed.

A live build produced 5,374 rows with date range `2002-12-18` to `2026-06-26`.

Published artifacts are generated from this derived cache and written to:

```text
site/data/fed-net-liquidity.json
site/data/fed-net-liquidity.csv
site/data/fed-net-liquidity-metadata.json
```

The JSON artifact is a records array with `YYYY-MM-DD` date strings and JSON `null` for missing values. The metadata artifact includes formula, units, source dataset IDs, source row counts, date range, dataset build timestamp, artifact filenames, and chart-series labels. It omits local cache paths and secrets. `site/data/` is ignored by git.

A live publish wrote 5,374 JSON records and 5,374 CSV rows with date range `2002-12-18` to `2026-06-26`. Local artifact sizes were about 1.38 MB for JSON, 700 KB for CSV, and 2 KB for metadata.

The first static site shell is implemented with tracked source files:

```text
site/index.html
site/pages/fed-net-liquidity/index.html
site/assets/css/site.css
site/assets/js/site.js
site/assets/js/fed-net-liquidity.js
```

The root page is a minimal dashboard directory. The Fed Net Liquidity page loads the generated JSON and metadata artifacts with relative paths, renders a Plotly time-series chart, displays summary metrics, shows source metadata, and includes a recent-observations table.

The recent-observations table uses fixed per-column units for scanability: Fed Net Liquidity and WALCL in trillions, and change, RRP, TGA, and REM in billions.

Local preview command:

```powershell
uv run macro-observatory serve-site
```

The `storage-report` command reports known source caches, derived caches, metadata files, and published site artifacts with fixed-width `KB` size columns, local modified timestamps, group totals, and explicit missing-file rows. It supports `--data-dir` and `--site-dir` for scratch directories.

A live storage report after this checkpoint showed these totals:

```text
source cache        350.8 KB
derived cache       384.2 KB
metadata              7.6 KB
site data         2,037.2 KB
overall           2,779.8 KB
```

Legacy comparison against the old pickle-backed formula matched exactly for 4,833 overlapping rows through `2024-05-01`, the date where all old component source pickles still had complete coverage. Tail differences after that were due to the old pickles forward-filling stale component values while the current source caches have newer values.

## Secrets

Source caches are ignored by git.

The FRED adapter uses `FRED_API_KEY` when present. For the current FRED datasets, it can fall back to FRED's public CSV endpoint when no key is configured.

The current New York Fed and Treasury Fiscal Data datasets do not require API keys.

Do not commit real API keys, personal contact information, or generated local cache files.

## Next Likely Checkpoint

The next likely checkpoint is either GitHub Pages deployment automation or a review/polish pass on the first static Fed Net Liquidity page after manual browser inspection.

Recommended next-step scope:

- Confirm the desired GitHub Pages source and path structure.
- Add a GitHub Actions workflow that can refresh source data, build derived data, publish artifacts, and deploy the static site.
- Decide whether generated `site/data/` artifacts should be committed, deployed as action artifacts, or maintained on a deployment branch.
- Keep the root page and dashboard-page structure compatible with future pages such as TGA Explorer, tax data, and Treasury securities views.
- Revisit Plotly CDN pinning or vendoring if reproducibility or offline local preview becomes important.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy .` after the next checkpoint.

## Known Open Questions

- The old README says `Fed Net Liquidity = WALCL - RRP - TGA`.
- The old implementation computes `NL = WALCL - RRP - TGA - REM`.
- The current implementation intentionally reproduces the old code formula and records it in metadata, but the canonical formula still deserves an explicit review before public labeling is finalized.
- The final chart label for `RESPPLLOPNWW` should be reviewed if it remains the `REM` term.
- The first static page uses Plotly from a CDN; long-term vendoring or a frontend build system remains undecided.
- GitHub Actions deployment/update workflows are not implemented yet.

## Future Deployment Notes

GitHub Pages is the first target. The core data commands should stay platform-neutral so the same pipeline can later be called by other schedulers or hosts.

A future paid managed instance on Vercel or another host is possible, but it is not in the current implementation scope. If that is explored later, the paid layer should be framed as hosted convenience and reliability around an open-source project, not as closed access to the public source code. See `docs/design/90-future-deployment-options.md` for the current future-facing deployment note.

A future browser data-format checkpoint could evaluate Apache Arrow, browser-readable Parquet, DuckDB-Wasm, and compressed JSON against the current JSON/CSV baseline. See `docs/design/91-browser-data-formats.md`. This should not block the first static chart milestone.
