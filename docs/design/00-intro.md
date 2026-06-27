# Macro Observatory Design Intro

Status: draft

Macro Observatory is a new project for collecting, transforming, publishing, and presenting macroeconomic and financial time-series data. The initial target is a GitHub Pages site that renders a Fed Net Liquidity chart from generated static data files.

The project is inspired by the existing `fed_net_liquidity_streamlit.py` and related Python libraries, but it is not intended to modify them. Those projects remain the working Streamlit/DigitalOcean system. Macro Observatory is a fresh architecture aimed at static hosting, repeatable data builds, and clear user inspection paths.

## Why This Project Exists

The existing Streamlit app works well as a live Python application:

- Pandas dataframes are available directly.
- Streamlit provides fast interactive exploration.
- DigitalOcean can run Python, cron jobs, local caches, and server-side dependencies.
- Multiple Streamlit pages can act as small apps over related datasets.

GitHub Pages changes the runtime model. A GitHub Pages site can serve HTML, CSS, JavaScript, images, and static data files, but it cannot run Streamlit or Python when a visitor opens the page.

Macro Observatory should preserve the useful parts of the current workflow while moving page-view work into the browser and moving Python/Pandas work into update and build steps.

## Primary Target

The primary deployment target is GitHub Pages.

The first implementation should prove this flow:

```text
source APIs
  -> incremental local cache
  -> Pandas normalization and transforms
  -> static published data artifacts
  -> GitHub Pages chart and table
```

The project should not become a general hosting framework. However, the core update and build commands should remain ordinary command-line operations so that a future deployment could run the same pipeline under cron on an Ubuntu server.

## First Milestone

The first milestone is one complete vertical slice: a Fed Net Liquidity presentation rendered on GitHub Pages.

This chart is a good first target because it exercises multiple source APIs while keeping the browser-facing dataset relatively small:

- FRED for Federal Reserve balance sheet data such as `WALCL`.
- FRED for `RESPPLLOPNWW` if the current `REM` term remains part of the formula.
- New York Fed for reverse repo operation data.
- Treasury Fiscal Data for Treasury General Account data.

The initial goal is not to recreate every Streamlit page. The first goal is to build one source-to-chart pipeline correctly.

## Development Checkpoints

Work should proceed API by API. A source integration is not complete until it can:

- fetch the required source data,
- store it locally in the new cache format,
- reload it as a Pandas dataframe,
- perform an incremental update with an overlap window,
- expose a user-facing way to inspect it,
- survive a checkpoint review before moving to the next source.

For the Fed Net Liquidity milestone, likely checkpoints are:

1. FRED `WALCL`.
2. FRED `RESPPLLOPNWW`, if needed.
3. New York Fed RRP.
4. Treasury TGA.
5. Derived Fed Net Liquidity dataframe.
6. Static published data and first chart.

## Core Principles

### Pandas First

The deployed site is static and browser-oriented, but the data layer should remain Pandas-friendly. Every maintained dataset should be loadable as a Pandas dataframe by name.

For example, the eventual Python interface should feel like:

```python
from macro_observatory.data import load_dataset

df = load_dataset("fed_net_liquidity")
```

The durable storage format does not have to be pickle. Parquet is a likely candidate for internal cache and normalized data because it is compact, typed, portable, and easy to read with Pandas.

### Static Presentation Data

Browser-facing files should be presentation-neutral where practical. The data pipeline should not make Plotly the data model.

The first chart may use Plotly.js because it is close to the existing Streamlit/Plotly experience, but the same published dataset should be reusable by future presentations.

### Incremental Updates

Incremental updates are a requirement, not an optimization.

The update flow should generally:

1. load the existing cache,
2. find the latest known source date,
3. request new source rows starting from that date minus an overlap window,
4. merge old and new rows,
5. deduplicate by configured keys,
6. sort and validate,
7. write updated cache and metadata.

Each source API has its own quirks, but the update lifecycle should be shared where possible.

### Modular Source Adapters

Source-specific code should live behind source adapters:

- Treasury Fiscal Data adapter.
- FRED adapter.
- New York Fed adapter.

Adapters should know how to talk to their source API. Shared infrastructure should handle cache loading, merge/dedupe behavior, metadata, and serialization.

### User Inspectability

The project should make data easy to inspect without requiring the user to know internal file paths.

Each maintained dataset should eventually support operations like:

- update by dataset name,
- show row count and date range,
- preview recent rows,
- load into Pandas,
- export to CSV or another simple format.

Charts should eventually link back to their underlying data and show a short Pandas snippet for local inspection.

### Safe Secrets

Secrets are deployment configuration, not project data.

API keys, contact email addresses, and other private values should come from environment variables, local `.env` files, or GitHub Actions secrets. They must not be committed to source control or emitted into published site artifacts.

## Relationship To The Existing Projects

The existing multi-repo Streamlit system is the reference implementation and working production system.

Macro Observatory may reuse ideas, formulas, endpoint knowledge, and behavioral lessons from the existing projects. It should not require changing those projects.

For now, Macro Observatory is a monorepo. Internal Python modules can replace the current multi-repo leaf-library layout while the new design is being proven.

## Non-Goals For The First Milestone

- Port every Streamlit page.
- Recreate the full DigitalOcean deployment.
- Build a general framework for arbitrary APIs.
- Decide every future charting library.
- Make all raw source data browser-loadable.
- Optimize every large Treasury dataset before the first chart works.

## Open Questions

- Should the Fed Net Liquidity formula be `WALCL - RRP - TGA` or `WALCL - RRP - TGA - REM`?
- What exact durable cache format should v1 use?
- What exact web data formats should be published for the first chart?
- Should the first presentation use Plotly.js, or should another charting library be tested first?
- What should the first command-line interface look like?
- Which generated data files should be committed, and which should be build-only?
- What update cadence should be used for each source?

## Next Design Document

The next design document should describe the Fed Net Liquidity milestone in more detail, including source datasets, API checkpoints, cache behavior, published artifacts, and the first static chart requirements.
