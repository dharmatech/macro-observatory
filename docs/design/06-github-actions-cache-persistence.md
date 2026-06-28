# GitHub Actions Cache Persistence Checkpoint

Status: implemented

This checkpoint adds a GitHub-native persistence layer for `data/cache/` without changing the Python data pipeline.

GitHub-hosted runners are ephemeral. Without an explicit persistence layer, each Pages deployment starts from an empty filesystem and cold-fetches source data from public APIs. This checkpoint avoids that by restoring `data/cache/` from GitHub Actions cache before the site build and saving a new cache snapshot after a successful build.

## Scope

Included:

- one Actions cache for the entire `data/cache/` directory,
- manual-only Pages workflow,
- explicit `allow_cold_build` manual input,
- refusal to cold-build unless `allow_cold_build=true`,
- cache hit/miss logging,
- cache size logging before and after `build-site`,
- saving a new immutable cache key after a successful build,
- no Python source-code awareness of GitHub Actions cache.

Not included:

- dataset-level caches,
- automatic cache cleanup,
- scheduled refresh,
- deploy-on-push re-enable,
- external object storage,
- self-hosted runner support.

## Workflow Policy

Normal runs should use:

```text
allow_cold_build=false
```

If a data cache is restored, the workflow runs normal incremental updates and deploys the site. If no data cache is restored, the workflow fails before calling source APIs.

Bootstrap or repair runs may use:

```text
allow_cold_build=true
```

This is only for the first cache-enabled run or for an intentional cache repair. On a cache miss, this mode permits a full API cold build, saves the first or replacement `data/cache/` snapshot, and deploys the site.

## Cache Keys

The workflow uses one cache namespace:

```text
macro-observatory-data-cache-v1-${runner.os}-
```

Each successful run saves a unique immutable key:

```text
macro-observatory-data-cache-v1-${runner.os}-${github.run_id}
```

The next run restores the newest matching cache through the restore-key prefix. If GitHub restores a prefix match, the cache action reports `cache-hit=false` but also sets `cache-matched-key`. An empty `cache-hit` means no cache was restored.

## Why Single Cache First

Current cache size is small enough that a single `data/cache/` snapshot is simpler and more practical than dataset-level cache splitting.

Dataset-level caches remain a future optimization if restore/save time, cache size, or storage usage becomes a real issue.

## Observability

The workflow prints:

- `CACHE_HIT`,
- `CACHE_PRIMARY_KEY`,
- `CACHE_MATCHED_KEY`,
- `ALLOW_COLD_BUILD`,
- `data/cache` size before build when present,
- `build-site` duration,
- `data/cache` size after build,
- the normal storage report.

These logs should make cold builds visible and make cache restore/save performance measurable.

## Next Steps

After this checkpoint:

1. Manually run the Pages workflow once with `allow_cold_build=true` to bootstrap the first Actions cache snapshot.
2. Manually run it again with `allow_cold_build=false` to confirm the cache restores and the build is incremental.
3. If the cache behavior is reliable, consider re-enabling deploy-on-push.
4. After deploy-on-push is safe, design scheduled refresh workflows.
