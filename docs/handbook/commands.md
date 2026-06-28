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

The current Treasury Fiscal Data datasets do not require an API key.

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
fred_walcl                                                       Federal Reserve Balance Sheet Assets (WALCL)
fred_resppllopnww                                                Earnings Remittances Due to the U.S. Treasury (RESPPLLOPNWW)
fred_sp500                                                       S&P 500 Index (SP500)
nyfed_rrp                                                        New York Fed Reverse Repo Operations (RRP)
treasury_dts_operating_cash_balance                              Treasury Daily Treasury Statement Operating Cash Balance
treasury_dts_deposits_withdrawals_operating_cash                 Treasury Daily Treasury Statement Deposits and Withdrawals of Operating Cash
treasury_od_auctions_query                                       Treasury Auctions Query
treasury_tga                                                     Treasury General Account (TGA)
treasury_dts_deposits_withdrawals_operating_cash_explorer        Treasury DTS Deposits and Withdrawals Explorer Dataset
treasury_securities_net_issuance                                 Treasury Securities Net Issuance
fed_net_liquidity                                                Fed Net Liquidity
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

## Update FRED SP500

Run an incremental update for the local S&P 500 cache:

```powershell
uv run macro-observatory update fred_sp500
```

This dataset is the FRED `SP500` series. It is published as a separate market-context artifact for future chart overlays and is not merged into Treasury Securities Net Issuance rows.

Current local cache paths:

```text
data/cache/sources/fred_sp500.parquet
data/cache/metadata/fred_sp500.json
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

## Update Treasury Deposits And Withdrawals Operating Cash

Run an incremental update for the local Treasury Daily Treasury Statement Deposits and Withdrawals of Operating Cash cache:

```powershell
uv run macro-observatory update treasury_dts_deposits_withdrawals_operating_cash
```

This dataset uses the Treasury Fiscal Data API endpoint:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash
```

The cache preserves the full endpoint, not just the columns needed by the TGA Explorer page. Transaction amounts are stored in Treasury's published units: millions of U.S. dollars.

Current local cache paths:

```text
data/cache/sources/treasury_dts_deposits_withdrawals_operating_cash.parquet
data/cache/metadata/treasury_dts_deposits_withdrawals_operating_cash.json
```

These cache files are ignored by git.

## Update Treasury Auctions Query

Run an incremental update for the local Treasury auctions query cache:

```powershell
uv run macro-observatory update treasury_od_auctions_query
```

This dataset uses the Treasury Fiscal Data API endpoint:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query
```

The cache preserves the full endpoint for Pandas inspection and future Treasury securities pages. The current source checkpoint parses `total_accepted` as U.S. dollars and uses `record_date` for incremental updates.

Current local cache paths:

```text
data/cache/sources/treasury_od_auctions_query.parquet
data/cache/metadata/treasury_od_auctions_query.json
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

## Build Derived TGA Explorer Dataset

Build the reduced TGA Explorer dataset from the full Treasury Deposits and Withdrawals source cache:

```powershell
uv run macro-observatory build-derived treasury_dts_deposits_withdrawals_operating_cash_explorer
```

This command reads:

```text
data/cache/sources/treasury_dts_deposits_withdrawals_operating_cash.parquet
```

and writes:

```text
data/cache/derived/treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet
data/cache/metadata/treasury_dts_deposits_withdrawals_operating_cash_explorer.json
```

The derived cache keeps the fields needed for Explorer-style TGA pages plus `src_line_nbr` for traceability. It applies the same baseline category exclusions used by the legacy Streamlit TGA Explorer page.

If the source cache is missing, run this first:

```powershell
uv run macro-observatory update treasury_dts_deposits_withdrawals_operating_cash
```

## Build Derived Treasury Securities Net Issuance

Build the derived Treasury Securities Net Issuance dataset from the full Treasury auctions query source cache:

```powershell
uv run macro-observatory build-derived treasury_securities_net_issuance
```

This command reads:

```text
data/cache/sources/treasury_od_auctions_query.parquet
```

and writes:

```text
data/cache/derived/treasury_securities_net_issuance.parquet
data/cache/metadata/treasury_securities_net_issuance.json
```

