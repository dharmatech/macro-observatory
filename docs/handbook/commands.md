# Command Handbook

Status: draft

This handbook collects practical commands for working with Macro Observatory locally. Commands should be runnable by anyone who clones the repository and has `uv` installed.

## First-Time Setup

From the repository root:

```powershell
uv sync
```

This creates or updates the local `.venv` from `pyproject.toml` and `uv.lock`.

## Active Environment Warning

If your PowerShell profile automatically activates another Python environment, your prompt may look like this before you run project commands:

```powershell
(uv-general-3.14) PS C:\Users\dharm\src\macro-observatory>
```

In that case, `uv sync` may print a warning like:

```text
warning: `VIRTUAL_ENV=...` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

For this project, that warning is usually harmless. It means uv noticed the unrelated active environment and ignored it so it can use Macro Observatory's project-local `.venv`.

To silence the warning for the current shell, deactivate the unrelated environment before running project commands:

```powershell
deactivate
uv sync
```

Do not use `uv sync --active` unless you intentionally want uv to install this project's dependencies into the already-active environment instead of the project `.venv`.

## Optional Secrets

The FRED adapter uses `FRED_API_KEY` when it is available. For the current FRED datasets, the adapter can also fall back to FRED's public CSV endpoint when no key is configured.

The current New York Fed RRP dataset does not require an API key.

The current Treasury Fiscal Data Operating Cash Balance dataset does not require an API key.

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
fred_walcl                           Federal Reserve Balance Sheet Assets (WALCL)
fred_resppllopnww                    Earnings Remittances Due to the U.S. Treasury (RESPPLLOPNWW)
nyfed_rrp                            New York Fed Reverse Repo Operations (RRP)
treasury_dts_operating_cash_balance  Treasury Daily Treasury Statement Operating Cash Balance
treasury_tga                         Treasury General Account (TGA)
fed_net_liquidity                    Fed Net Liquidity
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

## Update FRED RESPPLLOPNWW

Run an incremental update for the local earnings-remittances cache:

```powershell
uv run macro-observatory update fred_resppllopnww
```

This dataset is the FRED `RESPPLLOPNWW` series. The existing legacy code uses this series as the candidate `REM` term, but the final Fed Net Liquidity formula remains an explicit checkpoint.

Current local cache paths:

```text
data/cache/sources/fred_resppllopnww.parquet
data/cache/metadata/fred_resppllopnww.json
```

These cache files are ignored by git.

## Update New York Fed RRP

Run an incremental update for the local New York Fed reverse repo cache:

```powershell
uv run macro-observatory update nyfed_rrp
```

This dataset uses the documented New York Fed Markets API endpoint:

```text
https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json
```

The cached source dataset is flat and operation-level. It keeps the regular daily reverse repo operation, filters Small Value Exercise rows, and defensively keeps the highest `totalAmtAccepted` when multiple rows share an `operationDate`.

Current local cache paths:

```text
data/cache/sources/nyfed_rrp.parquet
data/cache/metadata/nyfed_rrp.json
```

These cache files are ignored by git.

## Update Treasury Operating Cash Balance

Run an incremental update for the local Treasury Daily Treasury Statement Operating Cash Balance cache:

```powershell
uv run macro-observatory update treasury_dts_operating_cash_balance
```

This dataset uses the Treasury Fiscal Data API endpoint:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance
```

The cache intentionally preserves the full endpoint, not just the TGA rows needed by the first chart. Balance values are stored in Treasury's published units: millions of U.S. dollars.

Current local cache paths:

```text
data/cache/sources/treasury_dts_operating_cash_balance.parquet
data/cache/metadata/treasury_dts_operating_cash_balance.json
```

These cache files are ignored by git.

## Build Derived Treasury TGA

Build the derived Treasury General Account series from the full Treasury Operating Cash Balance source cache:

```powershell
uv run macro-observatory build-derived treasury_tga
```

This command reads:

```text
data/cache/sources/treasury_dts_operating_cash_balance.parquet
```

and writes:

```text
data/cache/derived/treasury_tga.parquet
data/cache/metadata/treasury_tga.json
```

The derived dataset keeps the TGA value in Treasury's published units, millions of U.S. dollars. It also includes traceability columns:

```text
source_account_type
source_balance_field
```

Those columns make Treasury account-name transitions visible when inspecting the data.

If the source cache is missing, run this first:

```powershell
uv run macro-observatory update treasury_dts_operating_cash_balance
```

## Build Derived Fed Net Liquidity

