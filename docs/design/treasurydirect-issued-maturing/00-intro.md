# TreasuryDirect Issued/Maturing Intro

Status: draft

This folder documents a possible Macro Observatory report/page based on the legacy `treasury-direct-issued-maturing.ps1` project. The legacy project is a self-contained PowerShell console program that predates the Streamlit dashboards and the Python data libraries.

The goal of this design work is to capture context and preserve the useful behavior before any Python or web implementation begins. This is not a line-by-line port plan yet. It is the orientation document for the feature family.

## References

Legacy project directory:

```text
C:\Users\dharm\Dropbox\Documents\treasury-direct-issued-maturing.ps1
```

Legacy PowerShell script:

```text
C:\Users\dharm\Dropbox\Documents\treasury-direct-issued-maturing.ps1\treasury-direct-issued-maturing.ps1
```

Rendered example report:

```text
https://dharmatech.dev/data/reports/treasury-direct-issued-maturing-latest.html
```

The rendered report is produced by running the PowerShell console report on a DigitalOcean server, capturing terminal output, converting ANSI terminal output to HTML, and publishing the HTML artifact.

## What The Legacy Tool Is

The legacy tool began as a simple PowerShell console application. It has a narrow purpose and no external project dependency structure. It queries TreasuryDirect directly, reshapes the returned rows, and prints a dense colorized terminal table.

The script is valuable because it captures the domain model compactly:

- fetch issued securities by issue date,
- fetch maturing securities by maturity date,
- fetch auctioned securities by auction date,
- aggregate issued, maturing, and net change by date,
- split those measures across Bills, Notes, Bonds, and Total,
- include auction context and near-term projected change,
- roll weekend changes into the next weekday for scan-friendly reporting.

The console output uses color as part of the user experience. Positive changes are green, negative changes are red, and the table is aligned for a wide terminal window.

## Source Boundary

This feature should use TreasuryDirect as its source boundary.

TreasuryDirect endpoint family used by the legacy script:

```text
http://www.treasurydirect.gov/TA_WS/securities/search
```

The current Macro Observatory Treasury Securities Net Issuance page uses Treasury Fiscal Data instead:

```text
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query
```

These sources overlap in subject matter but should remain distinct in Macro Observatory. TreasuryDirect is closer to the current operational auction and security search system. Treasury Fiscal Data is better viewed as a normalized public data platform and historical archive.

## Relationship To The Existing Treasury Securities Page

This feature is not intended to replace the existing Treasury Securities Net Issuance page.

The existing page remains a Fiscal Data / treasury.gov-backed historical analysis page. It is designed for long-range issuance and maturity analysis, resampling, cumulative views, and chart overlays.

The TreasuryDirect Issued/Maturing feature is a separate report/page candidate. It is intended for a near-term operational calendar view: what is being issued, what is maturing, what auctions are relevant, and what projected changes are visible over the next several weeks.

Both pages can exist side by side because they answer different questions.

## Report Shape

The legacy report is a wide table with one row per date.

Core column groups:

- Date
- Bills: issued, maturing, change
- Notes: issued, maturing, change
- Bonds: issued, maturing, change
- Total: issued, maturing, change

Additional operational columns:

- `change_with_weekend`
- `auction`
- `auction_issuing`
- `offeringAmount`
- `somaTendered`
- `projected_change`
- projected split: `bills`, `notes`, `bonds`

The wide row is important. A major value of the report is comparing the security-type groups and totals for the same date.

## Presentation Options

### Embedded Terminal Report

One option is to preserve the terminal-report presentation directly. Macro Observatory could present normal page chrome, then embed a terminal-style report region that resembles the existing HTML conversion output.

This honors the original tool and keeps the console report as the canonical presentation. It is also a reusable pattern for future terminal reports.

Tradeoffs:

- It would feel different from the Plotly and native table pages.
- Horizontal scrolling would be unavoidable.
- Interactivity would be limited unless built around the artifact.
- Mobile usability would be weak.

### Native Web Report

Another option is to treat the PowerShell script as a domain prototype and redesign the presentation as native HTML.

A native page could use:

- sticky date column,
- sticky grouped headers,
- compact numeric formatting,
- red and green change formatting,
- horizontal scrolling inside the table frame,
- controls for date range and visible column groups.

This fits Macro Observatory better as a first-class page, but it requires reimplementing the presentation instead of reusing the console output.

## Recommended First Presentation

The recommended first Macro Observatory presentation is a native wide table with progressive column disclosure.

Default visible columns should stay compact, likely:

- date,
- Total issued,
- Total maturing,
- Total change,
- auction marker,
- projected change.

Optional column groups should be toggleable:

- Bills,
- Notes,
- Bonds,
- Auction Context,
- Projection Details.

This keeps the one-row-per-date comparison model while avoiding an overwhelming first view. It also preserves the path to the full wide report for users who want the complete operational table.

A vertically partitioned page, where Bills, Notes, Bonds, and Total appear in separate page sections, is not recommended for the first version because it loses the row-level comparison that makes the original report useful.

## Possible Implementation Path

A likely sequence:

1. Document the TreasuryDirect source API and source fields.
2. Add a Python TreasuryDirect source adapter.
3. Build a derived daily issued/maturing report dataset matching the PowerShell semantics.
4. Add a CLI or data export checkpoint for parity testing against the legacy report.
5. Publish a browser-facing JSON/CSV artifact.
6. Build a Macro Observatory static page with the native wide table and column group toggles.
7. Add scheduled refresh behavior once the data/cache behavior is understood.

The Python port should preserve the clear domain logic first. The web page should follow after the data shape is proven.

## Non-Goals For The Intro Checkpoint

This document does not define the full API adapter contract, exact cache paths, or final UI details.

This feature should not:

- replace the existing Treasury Securities Net Issuance page,
- merge TreasuryDirect and Fiscal Data provenance prematurely,
- force the report into a mobile-first card layout,
- require a line-by-line PowerShell port,
- discard the terminal-report heritage before evaluating it.

## Open Questions

Questions for follow-up docs:

- What exact TreasuryDirect fields are needed for parity with the current report?
- Should the first Python checkpoint reproduce the PowerShell report output exactly, or only reproduce the row data?
- What default date window should Macro Observatory use?
- Should the TreasuryDirect source cache store full raw rows for each query mode, or a normalized union of securities?
- How should upcoming auction projections be labeled so users do not confuse projected changes with completed issuance?
- Should a classic terminal-report artifact remain available alongside the native web table?