The derived cache precomputes the legacy pandas resample frequencies `D`, `W`, `ME`, `QE`, and `YE`. Rows are long-form by `frequency`, `date`, and `security_type`, with `issued`, `maturing`, and `net_issuance` in U.S. dollars. Future maturities are intentionally preserved.

If the source cache is missing, run this first:

```powershell
uv run macro-observatory update treasury_od_auctions_query
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

## Publish Treasury Securities Net Issuance Artifacts

Publish browser-facing artifacts from the derived Treasury Securities Net Issuance cache:

```powershell
uv run macro-observatory publish treasury_securities_net_issuance
```

This command reads:

```text
data/cache/derived/treasury_securities_net_issuance.parquet
data/cache/metadata/treasury_securities_net_issuance.json
```

and writes generated static-site artifacts:

```text
site/data/treasury-securities-net-issuance.json
site/data/treasury-securities-net-issuance.csv
site/data/treasury-securities-net-issuance-metadata.json
```

The JSON artifact uses compact split orientation and includes precomputed `D`, `W`, `ME`, `QE`, and `YE` rows. The browser page defaults to `ME`, filters by frequency and security type in JavaScript, and sends only non-zero `net_issuance` points to Plotly.

`site/data/` is generated output and is ignored by git.

If the derived cache is missing, run this first:

```powershell
uv run macro-observatory build-derived treasury_securities_net_issuance
```

Use a different static-site output directory when needed:

```powershell
uv run macro-observatory publish treasury_securities_net_issuance --site-dir scratch-site
```

## Publish SP500 Market Context Artifacts

Publish browser-facing market-context artifacts from the FRED SP500 source cache:

```powershell
uv run macro-observatory publish fred_sp500
```

This command reads:

```text
data/cache/sources/fred_sp500.parquet
data/cache/metadata/fred_sp500.json
```

and writes generated static-site artifacts:

```text
site/data/sp500.json
site/data/sp500.csv
site/data/sp500-metadata.json
```

The JSON artifact uses compact split orientation with `date` and `value` columns. It is intentionally independent from Treasury Securities Net Issuance rows so a later chart overlay can use a secondary y-axis without duplicating SP500 values across Treasury rows.

`site/data/` is generated output and is ignored by git.

If the source cache is missing, run this first:

```powershell
uv run macro-observatory update fred_sp500
```

Use a different static-site output directory when needed:

```powershell
uv run macro-observatory publish fred_sp500 --site-dir scratch-site
```

## Publish TGA Explorer Artifacts

Publish browser-facing artifacts from the derived TGA Explorer cache:

```powershell
uv run macro-observatory publish treasury_dts_deposits_withdrawals_operating_cash_explorer
```

This command reads:

```text
data/cache/derived/treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet
data/cache/metadata/treasury_dts_deposits_withdrawals_operating_cash_explorer.json
```

and writes generated static-site artifacts:

```text
site/data/tga-explorer.json
site/data/tga-explorer.csv
site/data/tga-explorer-metadata.json
```

The JSON artifact uses a compact JSON `split` shape with `columns` and `data` fields. This keeps the browser artifact in JSON while avoiding repeated field names for every row. The metadata records `json_orientation: split`, source endpoint, source row count, category count, transaction types, metric columns, units, and the initial render guardrail.

`site/data/` is generated output and is ignored by git.

If the derived cache is missing, run this first:

```powershell
uv run macro-observatory build-derived treasury_dts_deposits_withdrawals_operating_cash_explorer
```

Use a different static-site output directory when needed:

```powershell
uv run macro-observatory publish treasury_dts_deposits_withdrawals_operating_cash_explorer --site-dir scratch-site
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

The root page lists available static pages. Current dashboard pages are:

```text
http://localhost:8000/pages/fed-net-liquidity/
http://localhost:8000/pages/tga-explorer/
http://localhost:8000/pages/treasury-securities-net-issuance/
```

The Fed Net Liquidity page loads these published artifacts:

```text
site/data/fed-net-liquidity.json
site/data/fed-net-liquidity-metadata.json
```

