# GitHub Actions Cache Persistence Checkpoint

Status: implemented

This checkpoint adds a GitHub-native persistence layer for `data/cache/` without changing the Python data pipeline.

GitHub-hosted runners are ephemeral. Without an explicit persistence layer, each Pages deployment starts from an empty filesystem and cold-fetches source data from public APIs. This checkpoint avoids that by restoring `data/cache/` from GitHub Actions cache before site builds.

## Scope

Included:

- one Actions cache for the entire `data/cache/` directory,
- explicit `allow_cold_build` manual input,
- refusal to cold-build unless `allow_cold_build=true`,
- cache hit/miss logging,
- cache size logging before and after `build-site`,
- manual source-update deploys that save a new immutable cache snapshot after success,
- push-triggered cache-only deploys that run `build-site --from-cache`,
- push-triggered refusal to deploy if no cache is restored,
- no Python source-code awareness of GitHub Actions cache internals.

Not included:

- dataset-level caches,
- automatic cache cleanup,
- scheduled refresh,
- external object storage,
- self-hosted runner support.

## Workflow Policy

Manual runs are source-update deploys.

Normal manual runs should use:

```text
allow_cold_build=false
```

If a data cache is restored, the workflow runs normal incremental updates, rebuilds derived and browser artifacts, saves a new cache snapshot, and deploys the site. If no data cache is restored, the workflow fails before calling source APIs.

Bootstrap or repair runs may use:

```text
allow_cold_build=true
```

This is only for the first cache-enabled run or for an intentional cache repair. On a cache miss, this mode permits a full API cold build, saves the first or replacement `data/cache/` snapshot, and deploys the site.

Push-triggered runs are cache-only deploys. They restore the newest matching data cache, fail if no cache is restored, run:

```text
macro-observatory build-site --from-cache
```

and deploy the generated `site/` artifact. Push-triggered runs do not call source APIs and do not save a new data-cache snapshot.

## Cache Keys

The workflow uses one cache namespace:

```text
macro-observatory-data-cache-v1-${runner.os}-
```

Manual source-update runs save a unique immutable key:

```text
macro-observatory-data-cache-v1-${runner.os}-${github.run_id}
```

The next run restores the newest matching cache through the restore-key prefix. If GitHub restores a prefix match, the cache action reports `cache-hit=false` but also sets `cache-matched-key`. An empty `cache-hit` means no cache was restored.

## Why Single Cache First

Current cache size is small enough that a single `data/cache/` snapshot is simpler and more practical than dataset-level cache splitting.

Dataset-level caches remain a future optimization if restore/save time, cache size, or storage usage becomes a real issue.

## Observability

The workflow prints:

- `EVENT_NAME`,
- `CACHE_HIT`,
- `CACHE_PRIMARY_KEY`,
- `CACHE_MATCHED_KEY`,
- `ALLOW_COLD_BUILD`,
- `data/cache` size before build when present,
- selected `build-site` mode,
- `build-site` duration,
- `data/cache` size after build,
- the normal storage report.

These logs should make cold builds visible, prove whether a push used the cache-only path, and make cache restore/save performance measurable.

## Python Entry Point

`macro-observatory build-site` remains the aggregate deployment command.

Default behavior updates source caches from APIs, builds derived datasets, publishes browser artifacts, and writes `site/.nojekyll`.

`macro-observatory build-site --from-cache` validates that all current source cache and metadata files exist, skips every source update adapter, builds derived datasets, publishes browser artifacts, and writes `site/.nojekyll`.

The `--from-cache` flag is intentionally platform-neutral. GitHub Actions uses it for push deploys, but the command is also useful locally or on another host when a valid `data/cache/` snapshot already exists.

## Validation Results

Initial manual cache validation completed on June 28, 2026.

Bootstrap run:

```text
run: 28315964925
allow_cold_build: true
cache restored: no
cold build: yes
build-site duration: 132 seconds
data/cache size after build: 8.0 MB
saved cache key: macro-observatory-data-cache-v1-Linux-28315964925
result: success
```

Normal restore run:

```text
run: 28316049169
allow_cold_build: false
cache restored: yes
matched cache key: macro-observatory-data-cache-v1-Linux-28315964925
cold build: no
build-site duration: 9 seconds
data/cache size before build: 8.0 MB
data/cache size after build: 8.0 MB
saved cache key: macro-observatory-data-cache-v1-Linux-28316049169
result: success
```

The deployed root page, both current dashboard pages, and both JSON data artifacts returned HTTP 200 after the cache-enabled deployment.

## Next Steps

After this checkpoint:

1. Validate the first push-triggered cache-only deployment in GitHub Actions logs.
2. Design scheduled refresh workflows for daily Treasury/New York Fed data and weekly FRED balance-sheet data.
3. Keep dataset-level caches and external object storage as future options only if the single-cache workflow becomes too slow or too large.
