"""Core typed models for datasets and update results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

import pandas as pd

DatasetKind = Literal["source", "derived"]


class SourceAdapter(Protocol):
    """Protocol implemented by API-specific source adapters."""

    def fetch(self, start_date: date | None) -> pd.DataFrame:
        """Fetch source rows starting at ``start_date`` when supported."""


class SourceMetadataProvider(Protocol):
    """Optional protocol for adapters that expose source response metadata."""

    def source_metadata(self) -> dict[str, Any] | None:
        """Return metadata captured during the most recent fetch."""


@dataclass(frozen=True)
class DatasetSpec:
    """Configuration for one cacheable dataset."""

    id: str
    title: str
    source_name: str
    adapter: SourceAdapter | None
    date_column: str
    primary_key: tuple[str, ...]
    overlap_days: int
    cache_path: Path
    metadata_path: Path
    required_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...] = ()
    source_units: str | None = None
    display_units: str | None = None
    kind: DatasetKind = "source"


@dataclass(frozen=True)
class DatasetMetadata:
    """Metadata written next to a cached dataset."""

    dataset_id: str
    title: str
    source_name: str
    row_count: int
    min_date: date | None
    max_date: date | None
    last_successful_update: datetime
    overlap_days: int
    cache_path: str
    columns: tuple[str, ...]
    source_units: str | None = None
    display_units: str | None = None
    source_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpdateResult:
    """Summary of a completed dataset update."""

    dataset_id: str
    rows_before: int
    rows_fetched: int
    rows_after: int
    min_date: date | None
    max_date: date | None
    updated_at: datetime
    cache_path: Path
    metadata_path: Path
