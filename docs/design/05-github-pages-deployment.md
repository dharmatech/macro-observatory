# GitHub Pages Deployment Checkpoint

Status: implemented

This checkpoint publishes the current static site to GitHub Pages without adding scheduled data refresh yet.

The deployment intentionally keeps generated data out of git:

```text
data/cache/
site/data/
```

Those paths remain ignored. The GitHub Actions workflow regenerates them during deployment and uploads the complete `site/` directory as the Pages artifact.

## Scope

Included:

- build the current static site on push to `main`,
- allow manual deployment with `workflow_dispatch`,
- require `FRED_API_KEY` for the official GitHub Pages deployment,
- regenerate source caches, derived datasets, and browser artifacts during the workflow,
- publish the generated `site/` directory through the GitHub Pages Actions deployment flow,
- write `site/.nojekyll` so Pages serves the static assets directly.

Not included:

- scheduled data refresh,
- retry windows around data release times,
- freshness delay banners,
- alerting,
- paid hosting,
- alternate browser data formats.

Those remain future checkpoints.

## Workflow

The Pages workflow lives at:

```text
.github/workflows/pages.yml
```

It runs on:

```text
push to main
manual workflow_dispatch
```

The build job:

1. checks out the repository,
2. installs `uv`,
3. sets up Python from `.python-version`,
4. runs `uv sync --locked`,
5. verifies that `FRED_API_KEY` is configured as a repository Actions secret,
6. runs `uv run macro-observatory build-site --require-fred-api-key`,
7. prints the storage report,
8. uploads `site/` as the Pages artifact.

The deploy job uses GitHub's Pages deployment action to publish that artifact.

## Build Command

The local and CI entry point is:

```powershell
uv run macro-observatory build-site
```

For the official Pages deployment:

```bash
uv run macro-observatory build-site --require-fred-api-key
```

The command currently performs the full v1 site pipeline:

```text
update fred_walcl
update fred_resppllopnww
update nyfed_rrp
update treasury_dts_operating_cash_balance
update treasury_dts_deposits_withdrawals_operating_cash
build-derived treasury_tga
build-derived treasury_dts_deposits_withdrawals_operating_cash_explorer
build-derived fed_net_liquidity
publish fed_net_liquidity
publish treasury_dts_deposits_withdrawals_operating_cash_explorer
write site/.nojekyll
```

This deliberately rebuilds from public source APIs on deploy. Later scheduled refresh work can reuse the same command or split the source updates by cadence.

## Secret Policy

The Python FRED adapter can fall back to public FRED CSV access for local experimentation, but the official Pages workflow must not silently fall back.

The repository must define this Actions secret:

```text
FRED_API_KEY
```

The secret is passed only to the build step. It is not written into source code, generated browser data, metadata artifacts, or static JavaScript.

## Pages Settings

The repository's GitHub Pages source should be configured as:

```text
GitHub Actions
```

This is different from branch-folder publishing. Branch-folder publishing would not include ignored generated artifacts unless they were committed, which this project intentionally avoids.

## Future Refresh Checkpoint

Scheduled refresh should be designed separately. It should account for:

- release times per source dataset,
- UTC conversion for GitHub Actions schedules,
- short in-job retry/backoff for transient API failures,
- idempotent repeated runs around expected release windows,
- source freshness metadata,
- subtle site status when observations are delayed.
