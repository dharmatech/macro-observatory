"""Parquet cache and metadata update lifecycle."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd

from macro_observatory.models import DatasetMetadata, DatasetSpec, UpdateResult
from macro_observatory.validation import (
    normalize_date_column,
    normalize_numeric_columns,
    require_columns,
)


def _iso_or_none(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _date_from_value(value: Any) -> date | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date()


def _metadata_to_json(metadata: DatasetMetadata) -> dict[str, Any]:
    payload = asdict(metadata)
    payload["min_date"] = _iso_or_none(metadata.min_date)
    payload["max_date"] = _iso_or_none(metadata.max_date)
    payload["last_successful_update"] = metadata.last_successful_update.isoformat()
    payload["columns"] = list(metadata.columns)
    return payload


def _metadata_from_json(payload: dict[str, Any]) -> DatasetMetadata:
    min_date = date.fromisoformat(payload["min_date"]) if payload.get("min_date") else None
    max_date = date.fromisoformat(payload["max_date"]) if payload.get("max_date") else None
    return DatasetMetadata(
        dataset_id=str(payload["dataset_id"]),
        title=str(payload["title"]),
        source_name=str(payload["source_name"]),
        row_count=int(payload["row_count"]),
        min_date=min_date,
        max_date=max_date,
        last_successful_update=datetime.fromisoformat(str(payload["last_successful_update"])),
        overlap_days=int(payload["overlap_days"]),
        cache_path=str(payload["cache_path"]),
        columns=tuple(str(column) for column in payload["columns"]),
        source_units=payload.get("source_units"),
        display_units=payload.get("display_units"),
        source_metadata=payload.get("source_metadata"),
    )


def load_cache(spec: DatasetSpec) -> pd.DataFrame:
    """Load a dataset cache, returning an empty dataframe when absent."""
    if not spec.cache_path.exists():
        return pd.DataFrame(columns=spec.required_columns)
    df = pd.read_parquet(spec.cache_path)
    return _normalize_for_cache(spec, df)


def load_metadata(spec: DatasetSpec) -> DatasetMetadata | None:
    """Load dataset metadata when it exists."""
    if not spec.metadata_path.exists():
        return None
    with spec.metadata_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return _metadata_from_json(payload)


def _normalize_for_cache(spec: DatasetSpec, df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, spec.required_columns)
    result = normalize_date_column(df, spec.date_column)
    result = normalize_numeric_columns(result, spec.numeric_columns)
    return result


def _update_start_date(spec: DatasetSpec, existing: pd.DataFrame) -> date | None:
    if existing.empty:
        return None
    max_value = existing[spec.date_column].max()
    max_date = _date_from_value(max_value)
    if max_date is None:
        return None
    return max_date - timedelta(days=spec.overlap_days)


def _merge_rows(spec: DatasetSpec, existing: pd.DataFrame, fetched: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([existing, fetched], ignore_index=True)
    if combined.empty:
        return combined
    combined = combined.sort_values([spec.date_column, *spec.primary_key])
    combined = combined.drop_duplicates(subset=list(spec.primary_key), keep="last")
    combined = combined.sort_values(list(spec.primary_key)).reset_index(drop=True)
    return combined


def _write_cache(spec: DatasetSpec, df: pd.DataFrame) -> None:
    spec.cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(spec.cache_path, index=False)


def _adapter_source_metadata(adapter: object) -> dict[str, Any] | None:
    source_metadata = getattr(adapter, "source_metadata", None)
    if not callable(source_metadata):
        return None
    metadata = source_metadata()
    if metadata is None:
        return None
    return dict(metadata)


def _write_metadata(
    spec: DatasetSpec,
    df: pd.DataFrame,
    updated_at: datetime,
    source_metadata: dict[str, Any] | None,
) -> DatasetMetadata:
    if df.empty:
        min_date = None
        max_date = None
    else:
        min_date = _date_from_value(df[spec.date_column].min())
        max_date = _date_from_value(df[spec.date_column].max())

    metadata = DatasetMetadata(
        dataset_id=spec.id,
        title=spec.title,
        source_name=spec.source_name,
        row_count=len(df),
        min_date=min_date,
        max_date=max_date,
        last_successful_update=updated_at,
        overlap_days=spec.overlap_days,
        cache_path=str(spec.cache_path),
        columns=tuple(str(column) for column in df.columns),
        source_units=spec.source_units,
        display_units=spec.display_units,
        source_metadata=source_metadata,
    )
    spec.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with spec.metadata_path.open("w", encoding="utf-8") as f:
        json.dump(_metadata_to_json(metadata), f, indent=2)
        f.write("\n")
    return metadata


def replace_dataset(
    spec: DatasetSpec,
    df: pd.DataFrame,
    *,
    source_metadata: dict[str, Any] | None = None,
) -> UpdateResult:
    """Replace one cache with a fully built dataframe."""
    existing = load_cache(spec)
    normalized = _normalize_for_cache(spec, df)
    _write_cache(spec, normalized)
    updated_at = datetime.now(UTC)
    metadata = _write_metadata(spec, normalized, updated_at, source_metadata)
    return UpdateResult(
        dataset_id=spec.id,
        rows_before=len(existing),
        rows_fetched=len(normalized),
        rows_after=len(normalized),
        min_date=metadata.min_date,
        max_date=metadata.max_date,
        updated_at=updated_at,
        cache_path=spec.cache_path,
        metadata_path=spec.metadata_path,
    )


def update_dataset(spec: DatasetSpec) -> UpdateResult:
    """Run the shared incremental update lifecycle for ``spec``."""
    adapter = spec.adapter
    if adapter is None:
        raise ValueError(f"Dataset '{spec.id}' is derived. Use build-derived instead of update.")

    existing = load_cache(spec)
    start_date = _update_start_date(spec, existing)
    fetched = adapter.fetch(start_date)
    fetched = _normalize_for_cache(spec, fetched)
    merged = _merge_rows(spec, existing, fetched)
    _write_cache(spec, merged)
    updated_at = datetime.now(UTC)
    metadata = _write_metadata(spec, merged, updated_at, _adapter_source_metadata(adapter))
    return UpdateResult(
        dataset_id=spec.id,
        rows_before=len(existing),
        rows_fetched=len(fetched),
        rows_after=len(merged),
        min_date=metadata.min_date,
        max_date=metadata.max_date,
        updated_at=updated_at,
        cache_path=spec.cache_path,
        metadata_path=spec.metadata_path,
    )
