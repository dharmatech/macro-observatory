from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from macro_observatory.cache import load_cache, load_metadata, replace_dataset
from macro_observatory.data import load_dataset
from macro_observatory.derived import (
    MissingSourceCacheError,
    build_derived_dataset,
    derive_treasury_tga,
)
from macro_observatory.registry import get_dataset_spec


def operating_cash_balance_row(
    record_date: str,
    account_type: str,
    src_line_nbr: str,
    *,
    close_today_bal: str = "null",
    open_today_bal: str = "null",
) -> dict[str, str]:
    return {
        "record_date": record_date,
        "account_type": account_type,
        "close_today_bal": close_today_bal,
        "open_today_bal": open_today_bal,
        "open_month_bal": "1",
        "open_fiscal_year_bal": "2",
        "table_nbr": "I",
        "table_nm": "Operating Cash Balance",
        "sub_table_name": "Operating Cash Balance",
        "src_line_nbr": src_line_nbr,
        "record_fiscal_year": record_date[:4],
        "record_fiscal_quarter": "3",
        "record_calendar_year": record_date[:4],
        "record_calendar_quarter": "2",
        "record_calendar_month": record_date[5:7],
        "record_calendar_day": record_date[8:10],
    }


def test_derive_treasury_tga_covers_known_historical_account_type_eras() -> None:
    source_df = pd.DataFrame(
        [
            operating_cash_balance_row(
                "2021-09-30",
                "Federal Reserve Account",
                "1",
                close_today_bal="123",
            ),
            operating_cash_balance_row(
                "2021-10-01",
                "Treasury General Account (TGA)",
                "1",
                close_today_bal="456",
            ),
            operating_cash_balance_row(
                "2022-04-18",
                "Treasury General Account (TGA) Opening Balance",
                "1",
                open_today_bal="700",
            ),
            operating_cash_balance_row(
                "2022-04-18",
                "Treasury General Account (TGA) Closing Balance",
                "4",
                open_today_bal="789",
            ),
        ]
    )

    derived = derive_treasury_tga(source_df)

    assert derived["date"].dt.date.astype(str).tolist() == [
        "2021-09-30",
        "2021-10-01",
        "2022-04-18",
    ]
    assert derived["tga"].tolist() == [123, 456, 789]
    assert derived["source_account_type"].tolist() == [
        "Federal Reserve Account",
        "Treasury General Account (TGA)",
        "Treasury General Account (TGA) Closing Balance",
    ]
    assert derived["source_balance_field"].tolist() == [
        "close_today_bal",
        "close_today_bal",
        "open_today_bal",
    ]


def test_derive_treasury_tga_prefers_highest_priority_rule_for_duplicate_dates() -> None:
    source_df = pd.DataFrame(
        [
            operating_cash_balance_row(
                "2022-04-18",
                "Treasury General Account (TGA)",
                "1",
                close_today_bal="456",
            ),
            operating_cash_balance_row(
                "2022-04-18",
                "Treasury General Account (TGA) Closing Balance",
                "4",
                open_today_bal="789",
            ),
        ]
    )

    derived = derive_treasury_tga(source_df)

    assert len(derived) == 1
    assert derived.loc[0, "tga"] == 789
    assert derived.loc[0, "source_account_type"] == "Treasury General Account (TGA) Closing Balance"
    assert derived.loc[0, "source_balance_field"] == "open_today_bal"


def test_build_derived_treasury_tga_requires_source_cache(tmp_path: Path) -> None:
    with pytest.raises(MissingSourceCacheError) as exc_info:
        build_derived_dataset("treasury_tga", data_dir=tmp_path)

    assert "update treasury_dts_operating_cash_balance" in str(exc_info.value)


def test_build_derived_treasury_tga_writes_cache_and_metadata(tmp_path: Path) -> None:
    source_spec = get_dataset_spec("treasury_dts_operating_cash_balance", tmp_path)
    target_spec = get_dataset_spec("treasury_tga", tmp_path)
    source_df = pd.DataFrame(
        [
            operating_cash_balance_row(
                "2021-09-30",
                "Federal Reserve Account",
                "1",
                close_today_bal="123",
            ),
            operating_cash_balance_row(
                "2021-10-01",
                "Treasury General Account (TGA)",
                "1",
                close_today_bal="456",
            ),
        ]
    )
    replace_dataset(source_spec, source_df)

    result = build_derived_dataset("treasury_tga", data_dir=tmp_path)

    assert result.dataset_id == "treasury_tga"
    assert result.rows_before == 0
    assert result.rows_fetched == 2
    assert result.rows_after == 2
    assert target_spec.cache_path.exists()
    assert target_spec.metadata_path.exists()

    cached = load_cache(target_spec)
    assert cached["tga"].tolist() == [123, 456]
    assert cached["source_balance_field"].tolist() == ["close_today_bal", "close_today_bal"]

    loaded = load_dataset("treasury_tga", data_dir=tmp_path)
    assert loaded.equals(cached)

    metadata = load_metadata(target_spec)
    assert metadata is not None
    assert metadata.dataset_id == "treasury_tga"
    assert metadata.row_count == 2
    assert metadata.source_metadata is not None
    assert metadata.source_metadata["derived_from"] == ["treasury_dts_operating_cash_balance"]
    assert metadata.source_metadata["source_row_count"] == 2
    assert len(metadata.source_metadata["selection_rules"]) == 3