Build the derived Fed Net Liquidity dataset from the component source and derived caches:

```powershell
uv run macro-observatory build-derived fed_net_liquidity
```

This command requires these caches first:

```text
data/cache/sources/fred_walcl.parquet
data/cache/sources/fred_resppllopnww.parquet
data/cache/sources/nyfed_rrp.parquet
data/cache/derived/treasury_tga.parquet
```

and writes:

```text
data/cache/derived/fed_net_liquidity.parquet
data/cache/metadata/fed_net_liquidity.json
```

The output values are stored in U.S. dollars. FRED `WALCL`, FRED `RESPPLLOPNWW`, and Treasury `treasury_tga` values are converted from millions of dollars to dollars before the formula is calculated. New York Fed RRP values are already dollars.

The formula is:

```text
fed_net_liquidity = walcl - rrp - tga - rem
```

Components are outer-merged by date, sorted, forward-filled, and then the formula and diff columns are computed.

If component caches are missing, run the relevant source or derived commands first:

```powershell
uv run macro-observatory update fred_walcl
uv run macro-observatory update fred_resppllopnww
uv run macro-observatory update nyfed_rrp
uv run macro-observatory update treasury_dts_operating_cash_balance
uv run macro-observatory build-derived treasury_tga
```

## Publish Fed Net Liquidity Artifacts

Publish compact browser-facing artifacts from the derived Fed Net Liquidity cache:

```powershell
uv run macro-observatory publish fed_net_liquidity
```

This command reads:

```text
data/cache/derived/fed_net_liquidity.parquet
data/cache/metadata/fed_net_liquidity.json
```

and writes generated static-site artifacts:

```text
site/data/fed-net-liquidity.json
site/data/fed-net-liquidity.csv
site/data/fed-net-liquidity-metadata.json
```

The JSON artifact is a compact records array with `YYYY-MM-DD` date strings, lowercase stable column names, and raw numeric values in U.S. dollars. Missing values are written as JSON `null`.

The metadata artifact records the formula, units, source dataset IDs, source row counts, date range, dataset build timestamp, artifact filenames, and chart-series labels. It intentionally omits local cache paths and secrets.

`site/data/` is generated output and is ignored by git.

If the derived cache is missing, run this first:

```powershell
uv run macro-observatory build-derived fed_net_liquidity
```

Use a different static-site output directory when needed:

```powershell
uv run macro-observatory publish fed_net_liquidity --site-dir scratch-site
```

## Serve Static Site

Serve the generated static site locally:

```powershell
uv run macro-observatory serve-site
```

The default URL is:

```text
http://localhost:8000/
```

The root page lists available static pages. The first dashboard page is:

```text
http://localhost:8000/pages/fed-net-liquidity/
```

The Fed Net Liquidity page loads these published artifacts:

```text
site/data/fed-net-liquidity.json
site/data/fed-net-liquidity-metadata.json
```

If those files are missing or stale, run this first:

```powershell
uv run macro-observatory publish fed_net_liquidity
```

Use a different site directory or port when needed:

```powershell
uv run macro-observatory serve-site --site-dir scratch-site --port 8123
```


## Storage Report
Show a concise cross-platform report of known project data files:

```powershell
uv run macro-observatory storage-report
```

The report includes known source caches, derived caches, metadata files, and published site data artifacts. It does not scan arbitrary files under `data/` or `site/`.

Sizes are shown in fixed-width `KB` units with one decimal place and comma separators. Modified timestamps use this fixed column format:

```text
YYYY-MM-DD HH:MM:SS
```

Missing expected files are shown explicitly with a blank size and `missing` in the modified column.

Example shape:

```text
Group              Size KB  Modified             File
----------------  -------  -------------------  ----
source cache          21.0  2026-06-27 12:03:14  data/cache/sources/fred_walcl.parquet
site data          1,352.1  2026-06-27 15:08:31  site/data/fed-net-liquidity.json

Totals
source cache          21.0 KB
site data          1,352.1 KB
overall            1,373.1 KB
```

Use a different static-site output directory when needed:

```powershell
uv run macro-observatory storage-report --site-dir scratch-site
```

## Inspect Dataset Metadata

```powershell
uv run macro-observatory info fred_walcl
uv run macro-observatory info fred_resppllopnww
uv run macro-observatory info nyfed_rrp
uv run macro-observatory info treasury_dts_operating_cash_balance
uv run macro-observatory info treasury_tga
uv run macro-observatory info fed_net_liquidity
```

This prints the row count, date range, cache path, columns, and units recorded in metadata.

