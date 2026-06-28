# Future Browser Data Formats

Status: future consideration

This document records a future research area for Macro Observatory: publishing more compact browser-facing data formats for dataframe-shaped macroeconomic datasets.

This is not part of the first implementation milestones. The current v1 path remains JSON and CSV because they are simple, debuggable, broadly supported, and easy to inspect in a static site.

## Motivation

The first `fed_net_liquidity` publish checkpoint made the size tradeoff visible:

```text
data/cache/derived/fed_net_liquidity.parquet       about 312 KB
site/data/fed-net-liquidity.csv                    about 700 KB
site/data/fed-net-liquidity.json                   about 1.38 MB
site/data/fed-net-liquidity-metadata.json          about 2 KB
```

JSON is convenient, but it is verbose for repeated dataframe-shaped rows. A time-series table repeats every column name for every row, and browser JavaScript has to parse the full text payload before charting. This is acceptable for the first chart, but it is a real limitation as datasets and pages grow.

The future goal is to explore compact browser artifacts that preserve the static-site model while reducing transfer size, parse cost, and memory overhead.

## Current Boundary

For the initial GitHub Pages milestone:

- Keep `site/data/*.json` as the primary browser data format.
- Keep `site/data/*.csv` as a simple download/export format.
- Do not introduce a browser binary-data dependency before the first chart works.
- Do not block the static chart milestone on format research.

Any compact format should be added as an optional additional artifact later, not as a replacement for the current simple JSON path until it has been measured.

## Candidate Formats

### Apache Arrow

Apache Arrow is the closest fit for a browser-facing dataframe artifact. It is a columnar format with JavaScript support and is designed for efficient analytical data interchange.

A future publisher could emit:

```text
site/data/fed-net-liquidity.arrow
```

Potential advantages:

- dataframe-shaped columnar layout,
- less repeated structural text than JSON,
- strong fit for numeric time-series columns,
- useful bridge to analytical frontends.

Questions to evaluate:

- browser bundle size for Arrow JS,
- parsing and conversion cost before feeding a chart library,
- whether the charting layer can consume Arrow-derived arrays cleanly,
- how well nulls, dates, and metadata round-trip.

References:

- https://arrow.apache.org/docs/js/
- https://arrow.apache.org/docs/format/Columnar.html

### Parquet In The Browser

Parquet is already a strong internal cache format for Pandas. It is compact and columnar, but browser use generally requires WebAssembly tooling rather than native browser APIs.

A future publisher could emit:

```text
site/data/fed-net-liquidity.parquet
```

Potential advantages:

- very compact for numeric columnar datasets,
- already familiar in the Python/Pandas data layer,
- useful for advanced users who want direct analytical downloads,
- strong fit for in-browser query engines.

Questions to evaluate:

- whether Parquet should be a public download artifact, browser chart artifact, or both,
- WebAssembly library size and startup cost,
- compatibility with GitHub Pages static hosting,
- how much JavaScript glue is required for chart rendering.

References:

- https://duckdb.org/docs/current/clients/wasm/overview.html
- https://duckdb.org/docs/current/clients/wasm/data_ingestion.html
- https://github.com/kylebarron/parquet-wasm

### DuckDB-Wasm

DuckDB-Wasm is less a file format and more an in-browser analytical engine. It can query data such as Parquet, Arrow, CSV, and JSON from a static site.

This is especially relevant to a future browser-based data explorer or notebook-like experience. It could support a lightweight web analogue of the current Pandas inspection workflow.

Potential advantages:

- SQL-style browser exploration,
- good fit for larger multi-dataset pages,
- possible foundation for a future browser data console.

Questions to evaluate:

- startup cost and bundle size,
- whether it is excessive for a simple chart page,
- how to keep the UI understandable for non-SQL users,
- how it interacts with future hosted or paywalled deployments.

### Compressed JSON

HTTP compression such as gzip or Brotli can reduce transfer size without changing the artifact shape. It does not remove JSON parse cost, but it may be enough for many chart pages.

This should be measured separately from binary formats because it depends on the hosting layer and deployment configuration.

Questions to evaluate:

- what compression GitHub Pages applies in practice,
- compressed JSON size versus Arrow and Parquet,
- parse time after decompression,
- cache behavior across browsers and hosts.

### Lower-Priority Binary Encodings

Formats such as MessagePack, CBOR, Protocol Buffers, or custom binary encodings may reduce size, but they are less naturally dataframe-shaped than Arrow or Parquet.

They should not be the first experiments unless a specific frontend requirement makes them attractive.

## Large-Dataset Rendering

The TGA Explorer checkpoint should also be treated as an early performance probe for large browser-rendered datasets.

If JSON payload size, browser parsing, JavaScript filtering, or Plotly rendering becomes a real bottleneck, the project should open a focused research track for large-dataset browser presentation. That research should not assume Plotly is permanent. Plotly is the practical baseline because it is familiar and already works for the first pages, but future interfaces may need a different rendering engine.

Potential areas to evaluate:

- WebGL-backed charting libraries for large scatter, bar, or time-series views.
- Canvas-based renderers where SVG DOM size becomes a bottleneck.
- Columnar browser data formats such as Arrow or Parquet paired with efficient array-based chart preparation.
- DuckDB-Wasm or similar in-browser query engines for filtering and aggregation before rendering.
- Chunked or pre-aggregated published artifacts for pages that do not need all detail at once.
- Server-backed or hybrid interfaces for managed deployments if pure static hosting becomes too limiting.

The current TGA Explorer implementation should still start with JSON and Plotly, plus render guardrails such as maximum row counts. The point of the checkpoint is to measure the baseline before adding complexity.
## Evaluation Plan

A future compact-format checkpoint should be measured against the existing JSON baseline.

Suggested benchmark dimensions:

- uncompressed file size,
- compressed transfer size where hosting supports it,
- browser fetch time,
- browser parse/load time,
- chart preparation time,
- chart render time,
- JavaScript or WebAssembly dependency size,
- implementation complexity,
- ease of local inspection,
- compatibility with GitHub Pages and other static hosts.

A good first experiment would publish one additional artifact for `fed_net_liquidity`, keep JSON unchanged, and compare both paths in the same local static page.

Example future commands could be:

```powershell
uv run macro-observatory publish fed_net_liquidity --extra-format arrow
uv run macro-observatory publish fed_net_liquidity --extra-format parquet
```

The exact CLI shape is not decided. The important point is that compact formats should be generated from the same derived cache and should remain reproducible.

## Design Rules For Later

When this work becomes active, the project should preserve these rules:

- The derived Parquet cache remains the analytical source of truth.
- JSON remains the simple compatibility baseline until a replacement is clearly better.
- Compact artifacts are generated outputs, not hand-edited source files.
- Metadata must describe the artifact format, schema version, units, formula, source datasets, and date range.
- The chart code should keep display labels separate from stable data column names.
- Browser format choices should be measured, not assumed.

## Non-Goals

This document does not propose implementing compact browser artifacts now.

It also does not propose replacing Pandas, replacing Parquet caches, or making DuckDB-Wasm part of the first static chart milestone.