The TGA Explorer page loads these published artifacts:

```text
site/data/tga-explorer.json
site/data/tga-explorer-metadata.json
```

The Treasury Securities Net Issuance page loads these published artifacts:

```text
site/data/treasury-securities-net-issuance.json
site/data/treasury-securities-net-issuance-metadata.json
```

The SP500 market-context artifact is generated for a future Treasury Securities overlay, but no current page consumes it yet:

```text
site/data/sp500.json
site/data/sp500-metadata.json
```

If the Fed Net Liquidity files are missing or stale, run this first:

```powershell
uv run macro-observatory publish fed_net_liquidity
```

If the TGA Explorer files are missing or stale, run this first:

```powershell
uv run macro-observatory publish treasury_dts_deposits_withdrawals_operating_cash_explorer
```

If the Treasury Securities Net Issuance files are missing or stale, run this first:

```powershell
uv run macro-observatory publish treasury_securities_net_issuance
```

Use a different site directory or port when needed:

```powershell
uv run macro-observatory serve-site --site-dir scratch-site --port 8123
```


## Build Static Site Artifacts

Build the current complete static site locally and update source caches from APIs:

```powershell
uv run macro-observatory build-site
```

This command updates the current source datasets, builds the current derived datasets, publishes the current browser artifacts, and writes:

```text
site/.nojekyll
```

The command currently builds the Fed Net Liquidity page, the TGA Explorer page, and the Treasury Securities Net Issuance page. It uses public network APIs, so it may take a while on a cold cache.

For the official manual GitHub Pages source-update policy, require the FRED API key explicitly:

```powershell
uv run macro-observatory build-site --require-fred-api-key
```

Build from existing local source caches without calling source APIs:

```powershell
uv run macro-observatory build-site --from-cache
```

This mode validates that all current source cache and metadata files exist, rebuilds derived caches and browser artifacts, and fails before any source API update path if a required source cache file is missing. The push-triggered GitHub Pages workflow uses this mode.

Update selected source caches and then rebuild all current derived caches and browser artifacts:

```powershell
uv run macro-observatory build-site --source-dataset nyfed_rrp
uv run macro-observatory build-site --source-dataset treasury_dts_operating_cash_balance --source-dataset treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory build-site --source-dataset treasury_od_auctions_query
uv run macro-observatory build-site --source-dataset fred_walcl --source-dataset fred_resppllopnww --source-dataset fred_sp500 --require-fred-api-key
```

Targeted source-update mode validates that all current source cache and metadata files exist before it updates anything. It updates only the selected source datasets, rebuilds every current derived dataset, republishes every current browser artifact, and writes `site/.nojekyll`.

`--source-dataset` may be repeated. Duplicate values are ignored after the first occurrence. `--source-dataset` cannot be combined with `--from-cache`.

Use a different static-site output directory when needed:

```powershell
uv run macro-observatory build-site --site-dir scratch-site
uv run macro-observatory build-site --source-dataset nyfed_rrp --site-dir scratch-site
```

## GitHub Pages Deployment

The repository deploys GitHub Pages with:

```text
.github/workflows/pages.yml
```

The workflow runs automatically on pushes to `main` and can also be started manually from the GitHub Actions tab.

Push-triggered runs are cache-only deploys. They restore the GitHub Actions `data/cache/` snapshot, fail if no cache is restored, run:

```powershell
uv run macro-observatory build-site --from-cache
```

and deploy the generated `site/` artifact. Push-triggered runs do not call source APIs and do not save a new data-cache snapshot.

Manual runs are source-update deploys. They restore the same cache, run source API updates, rebuild derived and browser artifacts, save a new immutable cache snapshot after success, and deploy the generated `site/` artifact.

The repository must have this GitHub Actions repository secret configured:

```text
FRED_API_KEY
```

The secret is read only by manual source-update runs. It must not be committed to git and must not be emitted into generated site data.

The GitHub Pages source should be set to:

```text
GitHub Actions
```

Do not use branch-folder publishing for this project. `site/data/` is generated output and is ignored by git, so the workflow uploads the generated `site/` directory as a Pages artifact instead.

