# Data Layer And Cache Design

Status: draft

This document describes the initial data-layer design for Macro Observatory. It supports the first Fed Net Liquidity milestone while leaving room for additional datasets and presentations later.

The main goal is to build a Python/Pandas-friendly data pipeline that can fetch source data, update it incrementally, store it locally, expose it for inspection, and publish compact static artifacts for a browser-based site.

## Language And Tooling

Python is the canonical language for the backend data pipeline.

Python owns:

- source API access,
- incremental updates,
- cache maintenance,
- normalization,
- validation,
- derived datasets,
- publication of static data artifacts,
- command-line inspection utilities.

Browser JavaScript or TypeScript owns only the static presentation layer. Frontend code should consume already-published artifacts. It should not contain canonical data fetching, normalization, or financial formula logic.

The Python project should use `uv` from the start. The project should be a uv-managed package so that dependencies, command execution, tests, and future GitHub Actions jobs are repeatable.

Expected tooling direction:

```powershell
uv init --package
uv sync
uv add pandas pyarrow requests
uv add --dev pytest ruff mypy
uv run pytest
uv run ruff check .
uv run mypy .
```

The exact dependency list may change during implementation, but commands in documentation and automation should use `uv run` or `uv sync` rather than relying on global Python or bare `pip`.

## Type Hints

Python code should use type hints generously where they improve refactoring and readability.

Type hints are especially useful for:

- dataset specs,
- source adapter contracts,
- cache metadata,
- update results,
- publication artifact descriptors,
- CLI/public functions.

Pandas dataframe schemas should be validated explicitly at runtime. Static typing alone is not enough to describe required dataframe columns and dtypes clearly.

Example interface shape:

```python
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class DatasetSpec:
    id: str
    date_column: str
    primary_key: tuple[str, ...]
    overlap_days: int
    cache_path: str


@dataclass(frozen=True)
class UpdateResult:
    dataset_id: str
    rows_before: int
    rows_after: int
    min_date: date | None
    max_date: date | None
    updated_at: datetime


class SourceAdapter(Protocol):
    def fetch(self, start_date: date | None) -> pd.DataFrame:
        ...
```

The exact implementation may differ, but the design direction is:

- type the interfaces and metadata,
- validate dataframe contents at runtime.

## Dataset IDs

Every maintained dataset should have a stable ID.

Initial expected IDs:

- `fred_walcl`
- `fred_resppllopnww`
- `nyfed_rrp`
- `treasury_tga`
- `fed_net_liquidity`

Dataset IDs should be used consistently by:

- update commands,
- inspection commands,
- cache filenames,
- metadata records,
- published artifacts where practical,
- chart-to-data links.

## Dataset Registry

The project should have a dataset registry. It can start as simple Python data structures and evolve later if needed.

The registry should describe enough about each dataset for the shared data layer to update, cache, inspect, and publish it.

Likely registry fields:

- dataset ID,
- human-readable title,
- source adapter,
- source endpoint or series ID,
- source date column,
- normalized date column,
- primary key columns,
- overlap window,
- cache path,
- expected schema,
- update cadence,
- public/private publication behavior,
- required secret names.

The registry should not contain secret values.

## Source Adapters

Source adapters are API-specific.

Initial adapters:

- FRED adapter,
- New York Fed adapter,
- Treasury Fiscal Data adapter.

Adapters should know how to:

- construct source requests,
- apply required authentication or request metadata,
- handle source pagination or API quirks,
- return fetched rows as Pandas dataframes.

Adapters should not own the generic cache/update lifecycle. That should be shared.

## Shared Incremental Update Lifecycle

The incremental updater should be shared across datasets where practical.

General lifecycle:

1. Load existing cache if present.
2. Determine the latest known source date.
3. Subtract the dataset overlap window.
4. Ask the source adapter to fetch rows from that start date.
5. Normalize fetched rows enough to merge.
6. Merge old and new rows.
7. Deduplicate by configured primary key.
8. Prefer new rows when duplicates occur inside the overlap window.
9. Sort by date and primary key.
10. Validate required columns and dtypes.
11. Write cache data.
12. Write metadata.
13. Return an `UpdateResult`.

The overlap window is important because upstream datasets may revise recent values after initial publication.

Each source may require special handling, but source-specific code should plug into the shared lifecycle rather than reimplementing the full update process.

## Cache Layout

