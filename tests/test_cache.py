from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from macro_observatory.cache import load_cache, load_metadata, update_dataset
from macro_observatory.models import DatasetSpec


@dataclass
class FakeAdapter:
    frames: list[pd.DataFrame]
    starts: list[date | None]

    def fetch(self, start_date: date | None) -> pd.DataFrame:
        self.starts.append(start_date)
        return self.frames.pop(0)


def make_spec(tmp_path: Path, adapter: FakeAdapter) -> DatasetSpec:
    return DatasetSpec(
        id="test_dataset",
        title="Test Dataset",
        source_name="Test Source",
        adapter=adapter,
        date_column="date",
        primary_key=("date",),
        overlap_days=2,
        cache_path=tmp_path / "cache" / "sources" / "test_dataset.parquet",
        metadata_path=tmp_path / "cache" / "metadata" / "test_dataset.json",
        required_columns=("date", "value"),
        numeric_columns=("value",),
    )


def test_update_dataset_writes_cache_and_metadata(tmp_path: Path) -> None:
    adapter = FakeAdapter(
        frames=[pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "value": [1, 2]})],
        starts=[],
    )
    spec = make_spec(tmp_path, adapter)

    result = update_dataset(spec)

    assert result.rows_before == 0
    assert result.rows_fetched == 2
    assert result.rows_after == 2
    assert result.min_date == date(2024, 1, 1)
    assert result.max_date == date(2024, 1, 2)
    assert adapter.starts == [None]
    assert spec.cache_path.exists()
    assert spec.metadata_path.exists()

    cached = load_cache(spec)
    assert cached["value"].tolist() == [1, 2]

    metadata = load_metadata(spec)
    assert metadata is not None
    assert metadata.dataset_id == "test_dataset"
    assert metadata.row_count == 2
    assert metadata.min_date == date(2024, 1, 1)
    assert metadata.max_date == date(2024, 1, 2)


def test_update_dataset_uses_overlap_and_prefers_new_rows(tmp_path: Path) -> None:
    first_adapter = FakeAdapter(
        frames=[pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "value": [1, 2]})],
        starts=[],
    )
    first_spec = make_spec(tmp_path, first_adapter)
    update_dataset(first_spec)

    second_adapter = FakeAdapter(
        frames=[pd.DataFrame({"date": ["2024-01-02", "2024-01-03"], "value": [20, 3]})],
        starts=[],
    )
    second_spec = make_spec(tmp_path, second_adapter)

    result = update_dataset(second_spec)

    assert second_adapter.starts == [date(2023, 12, 31)]
    assert result.rows_before == 2
    assert result.rows_fetched == 2
    assert result.rows_after == 3

    cached = load_cache(second_spec)
    assert cached["date"].dt.date.tolist() == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    assert cached["value"].tolist() == [1, 20, 3]
