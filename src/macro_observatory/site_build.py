"""Build the generated static-site artifacts."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from macro_observatory.cache import update_dataset
from macro_observatory.derived import build_derived_dataset
from macro_observatory.models import DatasetSpec, UpdateResult
from macro_observatory.publish import DEFAULT_SITE_DIR, PublishResult, publish_dataset
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec

SOURCE_DATASET_IDS = (
    "fred_walcl",
    "fred_resppllopnww",
    "nyfed_rrp",
    "treasury_dts_operating_cash_balance",
    "treasury_dts_deposits_withdrawals_operating_cash",
    "treasury_od_auctions_query",
)
DERIVED_DATASET_IDS = (
    "treasury_tga",
    "treasury_dts_deposits_withdrawals_operating_cash_explorer",
    "treasury_securities_net_issuance",
    "fed_net_liquidity",
)
PUBLISH_DATASET_IDS = (
    "fed_net_liquidity",
    "treasury_dts_deposits_withdrawals_operating_cash_explorer",
    "treasury_securities_net_issuance",
)
SourceUpdateMode = Literal["update", "targeted", "from-cache"]


class BuildSiteError(RuntimeError):
    """Raised when a static-site build cannot proceed."""


@dataclass(frozen=True)
class BuildSiteResult:
    """Summary of one static-site artifact build."""

    data_dir: Path
    site_dir: Path
    source_update_mode: SourceUpdateMode
    source_dataset_ids: tuple[str, ...]
    source_results: tuple[UpdateResult, ...]
    derived_results: tuple[UpdateResult, ...]
    publish_results: tuple[PublishResult, ...]
    nojekyll_path: Path


def _require_fred_api_key() -> None:
    if not os.getenv("FRED_API_KEY"):
        raise BuildSiteError(
            "FRED_API_KEY is required for this site build. "
            "Configure it as a local environment variable or GitHub Actions repository secret."
        )


def _known_source_dataset_ids() -> str:
    return ", ".join(SOURCE_DATASET_IDS)


def _validate_source_cache(data_dir: Path) -> None:
    missing_paths: list[Path] = []
    for dataset_id in SOURCE_DATASET_IDS:
        spec = get_dataset_spec(dataset_id, data_dir)
        for path in (spec.cache_path, spec.metadata_path):
            if not path.exists():
                missing_paths.append(path)

    if missing_paths:
        missing = "\n".join(f"- {path}" for path in missing_paths)
        raise BuildSiteError(
            "Cannot build from cache because required source cache files are missing:\n"
            f"{missing}\n"
            "Run `macro-observatory build-site` without cache-only or targeted options "
            "to refresh sources intentionally, or restore a valid data/cache snapshot first."
        )


def _deduplicate_source_dataset_ids(source_dataset_ids: Sequence[str]) -> tuple[str, ...]:
    unique_dataset_ids: list[str] = []
    seen: set[str] = set()
    for dataset_id in source_dataset_ids:
        if dataset_id in seen:
            continue
        unique_dataset_ids.append(dataset_id)
        seen.add(dataset_id)
    return tuple(unique_dataset_ids)


def _target_source_specs(
    source_dataset_ids: Sequence[str], data_dir: Path
) -> tuple[DatasetSpec, ...]:
    specs: list[DatasetSpec] = []
    for dataset_id in _deduplicate_source_dataset_ids(source_dataset_ids):
        try:
            spec = get_dataset_spec(dataset_id, data_dir)
        except KeyError as exc:
            raise BuildSiteError(
                f"Unknown source dataset '{dataset_id}'. "
                f"Known static-site source datasets: {_known_source_dataset_ids()}."
            ) from exc

        if spec.kind != "source":
            raise BuildSiteError(
                f"Dataset '{dataset_id}' is derived. "
                "`--source-dataset` accepts only source datasets."
            )

        if dataset_id not in SOURCE_DATASET_IDS:
            raise BuildSiteError(
                f"Dataset '{dataset_id}' is not part of the current static-site source pipeline. "
                f"Known static-site source datasets: {_known_source_dataset_ids()}."
            )

        specs.append(spec)
    return tuple(specs)


def _write_nojekyll(site_dir: Path) -> Path:
    path = site_dir / ".nojekyll"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def build_static_site(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    site_dir: Path = DEFAULT_SITE_DIR,
    require_fred_api_key: bool = False,
    from_cache: bool = False,
    source_dataset_ids: Sequence[str] = (),
) -> BuildSiteResult:
    """Build derived datasets and static-site artifacts, optionally updating source caches first."""
    if from_cache and source_dataset_ids:
        raise BuildSiteError(
            "`--from-cache` cannot be combined with `--source-dataset`. "
            "Use one source update mode per build."
        )

    source_results: tuple[UpdateResult, ...]
    if from_cache:
        _validate_source_cache(data_dir)
        source_update_mode: SourceUpdateMode = "from-cache"
        selected_source_dataset_ids: tuple[str, ...] = ()
        source_results = ()
    elif source_dataset_ids:
        target_specs = _target_source_specs(source_dataset_ids, data_dir)
        _validate_source_cache(data_dir)
        if require_fred_api_key:
            _require_fred_api_key()
        source_update_mode = "targeted"
        selected_source_dataset_ids = tuple(spec.id for spec in target_specs)
        source_results = tuple(update_dataset(spec) for spec in target_specs)
    else:
        if require_fred_api_key:
            _require_fred_api_key()
        source_update_mode = "update"
        selected_source_dataset_ids = SOURCE_DATASET_IDS
        source_results = tuple(
            update_dataset(get_dataset_spec(dataset_id, data_dir))
            for dataset_id in SOURCE_DATASET_IDS
        )

    derived_results = tuple(
        build_derived_dataset(dataset_id, data_dir=data_dir) for dataset_id in DERIVED_DATASET_IDS
    )
    publish_results = tuple(
        publish_dataset(dataset_id, data_dir=data_dir, site_dir=site_dir)
        for dataset_id in PUBLISH_DATASET_IDS
    )
    nojekyll_path = _write_nojekyll(site_dir)

    return BuildSiteResult(
        data_dir=data_dir,
        site_dir=site_dir,
        source_update_mode=source_update_mode,
        source_dataset_ids=selected_source_dataset_ids,
        source_results=source_results,
        derived_results=derived_results,
        publish_results=publish_results,
        nojekyll_path=nojekyll_path,
    )