The workflow restores and saves one GitHub Actions cache for:

```text
data/cache/
```

Normal manual source-update runs should use:

```text
allow_cold_build=false
```

If no data cache is restored, normal runs fail before calling source APIs.

The first cache-enabled deployment, or an intentional cache repair, should use:

```text
allow_cold_build=true
```

That setting allows a full API cold build only when explicitly requested. After a successful build, the workflow saves a new immutable cache snapshot with a key like:

```text
macro-observatory-data-cache-v1-Linux-<run_id>
```

The next run restores the newest matching cache through this prefix:

```text
macro-observatory-data-cache-v1-Linux-
```

The workflow logs event name, cache hit/miss state, matched cache key, `data/cache` size, selected `build-site` mode, `build-site` duration, and the storage report.

To inspect the generated artifact locally before a manual source-update deployment:

```powershell
uv run macro-observatory build-site --require-fred-api-key
uv run macro-observatory storage-report
uv run macro-observatory serve-site
```

To inspect the generated artifact locally the same way a push deployment does:

```powershell
uv run macro-observatory build-site --from-cache
uv run macro-observatory storage-report
uv run macro-observatory serve-site
```

## Scheduled GitHub Pages Refresh

Scheduled source-data refreshes are implemented with:

```text
.github/workflows/scheduled-refresh.yml
```

The workflow restores the GitHub Actions `data/cache/` snapshot, refuses to run if no cache is restored, updates only the selected source datasets, rebuilds all current derived datasets and browser artifacts, saves a new immutable cache snapshot, and deploys `site/`.

Current refresh groups:

```text
rrp_daily       -> nyfed_rrp
                  35 18 * * 1-5  # 18:35 UTC, 11:35 AM PDT / 10:35 AM PST

treasury_daily  -> treasury_dts_operating_cash_balance
                  treasury_dts_deposits_withdrawals_operating_cash
                  25 21 * * 1-5  # 21:25 UTC, 2:25 PM PDT / 1:25 PM PST

fred_weekly     -> fred_walcl
                  fred_resppllopnww
                  fred_sp500
                  55 21 * * 4    # 21:55 UTC Thursday, 2:55 PM PDT / 1:55 PM PST
```

Manual dispatch from GitHub CLI after the workflow exists on `main`:

```powershell
gh workflow run scheduled-refresh.yml --ref main -f refresh_group=rrp_daily
gh workflow run scheduled-refresh.yml --ref main -f refresh_group=treasury_daily
gh workflow run scheduled-refresh.yml --ref main -f refresh_group=fred_weekly
```

Watch recent scheduled refresh runs:

```powershell
gh run list --workflow scheduled-refresh.yml --limit 5
gh run watch <run-id> --exit-status
```

Equivalent local commands for the three refresh groups:

```powershell
uv run macro-observatory build-site --source-dataset nyfed_rrp
uv run macro-observatory build-site --source-dataset treasury_dts_operating_cash_balance --source-dataset treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory build-site --source-dataset treasury_od_auctions_query
uv run macro-observatory build-site --source-dataset fred_walcl --source-dataset fred_resppllopnww --source-dataset fred_sp500 --require-fred-api-key
```

