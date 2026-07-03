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

The Web Development APIs page says the securities API information has moved to the Fiscal Service API Community. The API Community page is JavaScript-heavy, but rendered captures show both a newer credential-gated Fiscal Service API and a `Historical Securities API Specifications` page for the legacy TreasuryDirect `TA_WS` endpoint.

The Auction Query and Auction Query help pages are UI-oriented rather than endpoint-oriented, but they confirm the domain surface: security type filtering, date/date-range filtering, optional columns, and export formats. The `TA_WS` endpoint behavior below was verified directly against live TreasuryDirect responses.

## Legacy Endpoint Stance

The `TA_WS/securities/search` endpoint should be treated as an active legacy endpoint.

Rendered Fiscal Service API Community content includes a `Historical Securities API Specifications` page that documents the `TA_WS` base URL and several legacy endpoint patterns. The PowerShell script remains valuable as documentation by working example, but the endpoint is no longer purely reverse-engineered for our purposes.

For this feature, the practical documentation stack is:

1. Fiscal Service API Community `Historical Securities API Specifications` rendered page for the legacy `TA_WS` contract.
2. The legacy PowerShell script as documentation by working example.
3. Live endpoint probes that verify current behavior.
4. TreasuryDirect Auction Query pages for user-facing domain context.
5. Fiscal Service API Community newer API documentation as a future migration candidate, not yet a proven replacement.

This should be an intentional dependency. Source code should make the legacy nature visible through naming and comments, but the derived report and web UI should not depend directly on TreasuryDirect-specific URL details.

## Legacy TA_WS Documentation Evidence

A rendered capture of the Fiscal Service API Community `Historical Securities API Specifications` page documents the legacy endpoint family directly.

It lists the base URL as:

```text
https://www.treasurydirect.gov/TA_WS/
```

It also describes these endpoint patterns:

```text
/securities/Cusip(9#)/Date(MM/DD/YYYY)
/securities/auctioned
/securities/Type(Bill,Note,Bond,CMB,TIPS,FRN)
/securities/search
```

The rendered text describes `/securities/auctioned` as returning auctioned securities, with a maximum of 250 results, ordered by auction date descending, issue date descending, and security term length ascending.

The rendered text describes `/securities/search` as accepting parameter names that match camel-cased variable names. Examples include:

```text
auctionDate=2013-05-25
interestRate=7.5
auctionDate=notNull
issueDate=today
```

The same section says dates accept `today`, parameters can use `notNull`, and `/securities/search` displays all securities by default when no parameters are passed.

The rendered example URLs use `format=xhtml`, while the live endpoint also supports the `format=json` usage required by the PowerShell script and Macro Observatory adapter.

This evidence means the legacy `TA_WS` endpoint is not merely an undocumented implementation detail. It is documented in the newer API Community as historical API behavior, but it should still be treated as legacy because the same page also presents a newer credential-gated Fiscal Service API surface.

## Future Fiscal Service Migration Path

Fiscal Data / Fiscal Service should be treated as the likely long-term destination if it becomes fully documented and functionally equivalent for this report.

Do not switch sources just because newer documentation exists. The replacement source must reproduce the report semantics that matter:

- issue-date window queries,
- maturity-date window queries,
- auction-date window queries,
- `totalAccepted`-equivalent issued and maturing amounts,
- `offeringAmount`-equivalent projection inputs,
- `somaTendered`-equivalent projection inputs,
- security type classification compatible with Bills, Notes, and Bonds,
- near-term auction context and issue-date projection behavior.

The preferred migration pattern is to add a second source adapter, not to replace the first one immediately:

```text
TreasuryDirect TA_WS adapter -> normalized security rows -> derived issued/maturing report
Fiscal Service adapter      -> normalized security rows -> derived issued/maturing report
```

Once both adapters can produce the same normalized model, add parity checks over matched date windows. The comparison should verify row-level totals, projected values, auction markers, and security-type splits. A temporary V2 or beta page can then render the Fiscal Service-backed artifact next to the TreasuryDirect-backed version for visual inspection.

Only retire the TreasuryDirect adapter after the newer source has proven parity for the report and has stable enough documentation to be a better operational dependency.

## Fiscal Service API Community Evidence

A rendered copy of the Fiscal Service API Community page shows a newer official API surface named:

```text
US Treasury Marketable Securities Experience API 2.0
```

The API console inside that page identifies the runtime API as:

```text
API title: Marketable Securities APIs
Version: v1
```

The page describes the dataset as marketable Treasury securities that have been announced, auctioned, or bought back. It explicitly names CUSIP, auction date, issue date, security type, security term, maturity date, and other descriptors for announced and auctioned securities. It also describes buyback data with operation date, CUSIP, maturity date, and other descriptors.

The rendered page lists these server choices:

```text
Mocking Service
https://gov.anypoint.mulesoft.com:443/mocking/api/v1/sources/exchange/assets/ee1361fc-22ec-4c9f-9b34-046766cdd066/us-treasury-marketable-securities-exp-api/2.0.34/m

Testing Instance (Does not contain production data)
https://api-preprod.fiscal.treasury.gov/ap/acc/exp/v1/marketable-securities

Production
https://api.fiscal.treasury.gov/ap/exp/v1/marketable-securities
```

The rendered endpoint list includes:

```text
GET /securities/announced
GET /securities/auctioned
GET /securities/upcoming
GET /securities/{cusip}/{MM}/{DD}/{YYYY}
GET /securities/{type}
GET /securities/stats
GET /schemas
GET /schemas/buybacks
GET /schemas/buybacks/announcements
GET /schemas/buybacks/results
GET /buybacks
GET /buybacks/{operationStartDTM}
GET /buybacks/special
GET /buybacks/special/expired
```

