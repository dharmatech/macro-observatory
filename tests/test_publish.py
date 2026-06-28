from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from macro_observatory.cache import replace_dataset
from macro_observatory.derived import build_derived_dataset
from macro_observatory.publish import PublishDatasetError, publish_dataset
from macro_observatory.registry import get_dataset_spec
from macro_observatory.sources.treasury import TREASURY_AUCTIONS_QUERY_COLUMNS


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


def deposits_withdrawals_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "record_date": ["2024-01-02", "2024-01-02", "2024-01-03"],
            "account_type": [
                "Treasury General Account (TGA)",
                "Treasury General Account (TGA)",
                "Treasury General Account (TGA)",
            ],
            "transaction_type": ["Deposits", "Withdrawals", "Deposits"],
            "transaction_catg": [
                "Individual Income and Employment Taxes",
                "Education Department programs",
                "Sub-Total Deposits",
            ],
            "transaction_catg_desc": ["Taxes", "Education", "Subtotal"],
            "transaction_today_amt": ["100", "50", "999"],
            "transaction_mtd_amt": ["1000", "500", "999"],
            "transaction_fytd_amt": ["10000", "5000", "999"],
            "table_nbr": "II",
            "table_nm": "Deposits and Withdrawals of Operating Cash",
            "src_line_nbr": ["1", "2", "3"],
            "record_fiscal_year": "2024",
            "record_fiscal_quarter": "2",
            "record_calendar_year": "2024",
            "record_calendar_quarter": "1",
            "record_calendar_month": "01",
            "record_calendar_day": ["02", "02", "03"],
        }
    )


def write_tga_explorer_input(tmp_path: Path) -> None:
    replace_dataset(
        get_dataset_spec("treasury_dts_deposits_withdrawals_operating_cash", tmp_path),
        deposits_withdrawals_rows(),
        source_metadata={"endpoint_url": "https://example.test/deposits-withdrawals"},
    )


def auctions_query_row(
    record_date: str,
    cusip: str,
    *,
    security_type: str,
    issue_date: str,
    maturity_date: str,
    total_accepted: str,
    auction_date: str = "2024-01-01",
) -> dict[str, str]:
    row = {column: "null" for column in TREASURY_AUCTIONS_QUERY_COLUMNS}
    row.update(
        {
            "record_date": record_date,
            "cusip": cusip,
            "security_type": security_type,
            "auction_date": auction_date,
            "issue_date": issue_date,
            "maturity_date": maturity_date,
            "total_accepted": total_accepted,
        }
    )
    return row


def treasury_auctions_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            auctions_query_row(
                "2024-01-01",
                "A",
                security_type="Note",
                issue_date="2024-01-02",
                maturity_date="2024-01-07",
                total_accepted="100",
            ),
            auctions_query_row(
                "2024-01-01",
                "B",
                security_type="TIPS Note",
                issue_date="2024-01-02",
                maturity_date="2024-02-29",
                total_accepted="50",
            ),
            auctions_query_row(
                "2024-01-01",
                "C",
                security_type="CMB",
                issue_date="2024-01-31",
                maturity_date="2024-02-01",
                total_accepted="30",
            ),
            auctions_query_row(
                "2024-02-01",
                "D",
                security_type="Bond",
                issue_date="2024-02-15",
                maturity_date="2025-02-15",
                total_accepted="200",
            ),
            auctions_query_row(
                "2024-02-01",
                "E",
                security_type="FRN Note",
                issue_date="2024-02-15",
                maturity_date="2026-02-15",
                total_accepted="null",
            ),
        ]
    )


