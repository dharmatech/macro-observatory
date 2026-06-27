# Current State

Status: draft

This document is a quick handoff for a fresh Macro Observatory session. It records what has been completed, what is implemented, what commands have been verified, and what the next checkpoint probably is.

## Completed So Far

The project has an initial design and three implemented source-data checkpoints.

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

## Implemented Architecture

Current package files:

- `src/macro_observatory/models.py`: typed dataset, metadata, update-result, and source-adapter models.
- `src/macro_observatory/validation.py`: dataframe validation and normalization helpers.
- `src/macro_observatory/cache.py`: shared Parquet plus metadata JSON cache/update lifecycle.
- `src/macro_observatory/sources/fred.py`: FRED source adapter.
- `src/macro_observatory/sources/nyfed.py`: New York Fed reverse repo source adapter.
- `src/macro_observatory/registry.py`: dataset registry, currently containing `fred_walcl`, `fred_resppllopnww`, and `nyfed_rrp`.
- `src/macro_observatory/data.py`: user-facing `load_dataset(...)` helper.
- `src/macro_observatory/cli.py`: CLI commands for datasets, update, info, show, and export.

Current tests:

- `tests/test_cache.py`: verifies cache writing, metadata, overlap behavior, and deduplication preference for newer rows.
- `tests/test_registry.py`: verifies the initial source registry entries and known-ID error message.
- `tests/test_nyfed.py`: verifies New York Fed RRP fetch parameters, Small Value Exercise filtering, duplicate-date amount selection, and cold-cache start date.

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

The user successfully ran the initial WALCL handbook flow locally after deactivating an unrelated default Python environment.

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
```

Inspect metadata:

```powershell
uv run macro-observatory info fred_walcl
uv run macro-observatory info fred_resppllopnww
uv run macro-observatory info nyfed_rrp
```

Show recent rows:

```powershell
uv run macro-observatory show fred_walcl --rows 10
uv run macro-observatory show fred_resppllopnww --rows 10
uv run macro-observatory show nyfed_rrp --rows 10
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
```

Verification commands that passed after the `nyfed_rrp` checkpoint:

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

Source caches are ignored by git.

The FRED adapter uses `FRED_API_KEY` when present. For the current FRED datasets, it can fall back to FRED's public CSV endpoint when no key is configured. The New York Fed RRP dataset does not require an API key.

## Next Likely Checkpoint

The next likely source dataset is:

```text
treasury_tga
```

Recommended next-step scope:

- Review the legacy Treasury TGA logic.
- Identify the current Treasury Fiscal Data endpoint and response schema.
- Add a Treasury Fiscal Data source adapter.
- Add a registry entry for `treasury_tga`.
- Run a live update.
- Verify `datasets`, `update`, `info`, `show`, and Pandas loading.
- Add handbook commands for the new dataset.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy .`.
- Commit and push after the checkpoint is complete.

Do not decide the canonical Fed Net Liquidity formula as part of the next source checkpoint. Treat TGA as a source dataset until the formula, units, and merge behavior have been reviewed.

## Known Open Questions

- The old README says `Fed Net Liquidity = WALCL - RRP - TGA`.
- The old implementation computes `NL = WALCL - RRP - TGA - REM`.
- The old implementation multiplies `WALCL`, `TGA`, and `REM` by `1_000_000`, but does not multiply RRP.
- The final chart label for `RESPPLLOPNWW` should be reviewed if it remains the `REM` term.
- Treasury TGA account selection and balance-column logic should be reviewed against the legacy code.
- Browser-facing published artifact formats are not implemented yet.
- GitHub Actions deployment/update workflows are not implemented yet.

## Future Deployment Notes

GitHub Pages is the first target. The core data commands should stay platform-neutral so the same pipeline can later be called by other schedulers or hosts.

A future paid managed instance on Vercel or another host is possible, but it is not in the current implementation scope. If that is explored later, the paid layer should be framed as hosted convenience and reliability around an open-source project, not as closed access to the public source code. See `docs/design/90-future-deployment-options.md` for the current future-facing design note.
