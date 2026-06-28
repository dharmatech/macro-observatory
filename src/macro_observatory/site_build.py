"""Build the generated static-site artifacts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from macro_observatory.cache import update_dataset
from macro_observatory.derived import build_derived_dataset
from macro_observatory.models import UpdateResult
from macro_observatory.publish import DEFAULT_SITE_DIR, PublishResult, publish_dataset
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec

SOURCE_DATASET_IDS = (
    "fred_walcl",
    "fred_resppllopnww",
    "nyfed_rrp",
    "treasury_dts_operating_cash_balance",
    "treasury_dts_deposits_withdrawals_operating_cash",
)
DERIVED_DATASET_IDS = (
    "treasury_tga",
    "treasury_dts_deposits_withdrawals_operating_cash_explorer",
    "fed_net_liquidity",
)
PUBLISH_DATASET_IDS = (
    "fed_net_liquidity",
    "treasury_dts_deposits_withdrawals_operating_cash_explorer",
)
SourceUpdateMode = Literal["update", "from-cache"]


class BuildSiteError(RuntimeError):
    """Raised when a static-site build cannot proceed."""


@dataclass(frozen=True)
class BuildSiteResult:
    """Summary of one static-site artifact build."""

    data_dir: Path
    site_dir: Path
    source_update_mode: SourceUpdateMode
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
            "Run `macro-observatory build-site` without `--from-cache` to refresh sources, "
            "or restore a valid data/cache snapshot first."
        )


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
) -> BuildSiteResult:
    """Build derived datasets and static-site artifacts, optionally updating source caches first."""
    source_results: tuple[UpdateResult, ...]
    if from_cache:
        _validate_source_cache(data_dir)
        source_update_mode: SourceUpdateMode = "from-cache"
        source_results = ()
    else:
        if require_fred_api_key:
            _require_fred_api_key()
        source_update_mode = "update"
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
        source_results=source_results,
        derived_results=derived_results,
        publish_results=publish_results,
        nojekyll_path=nojekyll_path,
    )