def write_treasury_securities_input(tmp_path: Path) -> None:
    replace_dataset(
        get_dataset_spec("treasury_od_auctions_query", tmp_path),
        treasury_auctions_rows(),
        source_metadata={"endpoint_url": "https://example.test/auctions"},
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

def test_publish_sp500_writes_market_context_artifacts(tmp_path: Path) -> None:
    replace_dataset(
        get_dataset_spec("fred_sp500", tmp_path),
        fred_rows("SP500", [("2024-01-02", 4700.1), ("2024-01-03", 4725.2)]),
        source_metadata={
            "series_id": "SP500",
            "source_url": "https://fred.stlouisfed.org/series/SP500",
        },
    )

    result = publish_dataset("fred_sp500", data_dir=tmp_path, site_dir=tmp_path / "site")

    assert result.dataset_id == "fred_sp500"
    assert result.rows_published == 2
    assert result.output_dir == tmp_path / "site" / "data"
    assert result.json_path == tmp_path / "site" / "data" / "sp500.json"
    assert result.csv_path == tmp_path / "site" / "data" / "sp500.csv"
    assert result.metadata_path == tmp_path / "site" / "data" / "sp500-metadata.json"

    with result.json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload == {
        "columns": ["date", "value"],
        "data": [["2024-01-02", 4700.1], ["2024-01-03", 4725.2]],
    }

    csv_df = pd.read_csv(result.csv_path)
    assert csv_df.columns.tolist() == ["date", "value"]
    assert csv_df.loc[1, "value"] == 4725.2

    with result.metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata["schema_version"] == 1
    assert metadata["dataset_id"] == "fred_sp500"
    assert metadata["row_count"] == 2
    assert metadata["date_range"] == {"min": "2024-01-02", "max": "2024-01-03"}
    assert metadata["json_orientation"] == "split"
    assert metadata["source_dataset_ids"] == ["fred_sp500"]
    assert metadata["series_id"] == "SP500"
    assert metadata["source_url"] == "https://fred.stlouisfed.org/series/SP500"
    assert metadata["series"]["value"]["role"] == "market_context"
    assert "not merged" in metadata["data_policy"]
    assert "copyright" in metadata["rights_note"]


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


def test_publish_treasury_securities_net_issuance_writes_browser_artifacts(
    tmp_path: Path,
) -> None:
    write_treasury_securities_input(tmp_path)
    build_derived_dataset("treasury_securities_net_issuance", data_dir=tmp_path)

    result = publish_dataset(
        "treasury_securities_net_issuance",
        data_dir=tmp_path,
        site_dir=tmp_path / "site",
    )

    assert result.dataset_id == "treasury_securities_net_issuance"
    assert result.output_dir == tmp_path / "site" / "data"
    assert result.json_path == tmp_path / "site" / "data" / "treasury-securities-net-issuance.json"
    assert result.csv_path == tmp_path / "site" / "data" / "treasury-securities-net-issuance.csv"
    assert (
        result.metadata_path
        == tmp_path / "site" / "data" / "treasury-securities-net-issuance-metadata.json"
    )

    with result.json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["columns"] == [
        "frequency",
        "date",
        "security_type",
        "issued",
        "maturing",
        "net_issuance",
    ]
    assert ["ME", "2024-01-01", "Note", 150.0, 100.0, 50.0] in payload["data"]
    assert ["ME", "2024-02-01", "Bill", 0.0, 30.0, -30.0] in payload["data"]
    assert ["YE", "2025-12-31", "Bond", 0.0, 200.0, -200.0] in payload["data"]

    csv_df = pd.read_csv(result.csv_path)
    assert csv_df.columns.tolist() == [
        "frequency",
        "date",
        "security_type",
        "issued",
        "maturing",
        "net_issuance",
    ]

    with result.metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata["schema_version"] == 1
    assert metadata["dataset_id"] == "treasury_securities_net_issuance"
    assert metadata["row_count"] == result.rows_published
    assert metadata["json_orientation"] == "split"
    assert metadata["source_dataset_ids"] == ["treasury_od_auctions_query"]
    assert metadata["source_endpoint"] == "https://example.test/auctions"
    assert metadata["source_cache_file"] == "treasury_od_auctions_query.parquet"
    assert metadata["source_row_count"] == 5
    assert metadata["valid_total_accepted_rows"] == 4
    assert metadata["null_total_accepted_rows"] == 1
    assert metadata["frequencies"] == ["D", "W", "ME", "QE", "YE"]
    assert metadata["default_frequency"] == "ME"
    assert metadata["security_types"] == ["Bill", "Bond", "Note"]
    assert metadata["primary_metric"] == "net_issuance"
    assert metadata["render_guardrail"] == {"max_points": 25000}
    assert metadata["series"]["net_issuance"]["label"] == "Net Issuance"
    assert "Future maturity dates" in metadata["future_maturity_policy"]


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


def test_publish_tga_explorer_requires_derived_cache(tmp_path: Path) -> None:
    with pytest.raises(PublishDatasetError) as exc_info:
        publish_dataset(
            "treasury_dts_deposits_withdrawals_operating_cash_explorer",
            data_dir=tmp_path,
            site_dir=tmp_path / "site",
        )

    assert "build-derived treasury_dts_deposits_withdrawals_operating_cash_explorer" in str(
        exc_info.value
    )


def test_publish_tga_explorer_writes_reduced_browser_artifacts(tmp_path: Path) -> None:
    write_tga_explorer_input(tmp_path)
    build_derived_dataset(
        "treasury_dts_deposits_withdrawals_operating_cash_explorer",
        data_dir=tmp_path,
    )

    result = publish_dataset(
        "treasury_dts_deposits_withdrawals_operating_cash_explorer",
        data_dir=tmp_path,
        site_dir=tmp_path / "site",
    )

    assert result.dataset_id == "treasury_dts_deposits_withdrawals_operating_cash_explorer"
    assert result.rows_published == 2
    assert result.output_dir == tmp_path / "site" / "data"
    assert result.json_path == tmp_path / "site" / "data" / "tga-explorer.json"
    assert result.csv_path == tmp_path / "site" / "data" / "tga-explorer.csv"
    assert result.metadata_path == tmp_path / "site" / "data" / "tga-explorer-metadata.json"

    with result.json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload == {
        "columns": [
            "record_date",
            "transaction_catg",
            "transaction_type",
            "transaction_today_amt",
            "transaction_mtd_amt",
            "transaction_fytd_amt",
        ],
        "data": [
            [
                "2024-01-02",
                "Individual Income and Employment Taxes",
                "Deposits",
                100,
                1000,
                10000,
            ],
            ["2024-01-02", "Education Department programs", "Withdrawals", 50, 500, 5000],
        ],
    }

    csv_df = pd.read_csv(result.csv_path)
    assert csv_df.columns.tolist() == [
        "record_date",
        "transaction_catg",
        "transaction_type",
        "transaction_today_amt",
        "transaction_mtd_amt",
        "transaction_fytd_amt",
    ]

    with result.metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata["schema_version"] == 1
    assert metadata["dataset_id"] == "treasury_dts_deposits_withdrawals_operating_cash_explorer"
    assert metadata["row_count"] == 2
    assert metadata["date_range"] == {"min": "2024-01-02", "max": "2024-01-02"}
    assert metadata["json_orientation"] == "split"
    assert metadata["source_dataset_ids"] == ["treasury_dts_deposits_withdrawals_operating_cash"]
    assert metadata["source_endpoint"] == "https://example.test/deposits-withdrawals"
    assert (
        metadata["source_cache_file"] == "treasury_dts_deposits_withdrawals_operating_cash.parquet"
    )
    assert metadata["source_row_count"] == 3
    assert metadata["category_count"] == 2
    assert metadata["transaction_types"] == ["Deposits", "Withdrawals"]
    assert metadata["render_guardrail"] == {"max_rows": 10000}
    assert metadata["series"]["transaction_fytd_amt"]["role"] == "metric"
    assert "Sub-Total Deposits" in metadata["excluded_categories"]
