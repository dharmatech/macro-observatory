# TreasuryDirect Source API

Status: draft

This document records the source API findings for the TreasuryDirect Issued/Maturing feature. It is intentionally narrow: identify the source boundary, document the current endpoint behavior, and define enough of the first adapter contract to implement the Python checkpoint later.

## Research Summary

TreasuryDirect still exposes the endpoint family used by the legacy PowerShell script:

```text
https://www.treasurydirect.gov/TA_WS/securities/search
```

The legacy script used `http://...`; current requests should use `https://...`. The HTTP URL redirects to HTTPS.

During this checkpoint, the most relevant official pages found were:

- TreasuryDirect Web Development APIs: `https://www.treasurydirect.gov/legal-information/developers/`
- TreasuryDirect API terms: `https://www.treasurydirect.gov/legal-information/developers/web-api-terms/`
- TreasuryDirect Auction Query: `https://www.treasurydirect.gov/auctions/auction-query/`
- TreasuryDirect Auction Query help: `https://www.treasurydirect.gov/auctions/auction-query/auction-query-help/`
- Fiscal Service API Community securities page linked by TreasuryDirect: `https://api-community.fiscal.treasury.gov/s/communityapi/a01Qo00000pDeK7IAK/enterprise-apisustreasurymarketablesecuritiesexperienceapi`

The Web Development APIs page says the securities API information has moved to the Fiscal Service API Community. The API Community page appears to be a JavaScript-heavy Salesforce/Anypoint page; the static fetch did not expose a directly readable OpenAPI or Swagger document in this pass.

The Auction Query and Auction Query help pages are UI-oriented rather than endpoint-oriented, but they confirm the domain surface: security type filtering, date/date-range filtering, optional columns, and export formats. The `TA_WS` endpoint behavior below was verified directly against live TreasuryDirect responses.

## Endpoint Shape

Base endpoint:

```text
https://www.treasurydirect.gov/TA_WS/securities/search
```

The legacy report needs three date-window queries:

```text
?issueDate=YYYY-MM-DD,YYYY-MM-DD&format=json
?maturityDate=YYYY-MM-DD,YYYY-MM-DD&format=json
?auctionDate=YYYY-MM-DD,YYYY-MM-DD&format=json
```

Observed behavior:

- HTTP method: `GET`
- Authentication: none observed
- Response format for this adapter: JSON
- Response body: JSON array of security rows
- Date/time strings: ISO-like timestamp strings such as `2026-07-02T00:00:00`
- Numeric measures: returned as strings and should be parsed explicitly
- Query fields verified in live checks: `issueDate`, `maturityDate`, `auctionDate`

The Auction Query UI advertises CSV, JSON, TSV, and XML export formats. In the live `TA_WS/securities/search` checks for this URL pattern, `format=json` succeeded and `format=csv`, `format=tsv`, and `format=xml` returned HTTP 406. The first adapter should depend only on JSON.

## Legacy Query Window

The legacy PowerShell script defaults to:

```powershell
$a = today - 7 days
$b = $a + 45 days
```

That means the default window is roughly seven days of recent history plus about five and a half weeks of forward-looking auction/maturity context.

The first Python port should preserve this default unless we intentionally change it after parity testing.

## Fields Needed For The First Report

The legacy report can be reproduced from these fields:

- `cusip`
- `securityType`
- `type`
- `securityTerm`
- `announcementDate`
- `auctionDate`
- `issueDate`
- `maturityDate`
- `totalAccepted`
- `offeringAmount`
- `somaTendered`

Core semantics:

- Issued amount uses `totalAccepted` from rows matched by `issueDate`.
- Maturing amount uses `totalAccepted` from rows matched by `maturityDate`.
- Completed change is `issued - maturing`.
- Auction context uses rows matched by `auctionDate`.
- Projected change uses `offeringAmount + somaTendered - maturing` for rows grouped by `issueDate`.
- Security type splits are based on `securityType`, initially `Bill`, `Note`, and `Bond`.

The live response contains many more columns. A representative check on `auctionDate=2026-07-01,2026-07-03` returned 120 fields. The adapter should preserve the raw rows in the source cache so future reports can use additional fields without rethinking the ingestion boundary.

## Source Cache Recommendation

Use TreasuryDirect as its own source adapter namespace. Do not merge this cache with the existing Fiscal Data auctions cache.

Recommended first cache shape:

```text
data/cache/sources/treasurydirect_securities.parquet
data/cache/metadata/treasurydirect_securities.json
```

The cache should store raw or minimally normalized security rows, with explicit query provenance fields added by our adapter:

- `query_mode`: `issueDate`, `maturityDate`, or `auctionDate`
- `query_start_date`
- `query_end_date`
- `retrieved_at`

Because the same security can appear in multiple query modes, the first implementation should preserve query provenance rather than deduplicating too early. A later derived step can create a canonical security view keyed by CUSIP plus issue/auction/maturity dates if that becomes useful.

## Derived Dataset Recommendation

The first derived dataset should be row-oriented and report-ready:

```text
data/cache/derived/treasurydirect_issued_maturing.parquet
```

Possible browser artifact names:

```text
site/data/treasurydirect-issued-maturing.json
site/data/treasurydirect-issued-maturing.csv
site/data/treasurydirect-issued-maturing-metadata.json
```

The derived rows should preserve the legacy one-row-per-date table model:

- date
- Bills issued, maturing, change
- Notes issued, maturing, change
- Bonds issued, maturing, change
- Total issued, maturing, change
- `change_with_weekend`
- `auction`
- `auction_issuing`
- `offeringAmount`
- `somaTendered`
- `projected_change`
- projected Bills, Notes, Bonds change

Weekend rollover should match the PowerShell script: weekend completed changes are accumulated and added to the next weekday as `change_with_weekend`.

## Freshness

This feature is near-term operational data. It should eventually refresh on business days after TreasuryDirect auction/security data is expected to be current.

Do not add a scheduled workflow until the source adapter and derived dataset have been validated locally and against the legacy report.

## Risks And Guardrails

TreasuryDirect can change API shape or field availability. The adapter should fail loudly if required fields are missing.

Numeric fields arrive as strings. The adapter should parse amount fields through a single helper and treat blanks as null/zero according to field semantics, not by accidental Python coercion.

Projected values must be labeled clearly in the derived dataset and UI. They should not be confused with completed issuance.

The official API Community page should be revisited if we need a stronger machine-readable contract. For the first implementation, the practical contract is the combination of TreasuryDirect official pages, the legacy working script, and the live `TA_WS` response checks above.

## Open Questions

- Should the source cache keep one combined file with `query_mode`, or three source files by query mode?
- Should the first CLI checkpoint reproduce the PowerShell table exactly, or only verify row data parity?
- Should the browser page include a terminal-style artifact alongside the native table?
- Should the date window be user-configurable in the static page, precomputed in several windows, or fixed at publish time?
- How should TIPS and FRNs be represented? The legacy table focuses on Bills, Notes, and Bonds, while TreasuryDirect's UI notes that FRNs are listed with Notes and TIPS with Bonds.