The rendered Requesting Access page says access requests are submitted through Fiscal Service's API Community Manager. The documented flow is:

1. Log in through the API Community page. Users without PIV or PIV-I credentials can use Login.gov or ID.me for identity confirmation.
2. Select `Request Access` on the Treasury Marketable Securities API page.
3. Choose an instance: `Production` or `Testing Instance (Does not contain production data)`.
4. Choose an SLA tier: `Silver`, `Gold`, or `Platinum`.
5. Create a new client application and provide the application name, company or organization, reason for access, and OAuth 2.0 redirect URL.
6. Submit the request. After approval, a contract is created between the client application and the instance, and the client application is registered.

The rendered page says instances are protected by a client ID enforcement policy and require client applications to provide a client ID and client secret. Those credentials are automatically created when the client application is registered. It also lists `taaps.support@fiscal.treasury.gov` for assistance.

The page also references `Security clientId - x-client-enforcement`. A direct unauthenticated probe of production endpoints returned HTTP 401 with:

```json
{ "error": "Invalid client id or secret" }
```

This means the newer Fiscal Service API is not a drop-in public replacement for the legacy unauthenticated TreasuryDirect `TA_WS` endpoint. It may become the preferred long-term source, but using it requires API access credentials and parity validation.

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

## Rolling Window And Snapshot Model

This source should not use the normal Macro Observatory historical backfill plus incremental update model.

TreasuryDirect `TA_WS` can expose records that are provisional from the report's point of view: announced securities, upcoming auctions, auctioned-but-not-settled rows, future issue dates, and projected values. Those rows can change as TreasuryDirect updates auction and issuance state.

For the first implementation, every refresh should fetch the configured rolling window fresh and replace the current source and derived artifacts. Do not append or merge rows into a long-lived canonical history for this report.

The current report should be modeled as:

```text
fresh TA_WS rolling-window fetch -> current source rows -> current issued/maturing report -> current site artifact
```

A historical archive can be added later, but it should be explicit snapshot history, not source-of-truth history. If implemented, snapshots should be immutable and keyed by retrieval time:

```text
snapshots/YYYY-MM-DDTHHMMSSZ/source.parquet
snapshots/YYYY-MM-DDTHHMMSSZ/report.parquet
snapshots/YYYY-MM-DDTHHMMSSZ/metadata.json
```

The UI could later default to the latest report while offering previous report snapshots in a dropdown. That archive would answer, "What did the report show when we generated it?" It would not answer, "What is the final historical truth for every security?"

The existing Fiscal Data-backed Treasury Securities Net Issuance page remains the historical/backfill source for long-range issuance and maturity analysis.

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

The live response contains many more columns. A representative check on `auctionDate=2026-07-01,2026-07-03` returned 120 fields. The adapter should preserve the raw rows in the current source cache so future reports can use additional fields without rethinking the ingestion boundary.

## Source Cache Recommendation

Use TreasuryDirect as its own source adapter namespace. Do not merge this cache with the existing Fiscal Data auctions cache.

Recommended first current-cache shape:

```text
data/cache/sources/treasurydirect_securities_current.parquet
data/cache/metadata/treasurydirect_securities_current.json
```

This cache is a replace-on-refresh artifact for the current rolling window. It should be overwritten each time the adapter runs successfully.

The cache should store raw or minimally normalized security rows, with explicit query provenance fields added by our adapter:

- `query_mode`: `issueDate`, `maturityDate`, or `auctionDate`
- `query_start_date`
- `query_end_date`
- `retrieved_at`
- `is_current_window`: true

Because the same security can appear in multiple query modes, the first implementation should preserve query provenance rather than deduplicating too early. A later derived step can create a report-local canonical security view keyed by CUSIP plus issue/auction/maturity dates if that becomes useful.

Do not use this cache as an append-only historical store. If historical retention is needed later, add an explicit snapshot archive keyed by `retrieved_at` and label it as report history.

## Derived Dataset Recommendation

The first derived dataset should be row-oriented, report-ready, and current-window scoped:

```text
data/cache/derived/treasurydirect_issued_maturing_current.parquet
```

This derived file should also be replaced on each successful refresh. It represents the latest report snapshot generated from the current rolling-window source rows.

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

Do not add a scheduled workflow until the source adapter and derived dataset have been validated locally and against the legacy report. When scheduling is added, each run should perform a fresh rolling-window fetch rather than an incremental update.

## Risks And Guardrails

TreasuryDirect can change API shape or field availability. The adapter should fail loudly if required fields are missing.

Numeric fields arrive as strings. The adapter should parse amount fields through a single helper and treat blanks as null/zero according to field semantics, not by accidental Python coercion.

Projected values must be labeled clearly in the derived dataset and UI. They should not be confused with completed issuance. Future/provisional rows should never be merged into a canonical historical truth table by accident.

The official API Community page now gives us a concrete newer API surface, but not a proven replacement. For the first implementation, the practical contract is still the combination of TreasuryDirect official pages, the legacy working script, and the live `TA_WS` response checks above.

## Open Questions

- Should the current rolling-window source keep one combined file with `query_mode`, or three current files by query mode?
- Should the first CLI checkpoint reproduce the PowerShell table exactly, or only verify row data parity?
- Should the browser page include a terminal-style artifact alongside the native table?
- Should the date window be user-configurable in the static page, precomputed in several windows, or fixed at publish time?
- If report snapshots are added, what retention policy and storage path should they use?
- How should TIPS and FRNs be represented? The legacy table focuses on Bills, Notes, and Bonds, while TreasuryDirect's UI notes that FRNs are listed with Notes and TIPS with Bonds.