The scheduled workflow shares the `github-pages` concurrency group with `.github/workflows/pages.yml` and uses `cancel-in-progress: false`, so push deploys and scheduled source updates queue instead of canceling each other.

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
Group                Size KB  Modified             File
----------------  ----------  -------------------  ----
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
uv run macro-observatory info fred_sp500
uv run macro-observatory info nyfed_rrp
uv run macro-observatory info treasury_dts_operating_cash_balance
uv run macro-observatory info treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory info treasury_od_auctions_query
uv run macro-observatory info treasury_tga
uv run macro-observatory info treasury_dts_deposits_withdrawals_operating_cash_explorer
uv run macro-observatory info treasury_securities_net_issuance
uv run macro-observatory info fed_net_liquidity
```

This prints the row count, date range, cache path, columns, and units recorded in metadata.

## Show Recent Rows

```powershell
uv run macro-observatory show fred_walcl --rows 10
uv run macro-observatory show fred_resppllopnww --rows 10
uv run macro-observatory show fred_sp500 --rows 10
uv run macro-observatory show nyfed_rrp --rows 10
uv run macro-observatory show treasury_dts_operating_cash_balance --rows 10
uv run macro-observatory show treasury_dts_deposits_withdrawals_operating_cash --rows 10
uv run macro-observatory show treasury_od_auctions_query --rows 10
uv run macro-observatory show treasury_tga --rows 10
uv run macro-observatory show treasury_dts_deposits_withdrawals_operating_cash_explorer --rows 10
uv run macro-observatory show treasury_securities_net_issuance --rows 10
uv run macro-observatory show fed_net_liquidity --rows 10
```

Use a different row count as needed:

```powershell
uv run macro-observatory show nyfed_rrp --rows 25
uv run macro-observatory show treasury_dts_operating_cash_balance --rows 25
uv run macro-observatory show treasury_dts_deposits_withdrawals_operating_cash --rows 25
uv run macro-observatory show treasury_od_auctions_query --rows 25
uv run macro-observatory show treasury_tga --rows 25
uv run macro-observatory show treasury_dts_deposits_withdrawals_operating_cash_explorer --rows 25
uv run macro-observatory show treasury_securities_net_issuance --rows 25
uv run macro-observatory show fed_net_liquidity --rows 25
```

## Export Datasets

Export to CSV:

```powershell
uv run macro-observatory export fred_walcl --format csv --output exports/fred_walcl.csv
uv run macro-observatory export fred_resppllopnww --format csv --output exports/fred_resppllopnww.csv
uv run macro-observatory export fred_sp500 --format csv --output exports/fred_sp500.csv
uv run macro-observatory export nyfed_rrp --format csv --output exports/nyfed_rrp.csv
uv run macro-observatory export treasury_dts_operating_cash_balance --format csv --output exports/treasury_dts_operating_cash_balance.csv
uv run macro-observatory export treasury_dts_deposits_withdrawals_operating_cash --format csv --output exports/treasury_dts_deposits_withdrawals_operating_cash.csv
uv run macro-observatory export treasury_od_auctions_query --format csv --output exports/treasury_od_auctions_query.csv
uv run macro-observatory export treasury_tga --format csv --output exports/treasury_tga.csv
uv run macro-observatory export treasury_dts_deposits_withdrawals_operating_cash_explorer --format csv --output exports/treasury_dts_deposits_withdrawals_operating_cash_explorer.csv
uv run macro-observatory export treasury_securities_net_issuance --format csv --output exports/treasury_securities_net_issuance.csv
uv run macro-observatory export fed_net_liquidity --format csv --output exports/fed_net_liquidity.csv
```

Export to Parquet:

```powershell
uv run macro-observatory export fred_walcl --format parquet --output exports/fred_walcl.parquet
uv run macro-observatory export fred_resppllopnww --format parquet --output exports/fred_resppllopnww.parquet
uv run macro-observatory export fred_sp500 --format parquet --output exports/fred_sp500.parquet
uv run macro-observatory export nyfed_rrp --format parquet --output exports/nyfed_rrp.parquet
uv run macro-observatory export treasury_dts_operating_cash_balance --format parquet --output exports/treasury_dts_operating_cash_balance.parquet
uv run macro-observatory export treasury_dts_deposits_withdrawals_operating_cash --format parquet --output exports/treasury_dts_deposits_withdrawals_operating_cash.parquet
uv run macro-observatory export treasury_od_auctions_query --format parquet --output exports/treasury_od_auctions_query.parquet
uv run macro-observatory export treasury_tga --format parquet --output exports/treasury_tga.parquet
uv run macro-observatory export treasury_dts_deposits_withdrawals_operating_cash_explorer --format parquet --output exports/treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet
uv run macro-observatory export treasury_securities_net_issuance --format parquet --output exports/treasury_securities_net_issuance.parquet
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
df_sp500 = load_dataset("fred_sp500")
df_rrp = load_dataset("nyfed_rrp")
df_treasury_ocb = load_dataset("treasury_dts_operating_cash_balance")
df_treasury_deposits_withdrawals = load_dataset("treasury_dts_deposits_withdrawals_operating_cash")
df_treasury_auctions = load_dataset("treasury_od_auctions_query")
df_tga = load_dataset("treasury_tga")
df_tga_explorer = load_dataset("treasury_dts_deposits_withdrawals_operating_cash_explorer")
df_treasury_net_issuance = load_dataset("treasury_securities_net_issuance")
df_net_liquidity = load_dataset("fed_net_liquidity")

