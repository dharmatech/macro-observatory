# Macro Observatory Agent Notes

Macro Observatory is a Python/Pandas-first data pipeline and static-site experiment for macroeconomic and financial time-series data. The first deployment target is GitHub Pages, but core commands should stay platform-neutral so the same project can later run under GitHub Actions, cron on an Ubuntu server, Vercel, or another scheduler/host.

## Current Project Shape

- Repository: `macro-observatory`.
- Python package: `macro_observatory` under `src/`.
- CLI command: `macro-observatory`.
- Package/dependency workflow: `uv`.
- Python version target: Python 3.12 or newer.
- Current durable cache direction: Parquet data files plus JSON metadata.
- Current data directory: `data/`, ignored by git.
- Current first milestone: one Fed Net Liquidity vertical slice.

## Working Principles

- Keep backend/data work in Python unless there is a concrete reason not to.
- Use type hints generously, especially for public interfaces, specs, adapters, metadata, and update results.
- Keep the data layer Pandas-friendly. Users should be able to load maintained datasets by dataset ID without knowing internal cache paths.
- Treat every source API integration as a checkpoint. Fetch, cache, reload, incremental update, metadata, CLI inspection, and review should work before moving to the next API.
- Keep source adapters API-specific and keep the cache/update lifecycle shared where practical.
- Do not commit API keys, contact emails, secrets, generated local caches, exports, virtualenvs, or build artifacts.
- Do not modify the legacy Streamlit or helper repositories unless the user explicitly asks. They are reference implementations, not the target of this project.
- Keep GitHub Pages/GitHub Actions support as the first deployment path, but avoid hard-coding the core data pipeline to GitHub.

## Commands And Tooling

Prefer `uv` commands:

```powershell
uv sync
uv run macro-observatory datasets
uv run macro-observatory update fred_walcl
uv run macro-observatory update fred_resppllopnww
uv run macro-observatory update nyfed_rrp
uv run macro-observatory info nyfed_rrp
uv run macro-observatory show nyfed_rrp --rows 10
uv run pytest
uv run ruff check .
uv run mypy .
```

If another Python environment is active, `uv sync` may warn that `VIRTUAL_ENV` does not match `.venv`. For this project, the normal fix is to deactivate the unrelated environment and run `uv sync` again, not to use `uv sync --active`.

## Verification Expectations

Before committing implementation changes, run:

```powershell
uv run pytest
uv run ruff check .
uv run mypy .
```

Documentation-only changes do not necessarily require the full test suite, but `git diff` should still be reviewed.

## Current Checkpoint

The implemented source datasets are `fred_walcl`, `fred_resppllopnww`, and `nyfed_rrp`. They support update, metadata, preview, export, and Pandas loading through `load_dataset(...)`.

The next likely implementation checkpoint is `treasury_tga`. Treat it as a source dataset checkpoint only; do not freeze the final Fed Net Liquidity formula until the user reviews units, labels, and the existing formula mismatch.

## Open Design Questions

- Should canonical Fed Net Liquidity be `WALCL - RRP - TGA` or `WALCL - RRP - TGA - REM`?
- What display label should be used for `RESPPLLOPNWW` in the final chart if it remains the `REM` term?
- Which source units need conversion before combining WALCL, RRP, TGA, and REM?
- What browser-facing artifact format should the first static chart consume?
- Which generated artifacts, if any, should be committed versus produced by scheduled jobs?
