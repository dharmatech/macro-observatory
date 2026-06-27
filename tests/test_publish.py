from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from macro_observatory.cache import replace_dataset
from macro_observatory.derived import build_derived_dataset
from macro_observatory.publish import PublishDatasetError, publish_dataset
from macro_observatory.registry import get_dataset_spec


def fred_rows(series_id: str, rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [date for date, _ in rows],
            "value": [value for _, value in rows],
            "series_id": series_id,
        }
    )


def rrp_rows(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "operationDate": [date for date, _ in rows],
            "totalAmtAccepted": [value for _, value in rows],
            "operationId": [f"operation-{index}" for index, _ in enumerate(rows)],
            "operationType": "Reverse Repo",
            "note": "",
        }
    )


def tga_rows(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [date for date, _ in rows],
            "tga": [value for _, value in rows],
            "source_account_type": "Treasury General Account (TGA) Closing Balance",
            "source_balance_field": "open_today_bal",
        }
    )


def write_fed_net_liquidity_inputs(tmp_path: Path) -> None:
    replace_dataset(
        get_dataset_spec("fred_walcl", tmp_path),
        fred_rows("WALCL", [("2024-01-01", 10), ("2024-01-08", 12)]),
    )
    replace_dataset(
        get_dataset_spec("fred_resppllopnww", tmp_path),
        fred_rows("RESPPLLOPNWW", [("2024-01-01", 1), ("2024-01-08", 2)]),
    )
    replace_dataset(
        get_dataset_spec("nyfed_rrp", tmp_path),
        rrp_rows([("2024-01-01", 100), ("2024-01-02", 200), ("2024-01-08", 300)]),
    )
    replace_dataset(
        get_dataset_spec("treasury_tga", tmp_path),
        tga_rows([("2024-01-02", 3), ("2024-01-08", 4)]),
    )


def test_publish_fed_net_liquidity_requires_derived_cache(tmp_path: Path) -> None:
    with pytest.raises(PublishDatasetError) as exc_info:
        publish_dataset("fed_net_liquidity", data_dir=tmp_path, site_dir=tmp_path / "site")

    assert "build-derived fed_net_liquidity" in str(exc_info.value)


def test_publish_rejects_dataset_without_publish_config(tmp_path: Path) -> None:
    with pytest.raises(PublishDatasetError) as exc_info:
        publish_dataset("fred_walcl", data_dir=tmp_path, site_dir=tmp_path / "site")

    assert "does not have a publish config" in str(exc_info.value)
    assert "fed_net_liquidity" in str(exc_info.value)


def test_publish_fed_net_liquidity_writes_browser_artifacts(tmp_path: Path) -> None:
    write_fed_net_liquidity_inputs(tmp_path)
    build_derived_dataset("fed_net_liquidity", data_dir=tmp_path)

    result = publish_dataset("fed_net_liquidity", data_dir=tmp_path, site_dir=tmp_path / "site")

    assert result.dataset_id == "fed_net_liquidity"
    assert result.rows_published == 3
    assert result.output_dir == tmp_path / "site" / "data"
    assert result.json_path == tmp_path / "site" / "data" / "fed-net-liquidity.json"
    assert result.csv_path == tmp_path / "site" / "data" / "fed-net-liquidity.csv"
    assert result.metadata_path == tmp_path / "site" / "data" / "fed-net-liquidity-metadata.json"

    with result.json_path.open("r", encoding="utf-8") as f:
        records = json.load(f)
    assert records[0]["date"] == "2024-01-01"
    assert records[0]["tga"] is None
    assert records[1]["fed_net_liquidity"] == 5_999_800
    assert records[2]["fed_net_liquidity_diff"] == -100

    csv_df = pd.read_csv(result.csv_path)
    assert csv_df.columns.tolist() == [
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
    ]
    assert csv_df.loc[1, "fed_net_liquidity"] == 5_999_800

    with result.metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata["schema_version"] == 1
    assert metadata["dataset_id"] == "fed_net_liquidity"
    assert metadata["row_count"] == 3
    assert metadata["date_range"] == {"min": "2024-01-01", "max": "2024-01-08"}
    assert metadata["formula"] == "fed_net_liquidity = walcl - rrp - tga - rem"
    assert metadata["source_dataset_ids"] == [
        "fred_walcl",
        "fred_resppllopnww",
        "nyfed_rrp",
        "treasury_tga",
    ]
    assert metadata["series"]["fed_net_liquidity"]["label"] == "Fed Net Liquidity"
    assert "cache_path" not in metadata


def test_publish_fed_net_liquidity_is_deterministic_for_same_cache(tmp_path: Path) -> None:
    write_fed_net_liquidity_inputs(tmp_path)
    build_derived_dataset("fed_net_liquidity", data_dir=tmp_path)
    first = publish_dataset("fed_net_liquidity", data_dir=tmp_path, site_dir=tmp_path / "site")
    first_json = first.json_path.read_bytes()
    first_csv = first.csv_path.read_bytes()
    first_metadata = first.metadata_path.read_bytes()

    second = publish_dataset("fed_net_liquidity", data_dir=tmp_path, site_dir=tmp_path / "site")

    assert second.json_path.read_bytes() == first_json
    assert second.csv_path.read_bytes() == first_csv
    assert second.metadata_path.read_bytes() == first_metadata