df_walcl.tail()
df_resp.tail()
df_sp500.tail()
df_rrp.tail()
df_treasury_ocb.tail()
df_treasury_deposits_withdrawals.tail()
df_treasury_auctions.tail()
df_tga.tail()
df_tga_explorer.tail()
df_treasury_net_issuance.tail()
df_net_liquidity.tail()

df_treasury_ocb["account_type"].drop_duplicates().sort_values()
df_tga.groupby(["source_account_type", "source_balance_field"]).agg(
    count=("date", "size"),
    min_date=("date", "min"),
    max_date=("date", "max"),
)
df_treasury_auctions[
    [
        "record_date",
        "cusip",
        "security_type",
        "auction_date",
        "issue_date",
        "maturity_date",
        "total_accepted",
    ]
].tail()
df_treasury_net_issuance.query('frequency == "ME"').tail()
df_treasury_net_issuance.groupby("frequency", sort=False).size()
```

The normal user-facing API should use dataset IDs rather than requiring users to know cache file paths.

## Use A Different Data Directory

Most commands default to `data/`. To test with a separate cache directory, use `--data-dir` before the subcommand:

```powershell
uv run macro-observatory --data-dir scratch-data update fred_walcl
uv run macro-observatory --data-dir scratch-data update fred_resppllopnww
uv run macro-observatory --data-dir scratch-data update fred_sp500
uv run macro-observatory --data-dir scratch-data update nyfed_rrp
uv run macro-observatory --data-dir scratch-data update treasury_dts_operating_cash_balance
uv run macro-observatory --data-dir scratch-data update treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory --data-dir scratch-data update treasury_od_auctions_query
uv run macro-observatory --data-dir scratch-data build-derived treasury_tga
uv run macro-observatory --data-dir scratch-data build-derived treasury_dts_deposits_withdrawals_operating_cash_explorer
uv run macro-observatory --data-dir scratch-data build-derived treasury_securities_net_issuance
uv run macro-observatory --data-dir scratch-data build-derived fed_net_liquidity
uv run macro-observatory --data-dir scratch-data publish fed_net_liquidity --site-dir scratch-site
uv run macro-observatory --data-dir scratch-data publish treasury_dts_deposits_withdrawals_operating_cash_explorer --site-dir scratch-site
uv run macro-observatory --data-dir scratch-data publish treasury_securities_net_issuance --site-dir scratch-site
uv run macro-observatory --data-dir scratch-data publish fred_sp500 --site-dir scratch-site
uv run macro-observatory --data-dir scratch-data storage-report --site-dir scratch-site
uv run macro-observatory --data-dir scratch-data info nyfed_rrp
uv run macro-observatory --data-dir scratch-data info treasury_dts_operating_cash_balance
uv run macro-observatory --data-dir scratch-data info treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory --data-dir scratch-data info treasury_od_auctions_query
uv run macro-observatory --data-dir scratch-data info treasury_tga
uv run macro-observatory --data-dir scratch-data info treasury_dts_deposits_withdrawals_operating_cash_explorer
uv run macro-observatory --data-dir scratch-data info treasury_securities_net_issuance
uv run macro-observatory --data-dir scratch-data info fed_net_liquidity
uv run macro-observatory --data-dir scratch-data show nyfed_rrp --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_dts_operating_cash_balance --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_dts_deposits_withdrawals_operating_cash --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_od_auctions_query --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_tga --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_dts_deposits_withdrawals_operating_cash_explorer --rows 5
uv run macro-observatory --data-dir scratch-data show treasury_securities_net_issuance --rows 5
uv run macro-observatory --data-dir scratch-data show fed_net_liquidity --rows 5
```
