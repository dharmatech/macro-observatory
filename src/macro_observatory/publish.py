"""Publish browser-facing static data artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

import pandas as pd

from macro_observatory.cache import load_cache, load_metadata
from macro_observatory.models import DatasetMetadata
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec
from macro_observatory.validation import require_columns

DEFAULT_SITE_DIR = Path("site")
ARTIFACT_SCHEMA_VERSION = 1
FED_NET_LIQUIDITY_DATASET_ID = "fed_net_liquidity"
FED_NET_LIQUIDITY_ARTIFACT_STEM = "fed-net-liquidity"
FED_NET_LIQUIDITY_COLUMNS = (
    "date",
    "walcl",
    "rrp",
    "tga",
    "rem",
    "fed_net_liquidity",
    "walcl_diff",
    "rrp_diff",
    "tga_diff",
    "rem_diff",
    "fed_net_liquidity_diff",
)
FED_NET_LIQUIDITY_SERIES: dict[str, dict[str, str]] = {
    "walcl": {"label": "WALCL", "units": "U.S. dollars", "role": "component"},
    "rrp": {"label": "RRP", "units": "U.S. dollars", "role": "component"},
    "tga": {"label": "TGA", "units": "U.S. dollars", "role": "component"},
    "rem": {"label": "REM", "units": "U.S. dollars", "role": "component"},
    "fed_net_liquidity": {
        "label": "Fed Net Liquidity",
        "units": "U.S. dollars",
        "role": "total",
    },
}


class PublishDatasetError(RuntimeError):
    """Raised when browser-facing artifacts cannot be published."""


@dataclass(frozen=True)
class PublishConfig:
    """Configuration for one browser-facing dataset artifact set."""

    dataset_id: str
    artifact_stem: str
    columns: tuple[str, ...]
    series: dict[str, dict[str, str]]


@dataclass(frozen=True)
class PublishResult:
    """Summary of a completed publish operation."""

    dataset_id: str
    rows_published: int
    min_date: date | None
    max_date: date | None
    output_dir: Path
    json_path: Path
    csv_path: Path
    metadata_path: Path


PUBLISH_CONFIGS = {
    FED_NET_LIQUIDITY_DATASET_ID: PublishConfig(
        dataset_id=FED_NET_LIQUIDITY_DATASET_ID,
        artifact_stem=FED_NET_LIQUIDITY_ARTIFACT_STEM,
        columns=FED_NET_LIQUIDITY_COLUMNS,
        series=FED_NET_LIQUIDITY_SERIES,
    )
}


def _get_publish_config(dataset_id: str) -> PublishConfig:
    try:
        return PUBLISH_CONFIGS[dataset_id]
    except KeyError as exc:
        known = ", ".join(sorted(PUBLISH_CONFIGS))
        raise PublishDatasetError(
            f"Dataset '{dataset_id}' does not have a publish config. "
            f"Known publishable datasets: {known}"
        ) from exc


def _date_or_none(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _build_command(dataset_id: str, kind: str) -> str:
    command = "build-derived" if kind == "derived" else "update"
    return f"uv run macro-observatory {command} {dataset_id}"


def _prepare_published_dataframe(df: pd.DataFrame, config: PublishConfig) -> pd.DataFrame:
    require_columns(df, config.columns)
    published = df.loc[:, list(config.columns)].copy()
    published["date"] = pd.to_datetime(published["date"], errors="raise").dt.strftime("%Y-%m-%d")
    return published


def _records_for_json(df: pd.DataFrame) -> list[dict[str, Any]]:
    json_safe = df.astype(object).where(pd.notna(df), None)
    return cast(list[dict[str, Any]], json_safe.to_dict(orient="records"))


def _write_json(path: Path, payload: Any, *, compact: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if compact:
            json.dump(payload, f, allow_nan=False, separators=(",", ":"))
        else:
            json.dump(payload, f, allow_nan=False, indent=2, sort_keys=True)
        f.write("\n")


def _metadata_payload(
    *,
    config: PublishConfig,
    metadata: DatasetMetadata,
    rows_published: int,
    json_path: Path,
    csv_path: Path,
    metadata_path: Path,
) -> dict[str, Any]:
    source_metadata = metadata.source_metadata or {}
    payload: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "dataset_id": metadata.dataset_id,
        "title": metadata.title,
        "source_name": metadata.source_name,
        "row_count": rows_published,
        "date_range": {
            "min": _date_or_none(metadata.min_date),
            "max": _date_or_none(metadata.max_date),
        },
        "dataset_built_at": metadata.last_successful_update.isoformat(),
        "columns": list(config.columns),
        "series": config.series,
        "source_units": metadata.source_units,
        "display_units": metadata.display_units,
        "source_dataset_ids": source_metadata.get("derived_from", []),
        "source_rows": source_metadata.get("source_rows", {}),
        "artifacts": {
            "json": json_path.name,
            "csv": csv_path.name,
            "metadata": metadata_path.name,
        },
    }
    for key in ("formula", "forward_fill_policy", "unit_policy"):
        if key in source_metadata:
            payload[key] = source_metadata[key]
    return payload


def publish_dataset(
    dataset_id: str,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    site_dir: Path = DEFAULT_SITE_DIR,
) -> PublishResult:
    """Publish compact browser-facing artifacts for one dataset."""
    config = _get_publish_config(dataset_id)
    spec = get_dataset_spec(dataset_id, data_dir)
    if not spec.cache_path.exists():
        raise PublishDatasetError(
            f"Missing cache for {dataset_id}. Run `{_build_command(dataset_id, spec.kind)}` first."
        )
    metadata = load_metadata(spec)
    if metadata is None:
        raise PublishDatasetError(
            f"Missing metadata for {dataset_id}. "
            f"Run `{_build_command(dataset_id, spec.kind)}` first."
        )

    df = load_cache(spec)
    published_df = _prepare_published_dataframe(df, config)
    output_dir = site_dir / "data"
    json_path = output_dir / f"{config.artifact_stem}.json"
    csv_path = output_dir / f"{config.artifact_stem}.csv"
    metadata_path = output_dir / f"{config.artifact_stem}-metadata.json"

    _write_json(json_path, _records_for_json(published_df), compact=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    published_df.to_csv(csv_path, index=False)
    _write_json(
        metadata_path,
        _metadata_payload(
            config=config,
            metadata=metadata,
            rows_published=len(published_df),
            json_path=json_path,
            csv_path=csv_path,
            metadata_path=metadata_path,
        ),
        compact=False,
    )

    return PublishResult(
        dataset_id=dataset_id,
        rows_published=len(published_df),
        min_date=metadata.min_date,
        max_date=metadata.max_date,
        output_dir=output_dir,
        json_path=json_path,
        csv_path=csv_path,
        metadata_path=metadata_path,
    )