## Show Recent Rows

```powershell
uv run macro-observatory show fred_walcl --rows 10
uv run macro-observatory show fred_resppllopnww --rows 10
uv run macro-observatory show nyfed_rrp --rows 10
uv run macro-observatory show treasury_dts_operating_cash_balance --rows 10
uv run macro-observatory show treasury_tga --rows 10
uv run macro-observatory show fed_net_liquidity --rows 10
```

Use a different row count as needed:

```powershell
uv run macro-observatory show nyfed_rrp --rows 25
uv run macro-observatory show treasury_dts_operating_cash_balance --rows 25
uv run macro-observatory show treasury_tga --rows 25
uv run macro-observatory show fed_net_liquidity --rows 25
```

## Export Datasets

Export to CSV:

```powershell
uv run macro-observatory export fred_walcl --format csv --output exports/fred_walcl.csv
uv run macro-observatory export fred_resppllopnww --format csv --output exports/fred_resppllopnww.csv
uv run macro-observatory export nyfed_rrp --format csv --output exports/nyfed_rrp.csv
uv run macro-observatory export treasury_dts_operating_cash_balance --format csv --output exports/treasury_dts_operating_cash_balance.csv
uv run macro-observatory export treasury_tga --format csv --output exports/treasury_tga.csv
uv run macro-observatory export fed_net_liquidity --format csv --output exports/fed_net_liquidity.csv
```

Export to Parquet:

```powershell
uv run macro-observatory export fred_walcl --format parquet --output exports/fred_walcl.parquet
uv run macro-observatory export fred_resppllopnww --format parquet --output exports/fred_resppllopnww.parquet
uv run macro-observatory export nyfed_rrp --format parquet --output exports/nyfed_rrp.parquet
uv run macro-observatory export treasury_dts_operating_cash_balance --format parquet --output exports/treasury_dts_operating_cash_balance.parquet
uv run macro-observatory export treasury_tga --format parquet --output exports/treasury_tga.parquet
uv run macro-observatory export fed_net_liquidity --format parquet --output exports/fed_net_liquidity.parquet
```

The `exports/` directory is not special yet; it is just a convenient local output path.

## Load Datasets In Pandas

Start a Python REPL inside the uv environment:

```powershell
uv run python
```

Then load datasets by ID:

```python
from macro_observatory.data import load_dataset

df_walcl = load_dataset("fred_walcl")
df_resp = load_dataset("fred_resppllopnww")
df_rrp = load_dataset("nyfed_rrp")
df_treasury_ocb = load_dataset("treasury_dts_operating_cash_balance")
df_tga = load_dataset("treasury_tga")
df_net_liquidity = load_dataset("fed_net_liquidity")

df_walcl.tail()
df_resp.tail()
df_rrp.tail()
df_treasury_ocb.tail()
df_tga.tail()
df_net_liquidity.tail()

df_treasury_ocb["account_type"].drop_duplicates().sort_values()
df_tga.groupby(["source_account_type", "source_balance_field"]).agg(
    count=("date", "size"),
    min_date=("date", "min"),
    max_date=("date", "max"),
)
```

The normal user-facing API should use dataset IDs rather than requiring users to know cache file paths.

## Use A Different Data Directory

Most commands default to `data/`. To test with a separate cache directory, use `--data-dir` before the subcommand:

```powershell
uv run macro-observatory --data-dir scratch-data update fred_walcl
uv run macro-observatory --data-dir scratch-data update fred_resppllopnww
uv run macro-observatory --data-dir scratch-data update nyfed_rrp
uv run macro-observatory --data-dir scratch-data update treasury_dts_operating_cash_balance
uv run macro-observatory --data-dir scratch-data build-derived treasury_tga
uv run macro-observatory --data-dir scratch-data build-derived fed_net_liquidity
uv run macro-observatory --data-dir scratch-data publish fed_net_liquidity --site-dir scratch-site
uv run macro-observatory --data-dir scratch-data storage-report --site-dir scratch-site
uv run macro-observatory --data-dir scratch-data info nyfed_rrp
uv run macro-observatory --data-dir scratch-data info treasury_dts_operating_cash_balance
uv run macro-observatory --data-dir scratch-data info treasury_tga
uv run macro-observatory --data-dir scratch-data info fed_net_liquidity
uv run macro-observatory --data-dir scratch-data show nyfed_rrp --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_dts_operating_cash_balance --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_tga --rows 5
uv run macro-observatory --data-dir scratch-data show fed_net_liquidity --rows 5
```