The cache should distinguish source-level data from derived data.

Possible layout:

```text
data/
  cache/
    sources/
      fred_walcl.parquet
      fred_resppllopnww.parquet
      nyfed_rrp.parquet
      treasury_tga.parquet
    derived/
      fed_net_liquidity.parquet
    metadata/
      fred_walcl.json
      fred_resppllopnww.json
      nyfed_rrp.json
      treasury_tga.json
      fed_net_liquidity.json
```

This layout is provisional. The implementation may adjust it, but the source/derived/metadata distinction should remain.

## Storage Format

The preferred initial cache format is Parquet plus metadata JSON.

Parquet is a strong fit because:

- Pandas reads and writes it directly,
- it preserves types better than CSV,
- it is usually smaller than CSV or JSON,
- it is safer and more portable than pickle,
- it works well for build-time datasets.

Metadata JSON is useful because it is easy to inspect without loading the full dataframe.

Metadata should include:

- dataset ID,
- source name,
- source endpoint or series,
- row count,
- min date,
- max date,
- last successful update time,
- overlap window,
- cache file path,
- schema or column summary,
- source units and display units where practical.

Metadata must not contain secrets.

## Published Artifacts

Published artifacts are separate from internal cache files.

Internal cache files support incremental updates and Pandas inspection. Published artifacts support the static web frontend.

For the first Fed Net Liquidity chart, likely published artifacts are:

```text
site/
  data/
    fed-net-liquidity.json
    fed-net-liquidity.csv
    fed-net-liquidity-metadata.json
```

A Parquet artifact may also be published if useful for direct Pandas download, but the browser should not need to load raw source caches.

Published artifacts should be compact and specific to the presentation. A large raw Treasury cache can exist at build time without becoming a large browser payload.

## User Inspection

Every maintained dataset should be easy to inspect by name.

The exact CLI shape is not final, but the design target is:

```text
datasets
update fred_walcl
info fred_walcl
show fred_walcl
export fred_walcl --format csv
```

The Python API should be similarly direct:

```python
from macro_observatory.data import load_dataset

df = load_dataset("fred_walcl")
```

For derived datasets:

```python
df = load_dataset("fed_net_liquidity")
```

The data layer should hide file paths and storage details from normal users.

## Secrets And Configuration

Secrets are deployment configuration, not project data.

Expected secret-like values:

- `FRED_API_KEY`,
- Treasury contact email or equivalent request metadata, if used,
- future API tokens.

Local development can use environment variables or a local uncommitted `.env` file. GitHub Actions should use repository secrets.

Source adapters should read secrets through explicit configuration or environment variables. They should not hard-code secrets, print secrets, or write secrets to metadata.

Pull-request and unit-test workflows should not require live secrets where possible. Tests can use fixtures, recorded small samples, or mocked adapters.

## Validation

Validation should happen at multiple layers.

Source cache validation:

- required columns exist,
- date column parses,
- primary key columns are non-null,
- numeric columns parse where expected,
- row count and date range are plausible.

Derived dataset validation:

- required source datasets are present,
- joins do not unexpectedly drop all rows,
- expected columns exist,
- unit conversions are explicit,
- formula output is present,
- latest rows can be compared to the existing implementation during the first milestone.

Published artifact validation:

- files are written,
- metadata date range matches source data,
- JSON loads successfully,
- CSV loads successfully,
- browser-facing payload is reasonably small.

## GitHub Actions And Portability

GitHub Actions should orchestrate the data pipeline, not contain the core logic.

The eventual workflow should call project commands such as:

```powershell
uv sync
uv run macro-observatory update fed_net_liquidity
uv run macro-observatory publish fed_net_liquidity
```

The exact command names are not final.

The same commands should be runnable locally. A future DigitalOcean or other server deployment should be able to use cron to run the same commands and serve the generated static files with a regular web server.

## Open Questions

- What exact CLI command name should the package expose?
- Should the dataset registry start as Python code, TOML, YAML, or JSON?
- Should cache files be committed to git, stored on a data branch, or regenerated from source in scheduled workflows?
- Should published Parquet files be exposed publicly for Pandas users?
- What schema validation helper should be used: lightweight custom checks, Pandera, Pydantic metadata models, or something else?
- How much source metadata should be carried into browser-facing metadata?
- How should update failures be reported in GitHub Actions and local CLI output?
