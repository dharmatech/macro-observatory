"""Dataset registry for the first implementation milestone."""

from __future__ import annotations

from pathlib import Path

from macro_observatory.models import DatasetSpec
from macro_observatory.sources.fred import FredSeriesAdapter

DEFAULT_DATA_DIR = Path("data")


def build_registry(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, DatasetSpec]:
    cache_dir = data_dir / "cache"
    metadata_dir = cache_dir / "metadata"
    source_dir = cache_dir / "sources"

    fred_walcl = DatasetSpec(
        id="fred_walcl",
        title="Federal Reserve Balance Sheet Assets (WALCL)",
        source_name="FRED",
        adapter=FredSeriesAdapter("WALCL"),
        date_column="date",
        primary_key=("date",),
        overlap_days=14,
        cache_path=source_dir / "fred_walcl.parquet",
        metadata_path=metadata_dir / "fred_walcl.json",
        required_columns=("date", "value", "series_id"),
        numeric_columns=("value",),
        source_units="millions of U.S. dollars",
        display_units="millions of U.S. dollars",
    )
    return {fred_walcl.id: fred_walcl}


def get_dataset_spec(dataset_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> DatasetSpec:
    registry = build_registry(data_dir)
    try:
        return registry[dataset_id]
    except KeyError as exc:
        known = ", ".join(sorted(registry))
        raise KeyError(f"Unknown dataset '{dataset_id}'. Known datasets: {known}") from exc

