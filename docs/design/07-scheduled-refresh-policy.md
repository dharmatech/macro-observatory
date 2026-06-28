# Scheduled Refresh Policy

Status: proposed

This design note defines the initial scheduled data-refresh policy for Macro Observatory on GitHub Actions.

The goal is to keep the public GitHub Pages site fresh without turning every deployment into a full API update. Push deployments remain cache-only. Manual deployments remain the explicit bootstrap and repair path. Scheduled refresh runs become the normal way public source data is incrementally updated.

## Current Foundation

The current deployment model has three useful behaviors already in place:

- `data/cache/` is restored from GitHub Actions cache before site builds.
- push-triggered Pages deployments run `macro-observatory build-site --from-cache`, do not call source APIs, and do not save a new data-cache snapshot.
- manual Pages deployments can intentionally update source APIs and save a new data-cache snapshot after success.

Scheduled refresh should build on that model rather than replacing it.

## GitHub Actions Schedule Facts

The GitHub Actions `schedule` event uses POSIX cron syntax. GitHub's current documentation says scheduled workflows default to UTC, run on the latest commit on the default branch, and can be delayed or dropped during periods of high load, especially around the start of an hour.

GitHub now also documents an optional `timezone` field for timezone-aware scheduling. The initial Macro Observatory design will still use UTC cron entries with explicit comments for Pacific and Eastern time. That keeps the schedule unambiguous in logs and matches the current cache/deploy workflow style. If the one-hour daylight-saving offset becomes irritating, switching schedule entries to `timezone: America/Los_Angeles` is a reasonable future simplification.

When one workflow has multiple scheduled cron entries, GitHub exposes the triggering cron string through `github.event.schedule`. We can use that to route one scheduled workflow to different refresh groups.

Reference:

```text
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
```

## Legacy Schedule Hints

The legacy Streamlit project has these cron comments:

```text
RRP:
25 10 * * MON-FRI      # 10:25 AM Pacific

Treasury operating cash balance:
10 13 * * MON-FRI      # 01:10 PM Pacific

FRED WALCL and RESPPLLOPNWW:
50 13 * * MON-FRI      # 01:50 PM Pacific, note says THUR

Treasury auctions query:
0 14 * * MON-FRI       # 02:00 PM Pacific
```

The TGA Explorer source script, `deposits_withdrawals_operating_cash.sh`, has no cron comment, but it is Treasury Daily Treasury Statement data and should be refreshed with the other Treasury Daily Treasury Statement source.

Only the first three groups are in scope for current pages. Auctions is noted for later Treasury securities pages.

## Initial Refresh Groups

The scheduled workflow should support these refresh groups.

| Refresh group | Source datasets | Proposed fixed UTC cron | Pacific sanity check | Eastern sanity check | Scope |
| --- | --- | --- | --- | --- | --- |
| `rrp_daily` | `nyfed_rrp` | `35 18 * * 1-5` | 11:35 AM PDT / 10:35 AM PST | 2:35 PM EDT / 1:35 PM EST | Fed Net Liquidity |
| `treasury_daily` | `treasury_dts_operating_cash_balance`, `treasury_dts_deposits_withdrawals_operating_cash` | `25 21 * * 1-5` | 2:25 PM PDT / 1:25 PM PST | 5:25 PM EDT / 4:25 PM EST | Fed Net Liquidity and TGA Explorer |
| `fred_weekly` | `fred_walcl`, `fred_resppllopnww` | `55 21 * * 4` | 2:55 PM PDT / 1:55 PM PST | 5:55 PM EDT / 4:55 PM EST | Fed Net Liquidity |

These UTC times are intentionally conservative. They are later than the legacy local-time comments during daylight saving time, but they avoid being too early during standard time.

They also avoid minute `0`, which reduces exposure to GitHub Actions high-load behavior around the top of the hour.

## Workflow Shape

Implement scheduled refresh as a separate workflow first:

```text
.github/workflows/scheduled-refresh.yml
```

The workflow should have:

- the three schedule entries above,
- comments next to each cron entry showing UTC, Pacific, and Eastern time,
- a `workflow_dispatch` input for manually running one refresh group,
- the same Pages deployment permissions as the existing Pages workflow,
- the same data-cache restore policy as the existing Pages workflow,
- no scheduled cold-build fallback.

