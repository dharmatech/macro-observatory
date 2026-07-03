# TGA Top Milestone

Status: draft

TGA Top is the next proposed Treasury Daily Treasury Statement page for Macro Observatory. It should port the legacy Streamlit `TGA_top` page in spirit, not line by line.

The page is a daily snapshot view over the same Treasury deposits and withdrawals dataset used by TGA Explorer. Where TGA Explorer is built for broad historical exploration, TGA Top should answer a narrower question: for a selected date, what were the largest Treasury General Account deposits and withdrawals?

## Legacy Reference

The legacy Streamlit page lives in two places:

- `C:\Users\dharm\Dropbox\Documents\fed_net_liquidity_streamlit.py\pages\4_TGA_top.py`
- `C:\Users\dharm\Dropbox\Documents\tga_top_streamlit.py\tga_top_streamlit.py`

The legacy page uses this Treasury Fiscal Data endpoint:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash
```

It loads the endpoint into Pandas, converts `record_date` and amount columns, lets the user choose a date, then renders:

- a deposits table for that date,
- a withdrawals table for that date,
- a withdrawals FYTD pie chart by raw category,
- a withdrawals FYTD pie chart with selected categories grouped by agency abbreviation.

## V1 Data Decision

TGA Top v1 should not add a new source dataset, derived dataset, or scheduled refresh.

It should reuse the existing published TGA Explorer artifact:

```text
site/data/tga-explorer.json
site/data/tga-explorer-metadata.json
```

The current pipeline is:

```text
Treasury Fiscal Data API
  -> data/cache/sources/treasury_dts_deposits_withdrawals_operating_cash.parquet
  -> data/cache/derived/treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet
  -> site/data/tga-explorer.json
  -> TGA Explorer and TGA Top browser pages
```

This is acceptable for v1 because TGA Top needs the same categories, transaction types, dates, and amount columns already published for TGA Explorer.

A future `site/data/tga-top.json` artifact should be considered only if measured page-load cost or browser memory use shows that a smaller daily snapshot artifact is worthwhile.

## Page Shape

Add a new static page:

```text
site/pages/tga-top/index.html
site/assets/js/tga-top.js
```

The home page should list TGA Top next to the other available dashboards.

The first page version should include:

- dataset metadata and latest available date,
- a date selector defaulting to the latest `record_date`,
- a summary of the selected date,
- a ranked deposits table,
- a ranked withdrawals table,
- a raw-category withdrawals FYTD pie chart,
- a grouped-agency withdrawals FYTD pie chart.

Tables are the primary surface. Pie charts are useful secondary context, but the main purpose of the page is to identify the top daily flows quickly.

## Table Behavior

For the selected date, split rows by `transaction_type`:

- `Deposits`
- `Withdrawals`

Each table should sort by `transaction_today_amt` descending, matching the legacy page.

The visible columns should be compact and scanner-friendly:

- category,
- today,
- month-to-date,
- fiscal-year-to-date.

The legacy page renames these columns to:

- `today`
- `mtd`
- `fytd`

The web page can use either short table headers or tooltip/label text, but the table should remain dense enough for daily inspection.

Amounts are in millions of U.S. dollars in the source artifact. Display should make units clear and avoid mixed units within the same column.

## Pie Chart Behavior

The first pie chart should show withdrawals FYTD by raw `transaction_catg` for the selected date.

It should exclude rows where:

- `transaction_catg` is `null`,
- `transaction_catg` contains `Public Debt Cash Redemp`, case-insensitive.

The legacy page divides FYTD amounts by 1000 and labels the chart as billions of U.S. dollars. The new page should preserve that display convention for the pie charts.

## Grouped Agency Pie Chart

The grouped agency pie chart should start with the same selected-date withdrawals FYTD rows, apply the same exclusions, then collapse selected categories by agency abbreviation.

The legacy grouping rules replace any category containing these case-sensitive substrings:

```text
HHS
USDA
DoD
SSA
VA
OPM
TREAS
DOT
DHS
DOL
```

Rows with categories that do not match those abbreviations should keep their original category label. After relabeling, values are summed by final label.

This behavior is useful but intentionally heuristic. The v1 port should preserve the legacy behavior, while leaving room for a better maintained grouping map later.

## Interaction Model

The date selector should be lightweight and static-site friendly.

Possible v1 behavior:

- use an HTML date input,
- clamp or reset to the latest available date if the chosen date is unavailable,
- show a clear message when no rows exist for the selected date,
- optionally expose previous/next available date controls later.

The first implementation does not need advanced URL state, but it should be designed so selected date can be added to the URL later.

## Performance Notes

TGA Top will initially load the same `tga-explorer.json` artifact as TGA Explorer. This means it loads more history than a one-day snapshot requires.

That is acceptable for now because:

- the existing TGA Explorer page already loads this artifact successfully,
- TGA Top conceptually uses the same category and amount space,
- reuse avoids another generated artifact before there is evidence that one is needed,
- the existing scheduled Treasury refresh already keeps the artifact current.

If TGA Top becomes a frequently used daily landing page, revisit whether to publish a compact artifact containing recent dates, selected-date top rows, or precomputed pie-chart inputs.

## Validation

The first implementation should verify:

- the page loads from the static site,
- the latest date defaults correctly,
- deposits and withdrawals tables match the legacy page for a sampled date,
- raw-category pie chart uses withdrawals FYTD and legacy exclusions,
- grouped-agency pie chart applies the legacy grouping rules,
- no new source update or scheduled refresh is required,
- the home page links to TGA Top.

## Non-Goals For V1

- Add a new Treasury source adapter.
- Add a new derived cache dataset.
- Add a new published `tga-top.json` artifact.
- Add a new scheduled GitHub Actions refresh.
- Recreate Streamlit dataframe widgets exactly.
- Build a fully maintained Treasury agency taxonomy.
- Add URL state for selected date unless it is trivial during implementation.

## Open Questions

- Should tables show all rows or only a top N with an option to expand?
- Should deposits also get pie-chart views, or should pies remain withdrawals-only like the legacy page?
- Should the grouped agency rules remain hard-coded in JavaScript for v1, or move into a shared metadata/config file?
- Should selected date eventually be encoded in the URL?
- Should a smaller `tga-top.json` artifact be added if the page becomes a daily landing view?

## Next Checkpoint

Implement the static TGA Top page using the existing `tga-explorer.json` and metadata artifacts. Keep the implementation scoped to browser presentation and home-page navigation.
