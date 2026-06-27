# Current State

Status: draft

This document is a quick handoff for a fresh Macro Observatory session. It records what has been completed, what is implemented, what commands have been verified, and what the next checkpoint probably is.

## Completed So Far

The project has an initial design and one implemented data checkpoint.

Completed design docs:

- `docs/design/00-intro.md`
- `docs/design/01-fed-net-liquidity-milestone.md`
- `docs/design/02-data-layer-and-cache.md`
- `docs/design/90-future-deployment-options.md`

Completed handbook docs:

- `docs/handbook/commands.md`
- `docs/handbook/current-state.md`

Completed implementation checkpoint:

- FRED `WALCL` as dataset ID `fred_walcl`.

## Implemented Architecture

Current package files:

- `src/macro_observatory/models.py`: typed dataset, metadata, update-result, and source-adapter models.
- `src/macro_observatory/validation.py`: dataframe validation and normalization helpers.
- `src/macro_observatory/cache.py`: shared Parquet plus metadata JSON cache/update lifecycle.
- `src/macro_observatory/sources/fred.py`: FRED source adapter.
- `src/macro_observatory/registry.py`: dataset registry, currently containing `fred_walcl`.
- `src/macro_observatory/data.py`: user-facing `load_dataset(...)` helper.
- `src/macro_observatory/cli.py`: CLI commands for datasets, update, info, show, and export.

Current tests:

- `tests/test_cache.py`: verifies cache writing, metadata, overlap behavior, and deduplication preference for newer rows.

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

The user successfully ran the handbook flow locally after deactivating an unrelated default Python environment.

Setup:

```powershell
uv sync
```

List datasets:

```powershell
uv run macro-observatory datasets
```

Update WALCL:

```powershell
uv run macro-observatory update fred_walcl
```

Inspect WALCL metadata:

```powershell
uv run macro-observatory info fred_walcl
```

Show recent WALCL rows:

```powershell
uv run macro-observatory show fred_walcl --rows 10
```

Load in Pandas:

```powershell
uv run python
```

```python
from macro_observatory.data import load_dataset

df = load_dataset("fred_walcl")
df.tail()
```

Verification commands that passed at the first implementation checkpoint:

```powershell
uv run pytest
uv run ruff check .
uv run mypy .
```

## Current Data Checkpoint

Dataset ID:

```text
fred_walcl
```

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

These cache files are ignored by git.

The FRED adapter uses `FRED_API_KEY` when present. For `fred_walcl`, it can fall back to FRED's public CSV endpoint when no key is configured.

## Next Likely Checkpoint

The next likely source dataset is:

```text
fred_resppllopnww
```

This should use the same FRED adapter with series ID:

```text
RESPPLLOPNWW
```

Recommended next-step scope:

- Add a registry entry for `fred_resppllopnww`.
- Verify official FRED title and units before locking the display label.
- Run a live update.
- Verify `datasets`, `update`, `info`, `show`, and Pandas loading.
- Add handbook commands for the new dataset.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy .`.
- Commit and push after the checkpoint is complete.

Do not decide the canonical Fed Net Liquidity formula as part of this source checkpoint. Treat `RESPPLLOPNWW` as a source dataset until the formula, units, and label have been reviewed.

## Known Open Questions

- The old README says `Fed Net Liquidity = WALCL - RRP - TGA`.
- The old implementation computes `NL = WALCL - RRP - TGA - REM`.
- The old implementation multiplies `WALCL`, `TGA`, and `REM` by `1_000_000`, but does not multiply RRP.
- The exact economic label for `RESPPLLOPNWW` should be verified.
- New York Fed RRP filtering and duplicate-date handling should be reviewed against the legacy code.
- Treasury TGA account selection and balance-column logic should be reviewed against the legacy code.
- Browser-facing published artifact formats are not implemented yet.
- GitHub Actions deployment/update workflows are not implemented yet.

## Future Deployment Notes

GitHub Pages is the first target. The core data commands should stay platform-neutral so the same pipeline can later be called by other schedulers or hosts.

A future paid managed instance on Vercel or another host is possible, but it is not in the current implementation scope. If that is explored later, the paid layer should be framed as hosted convenience and reliability around an open-source project, not as closed access to the public source code. See `docs/design/90-future-deployment-options.md` for the current future-facing design note.

