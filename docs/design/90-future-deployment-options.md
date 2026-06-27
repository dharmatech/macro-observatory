# Future Deployment Options

Status: future consideration

This document records possible future deployment directions for Macro Observatory. It is not part of the first implementation milestone and should not expand the current scope.

The first target remains a public static site on GitHub Pages, with data updates and site generation driven by ordinary project commands. Future hosting and payment options should build on that same core pipeline rather than replacing it.

## Current Boundary

Macro Observatory should first prove one open, reproducible path:

```text
source APIs
  -> local/cacheable Python data pipeline
  -> Pandas-friendly datasets
  -> static published artifacts
  -> public static site
```

For the first milestone, GitHub Pages and GitHub Actions are the practical target. Other hosts are worth keeping in mind, but they should not affect source API checkpoints or the first Fed Net Liquidity chart except through one design rule: the core commands should remain platform-neutral.

Examples of platform-neutral commands are:

```powershell
uv run macro-observatory update fred_walcl
uv run macro-observatory build-site
```

The exact command names may change, but hosting platforms should call project commands. The data pipeline should not become GitHub-specific workflow code.

## Future Hosting Lanes

Future deployments could include several lanes:

- GitHub Pages as the free public reference deployment.
- A local static preview for users who clone the repository.
- A self-hosted deployment on an Ubuntu server with cron or a similar scheduler.
- A managed static or hybrid deployment on a commercial platform such as Vercel, Cloudflare, Netlify, or another comparable host.

These are examples, not commitments. Any specific platform should be evaluated at implementation time because pricing, limits, runtime support, and service guarantees change.

## Managed Hosted Instance

A future managed instance could be useful if the free GitHub-hosted deployment becomes unreliable, rate-limited, stale, or inconvenient for users who do not want to run their own copy.

The clean framing is:

- The source code remains open.
- The reproducible data pipeline remains open.
- Publicly available source data remains public.
- The paid offering, if any, is for hosted convenience, operational maintenance, freshness monitoring, support, and possibly higher reliability.

This distinction matters. The paid service should not be described as selling exclusive ownership of the public source code or underlying public data.

## Optional Payment And Access Layer

A future managed instance could add account login and subscription billing. Stripe is a plausible payment provider example, but the design should not require Stripe until that work is actually in scope.

Possible managed-service pieces:

- user accounts and login,
- subscription checkout,
- account billing portal,
- subscription-status checks,
- private or authenticated access to the hosted app,
- freshness and failure monitoring,
- support contact or issue workflow.

This should be treated as an optional wrapper around the project, not as part of the core data layer.

## Future Alerting Layer

A future hosted or self-hosted deployment could add an alerting layer on top of the same datasets used by the charts. This should be modeled as another downstream consumer of the data pipeline, not as part of the charting layer.

The preferred shape is:

```text
source caches
  -> derived datasets
  -> published web artifacts
  -> public static charts

source caches
  -> derived datasets
  -> alert rules
  -> alert events
  -> delivery channels
```

Example alert rules could include:

- all-time high or all-time low,
- largest daily, weekly, or release-over-release change,
- rolling-window z-score or percentile outlier,
- threshold crossing,
- spread or inversion event,
- missing, stale, or delayed source data.

Alert evaluation should consume stable Pandas-friendly datasets and produce structured alert events. Delivery should be pluggable and platform-specific. Early local versions could write alert events to JSON, logs, or a static alerts page. A future managed instance could support email, SMS, webhooks, Discord or Slack, RSS/Atom, or social posting.

If alerts become part of a paid hosted offering, the paid component should be framed as hosted convenience, delivery infrastructure, preference management, and operational maintenance. The underlying public source data and open data-processing code should remain separate from that service wrapper.

This is not part of the first milestone. The current design implication is only to keep derived datasets stable, metadata-rich, and easy for non-chart consumers to load.

## Paywall Security Boundary

A real paywall cannot rely only on client-side JavaScript.

If browser-facing JSON, CSV, or Parquet files are deployed as public static files, any user can fetch them directly. A button, login modal, or client-side route guard does not protect those files.

A real protected managed instance would need server-side enforcement, such as:

- authenticated routes,
- server-side subscription checks,
- private object storage,
- signed URLs,
- or a backend/API layer that serves data only after access checks.

That is a different hosting model from pure GitHub Pages. It should remain outside the first milestone.

## Data And Legal Due Diligence

Before any commercial hosted service is launched, the project should review source-specific terms and operational constraints.

Questions to answer later:

- Do source APIs allow redistribution in the planned form?
- Are there attribution requirements?
- Are there commercial-use limitations?
- Are there API rate limits or contact-identity requirements?
- Do generated datasets need source timestamps or disclaimers?
- Does the hosted service need privacy policy, terms of service, or support policies?
- How should account data, billing data, and access logs be handled?

These questions do not block the open-source first milestone, but they matter before charging users for a managed service.

## Design Implications Now

The current project should preserve future flexibility by keeping these rules:

- Keep source adapters, cache management, derived datasets, and publication logic in normal Python package code.
- Make schedulers call the CLI instead of embedding business logic in GitHub Actions YAML.
- Keep published artifacts distinct from internal cache files.
- Record generated metadata such as data freshness, source ranges, and build timestamps.
- Avoid assuming every deployment target can run server-side code.
- Avoid assuming every deployment target is purely static.
- Keep secrets in environment variables or platform secret stores, never in committed files or public artifacts.

These rules support GitHub Pages now and leave room for managed hosting later.

## Non-Goals

This document does not propose implementing:

- Vercel integration,
- Stripe integration,
- user accounts,
- subscriptions,
- private data hosting,
- service-level guarantees,
- or multi-platform deployment automation.

Those are future options only. The next implementation work should remain focused on the source dataset checkpoints for the first Fed Net Liquidity chart.
