"""Dataset registry for the first implementation milestone."""

from __future__ import annotations

from pathlib import Path

from macro_observatory.models import DatasetSpec
from macro_observatory.sources.fred import FredSeriesAdapter
from macro_observatory.sources.nyfed import NyFedReverseRepoAdapter

DEFAULT_DATA_DIR = Path("data")
FRED_MILLIONS_USD = "millions of U.S. dollars"
US_DOLLARS = "U.S. dollars"


def _fred_series_spec(
    *,
    dataset_id: str,
    series_id: str,
    title: str,
    source_dir: Path,
    metadata_dir: Path,
    source_units: str = FRED_MILLIONS_USD,
    display_units: str = FRED_MILLIONS_USD,
) -> DatasetSpec:
    return DatasetSpec(
        id=dataset_id,
        title=title,
        source_name="FRED",
        adapter=FredSeriesAdapter(series_id),
        date_column="date",
        primary_key=("date",),
        overlap_days=14,
        cache_path=source_dir / f"{dataset_id}.parquet",
        metadata_path=metadata_dir / f"{dataset_id}.json",
        required_columns=("date", "value", "series_id"),
        numeric_columns=("value",),
        source_units=source_units,
        display_units=display_units,
    )


def _nyfed_rrp_spec(source_dir: Path, metadata_dir: Path) -> DatasetSpec:
    return DatasetSpec(
        id="nyfed_rrp",
        title="New York Fed Reverse Repo Operations (RRP)",
        source_name="New York Fed",
        adapter=NyFedReverseRepoAdapter(),
        date_column="operationDate",
        primary_key=("operationDate",),
        overlap_days=14,
        cache_path=source_dir / "nyfed_rrp.parquet",
        metadata_path=metadata_dir / "nyfed_rrp.json",
        required_columns=(
            "operationDate",
            "totalAmtAccepted",
            "operationId",
            "operationType",
            "note",
        ),
        numeric_columns=("totalAmtAccepted",),
        source_units=US_DOLLARS,
        display_units=US_DOLLARS,
    )


def build_registry(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, DatasetSpec]:
    cache_dir = data_dir / "cache"
    metadata_dir = cache_dir / "metadata"
    source_dir = cache_dir / "sources"

    specs = (
        _fred_series_spec(
            dataset_id="fred_walcl",
            series_id="WALCL",
            title="Federal Reserve Balance Sheet Assets (WALCL)",
            source_dir=source_dir,
            metadata_dir=metadata_dir,
        ),
        _fred_series_spec(
            dataset_id="fred_resppllopnww",
            series_id="RESPPLLOPNWW",
            title="Earnings Remittances Due to the U.S. Treasury (RESPPLLOPNWW)",
            source_dir=source_dir,
            metadata_dir=metadata_dir,
        ),
        _nyfed_rrp_spec(source_dir, metadata_dir),
    )
    return {spec.id: spec for spec in specs}


def get_dataset_spec(dataset_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> DatasetSpec:
    registry = build_registry(data_dir)
    try:
        return registry[dataset_id]
    except KeyError as exc:
        known = ", ".join(sorted(registry))
        raise KeyError(f"Unknown dataset '{dataset_id}'. Known datasets: {known}") from exc