A sketch of the schedule block:

```yaml
on:
  schedule:
    # RRP daily: 18:35 UTC = 11:35 AM PDT / 10:35 AM PST = 2:35 PM EDT / 1:35 PM EST.
    - cron: "35 18 * * 1-5"
    # Treasury DTS daily: 21:25 UTC = 2:25 PM PDT / 1:25 PM PST = 5:25 PM EDT / 4:25 PM EST.
    - cron: "25 21 * * 1-5"
    # FRED weekly: 21:55 UTC Thursday = 2:55 PM PDT / 1:55 PM PST = 5:55 PM EDT / 4:55 PM EST.
    - cron: "55 21 * * 4"
  workflow_dispatch:
    inputs:
      refresh_group:
        type: choice
        options:
          - rrp_daily
          - treasury_daily
          - fred_weekly
```

The workflow can map `github.event.schedule` or `github.event.inputs.refresh_group` to a list of source dataset IDs.

## Python CLI Support Needed

Before implementing the workflow, `build-site` should support targeted source updates.

Proposed command shape:

```powershell
uv run macro-observatory build-site --source-dataset nyfed_rrp
uv run macro-observatory build-site --source-dataset treasury_dts_operating_cash_balance --source-dataset treasury_dts_deposits_withdrawals_operating_cash
uv run macro-observatory build-site --source-dataset fred_walcl --source-dataset fred_resppllopnww --require-fred-api-key
```

Policy:

- no `--source-dataset` means the current full source-update behavior,
- `--from-cache` conflicts with `--source-dataset`,
- targeted source-update mode validates that every current source cache and metadata file exists before updating selected sources,
- targeted source-update mode updates only the selected source datasets,
- after selected source updates, the command rebuilds all current derived datasets and republishes all current browser artifacts.

Rebuilding all derived/site artifacts is intentionally simpler than a dependency graph at this stage. The current data sizes and build times are small enough that this is practical, and it keeps cross-page dependencies safe.

## Cache Policy

Scheduled refresh runs should:

1. restore `data/cache/` from the newest matching Actions cache,
2. fail before source API calls if no cache is restored,
3. validate required source cache files before targeted updates,
4. update only the selected source datasets,
5. rebuild all derived datasets and browser artifacts,
6. save a new immutable `data/cache/` snapshot after success,
7. deploy the generated `site/` artifact.

Scheduled refresh runs should not cold-build from APIs. Bootstrap and repair cold builds remain manual-only operations.

Saving a new cache snapshot after every successful scheduled refresh is acceptable for the current cache size. If cache growth becomes material, a later checkpoint can save only when metadata or source row counts changed.

## Secrets

`fred_weekly` requires `FRED_API_KEY` and should fail if it is not configured.

The other current refresh groups do not need API keys. The workflow can still pass `FRED_API_KEY` as an environment variable to all refresh groups, but the explicit secret validation should only be required for `fred_weekly` or for any future group that needs a secret.

## Concurrency

Scheduled refresh, manual source-update deployment, and push cache-only deployment all publish the same Pages site.

The scheduled refresh workflow should use the same broad concurrency group as the Pages deployment workflow, but scheduled source-update jobs should not be casually canceled by a push deploy. Before implementation, review the current `cancel-in-progress` behavior and choose one of these policies:

- queue refresh and deploy jobs behind each other, or
- allow push deploys to cancel older push deploys but not scheduled source-update runs.

The conservative initial policy is to avoid canceling a scheduled source-update run once it has started.

## Observability

The workflow should log:

- event name,
- triggering cron string or manual refresh group,
- resolved refresh group,
- selected source dataset IDs,
- cache primary key and matched key,
- cache size before and after build,
- source update mode,
- source datasets updated,
- per-command duration,
- storage report.

A successful scheduled run should make it obvious that the workflow did an incremental update, saved a new cache snapshot, and deployed the site.

A failed scheduled run should fail loudly before source APIs are called if the cache is missing or incomplete.

## Next Implementation Checkpoint

The next implementation checkpoint should be:

1. add targeted source-update support to `build-site`,
2. test that targeted mode updates only selected source datasets,
3. add `scheduled-refresh.yml` with the three initial refresh groups,
4. manually dispatch each refresh group once to validate behavior,
5. document the validation results.