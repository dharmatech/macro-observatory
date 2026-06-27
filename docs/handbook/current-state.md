# Current State

Status: draft

This document is a quick handoff for a fresh Macro Observatory session. It records what has been completed, what is implemented, what commands have been verified, and what the next checkpoint probably is.

## Completed So Far

The project has an initial design and the first Fed Net Liquidity data pipeline through the derived dataframe checkpoint.

Completed design docs:

- `docs/design/00-intro.md`
- `docs/design/01-fed-net-liquidity-milestone.md`
- `docs/design/02-data-layer-and-cache.md`
- `docs/design/90-future-deployment-options.md`

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

## Implemented Architecture

Current package files:

- `src/macro_observatory/models.py`: typed dataset, metadata, update-result, and source-adapter models.
- `src/macro_observatory/validation.py`: dataframe validation and normalization helpers.
- `src/macro_observatory/cache.py`: shared Parquet plus metadata JSON cache/update lifecycle.
- `src/macro_observatory/sources/fred.py`: FRED source adapter.
- `src/macro_observatory/sources/nyfed.py`: New York Fed reverse repo source adapter.
- `src/macro_observatory/sources/treasury.py`: Treasury Fiscal Data source adapter.
- `src/macro_observatory/derived.py`: derived dataset builders for `treasury_tga` and `fed_net_liquidity`.
- `src/macro_observatory/registry.py`: dataset registry for source and derived datasets.
- `src/macro_observatory/data.py`: user-facing `load_dataset(...)` helper.
- `src/macro_observatory/cli.py`: CLI commands for datasets, update, build-derived, info, show, and export.

Current tests:

- `tests/test_cache.py`: verifies cache writing, metadata, overlap behavior, and deduplication preference for newer rows.
- `tests/test_registry.py`: verifies registry entries and known-ID error messages.
- `tests/test_nyfed.py`: verifies New York Fed RRP fetch parameters, Small Value Exercise filtering, duplicate-date amount selection, and cold-cache start date.
- `tests/test_treasury.py`: verifies Treasury Fiscal Data pagination, date filtering, metadata capture, and cold-cache behavior.
- `tests/test_derived.py`: verifies derived TGA selection, Fed Net Liquidity unit conversion, forward-fill behavior, cache writing, and metadata.

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

Verification commands that passed after the `fed_net_liquidity` checkpoint:

```powershell
uv run pytest
uv run ruff check .
uv run mypy .
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

Legacy comparison against the old pickle-backed formula matched exactly for 4,833 overlapping rows through `2024-05-01`, the date where all old component source pickles still had complete coverage. Tail differences after that were due to the old pickles forward-filling stale component values while the current source caches have newer values.

## Secrets

Source caches are ignored by git.

The FRED adapter uses `FRED_API_KEY` when present. For the current FRED datasets, it can fall back to FRED's public CSV endpoint when no key is configured.

The current New York Fed and Treasury Fiscal Data datasets do not require API keys.

Do not commit real API keys, personal contact information, or generated local cache files.

## Next Likely Checkpoint

The next likely checkpoint is browser-facing published static data artifacts for `fed_net_liquidity`.

Recommended next-step scope:

- Decide the first published artifact shape for the chart.
- Generate compact JSON and CSV from the `fed_net_liquidity` derived cache.
- Include enough metadata for formula, units, row count, date range, source dataset IDs, and build timestamp.
- Keep the artifact presentation-neutral enough that Plotly.js is not the only possible frontend.
- Add handbook commands for publishing artifacts.
- Verify artifacts can be read without loading the raw source caches.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy .`.
- Commit and push after the checkpoint is complete.

After that, the next checkpoint should be the first static chart and simple data-grid presentation.

## Known Open Questions

- The old README says `Fed Net Liquidity = WALCL - RRP - TGA`.
- The old implementation computes `NL = WALCL - RRP - TGA - REM`.
- The current implementation intentionally reproduces the old code formula and records it in metadata, but the canonical formula still deserves an explicit review before public labeling is finalized.
- The final chart label for `RESPPLLOPNWW` should be reviewed if it remains the `REM` term.
- Browser-facing published artifact formats are not implemented yet.
- The first chart and data-grid presentation are not implemented yet.
- GitHub Actions deployment/update workflows are not implemented yet.

## Future Deployment Notes

GitHub Pages is the first target. The core data commands should stay platform-neutral so the same pipeline can later be called by other schedulers or hosts.

A future paid managed instance on Vercel or another host is possible, but it is not in the current implementation scope. If that is explored later, the paid layer should be framed as hosted convenience and reliability around an open-source project, not as closed access to the public source code. See `docs/design/90-future-deployment-options.md` for the current future-facing design note.
