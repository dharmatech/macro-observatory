# Command Handbook

Status: draft

This handbook collects practical commands for working with Macro Observatory locally. Commands should be runnable by anyone who clones the repository and has `uv` installed.

## First-Time Setup

From the repository root:

```powershell
uv sync
```

This creates or updates the local `.venv` from `pyproject.toml` and `uv.lock`.

## Optional Secrets

The FRED adapter uses `FRED_API_KEY` when it is available. For the current `fred_walcl` dataset, the adapter can also fall back to FRED's public CSV endpoint when no key is configured.

For a temporary PowerShell session:

```powershell
$env:FRED_API_KEY = "your-fred-api-key"
```

For a temporary Bash session:

```bash
export FRED_API_KEY="your-fred-api-key"
```

Do not commit real API keys or personal contact information.

## List Datasets

```powershell
uv run macro-observatory datasets
```

Current expected output includes:

```text
fred_walcl    Federal Reserve Balance Sheet Assets (WALCL)
```

## Update FRED WALCL

Run an incremental update for the local WALCL cache:

```powershell
uv run macro-observatory update fred_walcl
```

The first run downloads the full available series. Later runs use the local cache, request an overlap window, merge rows, deduplicate by date, and rewrite the local cache and metadata.

Current local cache paths:

```text
data/cache/sources/fred_walcl.parquet
data/cache/metadata/fred_walcl.json
```

These cache files are ignored by git.

## Inspect WALCL Metadata

```powershell
uv run macro-observatory info fred_walcl
```

This prints the row count, date range, cache path, columns, and units recorded in metadata.

## Show Recent WALCL Rows

```powershell
uv run macro-observatory show fred_walcl --rows 10
```

Use a different row count as needed:

```powershell
uv run macro-observatory show fred_walcl --rows 25
```

## Export WALCL

Export to CSV:

```powershell
uv run macro-observatory export fred_walcl --format csv --output exports/fred_walcl.csv
```

Export to Parquet:

```powershell
uv run macro-observatory export fred_walcl --format parquet --output exports/fred_walcl.parquet
```

The `exports/` directory is not special yet; it is just a convenient local output path.

## Load WALCL In Pandas

Start a Python REPL inside the uv environment:

```powershell
uv run python
```

Then load the dataset by ID:

```python
from macro_observatory.data import load_dataset

df = load_dataset("fred_walcl")
df.tail()
```

The normal user-facing API should use dataset IDs rather than requiring users to know cache file paths.

## Use A Different Data Directory

Most commands default to `data/`. To test with a separate cache directory, use `--data-dir` before the subcommand:

```powershell
uv run macro-observatory --data-dir scratch-data update fred_walcl
uv run macro-observatory --data-dir scratch-data info fred_walcl
uv run macro-observatory --data-dir scratch-data show fred_walcl --rows 5
```
