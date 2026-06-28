from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from macro_observatory.cache import load_cache, load_metadata, update_dataset
from macro_observatory.models import DatasetSpec
from macro_observatory.registry import build_registry
from macro_observatory.sources.treasury import (
    TREASURY_AUCTIONS_QUERY_COLUMNS,
    TREASURY_AUCTIONS_QUERY_ENDPOINT,
    TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_COLUMNS,
    TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT,
    TREASURY_OPERATING_CASH_BALANCE_COLUMNS,
    TreasuryFiscalDataAdapter,
    auctions_query_adapter,
    deposits_withdrawals_operating_cash_adapter,
)


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


def deposits_withdrawals_row(
    record_date: str,
    transaction_type: str,
    transaction_catg: str,
    src_line_nbr: str,
    *,
    transaction_today_amt: str = "1",
    transaction_mtd_amt: str = "2",
    transaction_fytd_amt: str = "3",
) -> dict[str, str]:
    return {
        "record_date": record_date,
        "account_type": "Treasury General Account (TGA)",
        "transaction_type": transaction_type,
        "transaction_catg": transaction_catg,
        "transaction_catg_desc": transaction_catg,
        "transaction_today_amt": transaction_today_amt,
        "transaction_mtd_amt": transaction_mtd_amt,
        "transaction_fytd_amt": transaction_fytd_amt,
        "table_nbr": "II",
        "table_nm": "Deposits and Withdrawals of Operating Cash",
        "src_line_nbr": src_line_nbr,
        "record_fiscal_year": record_date[:4],
        "record_fiscal_quarter": "3",
        "record_calendar_year": record_date[:4],
        "record_calendar_quarter": "2",
        "record_calendar_month": record_date[5:7],
        "record_calendar_day": record_date[8:10],
    }


def auctions_row(
    record_date: str,
    cusip: str,
    *,
    security_type: str = "Note",
    auction_date: str = "2026-06-24",
    issue_date: str = "2026-06-30",
    maturity_date: str = "2036-06-30",
    total_accepted: str = "2401000000",
) -> dict[str, str]:
    row = {column: "null" for column in TREASURY_AUCTIONS_QUERY_COLUMNS}
    row.update(
        {
            "record_date": record_date,
            "cusip": cusip,
            "security_type": security_type,
            "security_term": "10-Year",
            "auction_date": auction_date,
            "issue_date": issue_date,
            "maturity_date": maturity_date,
            "total_accepted": total_accepted,
        }
    )
    return row


def fiscal_payload_for_columns(
    rows: list[dict[str, str]],
    columns: tuple[str, ...],
    *,
    total_pages: int,
    next_link: str | None = None,
) -> dict[str, Any]:
    labels = {column: column.replace("_", " ").title() for column in columns}
    data_types = {column: "STRING" for column in columns}
    data_types["record_date"] = "DATE"
    data_formats = {column: "String" for column in columns}
    data_formats["record_date"] = "YYYY-MM-DD"
    for column in (
        "close_today_bal",
        "open_today_bal",
        "transaction_today_amt",
        "transaction_mtd_amt",
        "transaction_fytd_amt",
    ):
        if column in data_types:
            data_types[column] = "CURRENCY0"
            data_formats[column] = "$1,000,000"
    if "total_accepted" in data_types:
        data_types["total_accepted"] = "NUMBER"
        data_formats["total_accepted"] = "10.2"
    return {
        "data": rows,
        "meta": {
            "count": len(rows),
            "labels": labels,
            "dataTypes": data_types,
            "dataFormats": data_formats,
            "total-count": len(rows),
            "total-pages": total_pages,
        },
        "links": {"next": next_link},
    }


def fiscal_payload(
    rows: list[dict[str, str]],
    *,
    total_pages: int,
    next_link: str | None = None,
) -> dict[str, Any]:
    labels = {
        column: column.replace("_", " ").title()
        for column in TREASURY_OPERATING_CASH_BALANCE_COLUMNS
    }
    data_types = {column: "STRING" for column in TREASURY_OPERATING_CASH_BALANCE_COLUMNS}
    data_types["record_date"] = "DATE"
    data_types["close_today_bal"] = "CURRENCY0"
    data_types["open_today_bal"] = "CURRENCY0"
    data_formats = {column: "String" for column in TREASURY_OPERATING_CASH_BALANCE_COLUMNS}
    data_formats["record_date"] = "YYYY-MM-DD"
    data_formats["close_today_bal"] = "$1,000,000"
    data_formats["open_today_bal"] = "$1,000,000"
    return {
        "data": rows,
        "meta": {
            "count": len(rows),
            "labels": labels,
            "dataTypes": data_types,
            "dataFormats": data_formats,
            "total-count": len(rows),
            "total-pages": total_pages,
        },
        "links": {"next": next_link},
    }


@dataclass
class FakeResponse:
    payload: dict[str, Any]

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


@dataclass
class FakeSession:
    responses: list[dict[str, Any]]
    calls: list[dict[str, Any]]

    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self.responses.pop(0))


@dataclass
class FakeAdapter:
    frames: list[pd.DataFrame]
    starts: list[date | None]
    metadata: dict[str, Any] | None = None

    def fetch(self, start_date: date | None) -> pd.DataFrame:
        self.starts.append(start_date)
        return self.frames.pop(0)

    def source_metadata(self) -> dict[str, Any] | None:
        return self.metadata


def treasury_spec(tmp_path: Path, adapter: FakeAdapter) -> DatasetSpec:
    spec = build_registry(tmp_path)["treasury_dts_operating_cash_balance"]
    return replace(spec, adapter=adapter)


def treasury_auctions_spec(tmp_path: Path, adapter: FakeAdapter) -> DatasetSpec:
    spec = build_registry(tmp_path)["treasury_od_auctions_query"]
    return replace(spec, adapter=adapter)


def test_treasury_fiscal_data_fetch_paginates_and_captures_schema_metadata() -> None:
    row_1 = operating_cash_balance_row(
        "2026-06-24", "Treasury General Account (TGA) Opening Balance", "1"
    )
    row_2 = operating_cash_balance_row(
        "2026-06-24", "Treasury General Account (TGA) Closing Balance", "4"
    )
    session = FakeSession(
        responses=[
            fiscal_payload(
                [row_1], total_pages=2, next_link="&page%5Bnumber%5D=2&page%5Bsize%5D=1"
            ),
            fiscal_payload([row_2], total_pages=2),
        ],
        calls=[],
    )
    adapter = TreasuryFiscalDataAdapter(
        "https://example.test/operating_cash_balance",
        session=session,
        timeout=12.0,
        page_size=1,
    )

    df = adapter.fetch(date(2026, 6, 20))

    assert [call["params"]["page[number]"] for call in session.calls] == ["1", "2"]
    assert session.calls[0] == {
        "url": "https://example.test/operating_cash_balance",
        "params": {
            "filter": "record_date:gte:2026-06-20",
            "sort": "record_date,src_line_nbr",
            "page[number]": "1",
            "page[size]": "1",
        },
        "timeout": 12.0,
    }
    assert tuple(df.columns) == TREASURY_OPERATING_CASH_BALANCE_COLUMNS
    assert df["account_type"].tolist() == [
        "Treasury General Account (TGA) Opening Balance",
        "Treasury General Account (TGA) Closing Balance",
    ]

    metadata = adapter.source_metadata()
    assert metadata is not None
    assert metadata["endpoint_url"] == "https://example.test/operating_cash_balance"
    assert metadata["query_start_date"] == "2026-06-20"
    assert metadata["pages_fetched"] == 2
    assert metadata["rows_fetched"] == 2
    assert metadata["fiscal_data_meta"]["dataFormats"]["open_today_bal"] == "$1,000,000"


def test_treasury_operating_cash_balance_cache_normalizes_numeric_fields(tmp_path: Path) -> None:
    row = operating_cash_balance_row(
        "2026-06-25",
        "Treasury General Account (TGA) Closing Balance",
        "4",
        close_today_bal="null",
        open_today_bal="871469",
    )
    adapter = FakeAdapter(
        frames=[pd.DataFrame([row])],
        starts=[],
        metadata={"fiscal_data_meta": {"dataFormats": {"open_today_bal": "$1,000,000"}}},
    )
    spec = treasury_spec(tmp_path, adapter)

    update_dataset(spec)

    cached = load_cache(spec)
    assert cached["record_date"].dt.date.tolist() == [date(2026, 6, 25)]
    assert pd.isna(cached.loc[0, "close_today_bal"])
    assert cached.loc[0, "open_today_bal"] == 871469
    assert cached.loc[0, "src_line_nbr"] == 4

    metadata = load_metadata(spec)
    assert metadata is not None
    assert metadata.source_metadata == {
        "fiscal_data_meta": {"dataFormats": {"open_today_bal": "$1,000,000"}}
    }


def test_treasury_operating_cash_balance_cache_uses_overlap_and_primary_key(tmp_path: Path) -> None:
    first_adapter = FakeAdapter(
        frames=[
            pd.DataFrame(
                [
                    operating_cash_balance_row(
                        "2026-06-24",
                        "Treasury General Account (TGA) Closing Balance",
                        "4",
                        open_today_bal="901845",
                    ),
                    operating_cash_balance_row(
                        "2026-06-25",
                        "Treasury General Account (TGA) Closing Balance",
                        "4",
                        open_today_bal="871469",
                    ),
                ]
            )
        ],
        starts=[],
    )
    update_dataset(treasury_spec(tmp_path, first_adapter))

    second_adapter = FakeAdapter(
        frames=[
            pd.DataFrame(
                [
                    operating_cash_balance_row(
                        "2026-06-25",
                        "Treasury General Account (TGA) Closing Balance",
                        "4",
                        open_today_bal="870000",
                    ),
                    operating_cash_balance_row(
                        "2026-06-26",
                        "Treasury General Account (TGA) Closing Balance",
                        "4",
                        open_today_bal="880000",
                    ),
                ]
            )
        ],
        starts=[],
    )
    spec = treasury_spec(tmp_path, second_adapter)

    result = update_dataset(spec)

    assert second_adapter.starts == [date(2026, 6, 11)]
    assert result.rows_before == 2
    assert result.rows_fetched == 2
    assert result.rows_after == 3

    cached = load_cache(spec)
    assert cached["record_date"].dt.date.tolist() == [
        date(2026, 6, 24),
        date(2026, 6, 25),
        date(2026, 6, 26),
    ]
    assert cached["open_today_bal"].tolist() == [901845, 870000, 880000]


def test_treasury_deposits_withdrawals_adapter_uses_endpoint_and_schema() -> None:
    row = deposits_withdrawals_row(
        "2026-06-25",
        "Deposits",
        "Individual Income and Employment Taxes",
        "10",
    )
    session = FakeSession(
        responses=[
            fiscal_payload_for_columns(
                [row],
                TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_COLUMNS,
                total_pages=1,
            )
        ],
        calls=[],
    )
    adapter = deposits_withdrawals_operating_cash_adapter(
        session=session, timeout=9.0, page_size=50
    )

    df = adapter.fetch(date(2026, 6, 20))

    assert session.calls == [
        {
            "url": TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT,
            "params": {
                "filter": "record_date:gte:2026-06-20",
                "sort": "record_date,src_line_nbr",
                "page[number]": "1",
                "page[size]": "50",
            },
            "timeout": 9.0,
        }
    ]
    assert tuple(df.columns) == TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_COLUMNS
    assert df.loc[0, "transaction_catg"] == "Individual Income and Employment Taxes"

    metadata = adapter.source_metadata()
    assert metadata is not None
    assert metadata["endpoint_url"] == TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT
    assert metadata["rows_fetched"] == 1
    assert metadata["fiscal_data_meta"]["dataFormats"]["transaction_today_amt"] == "$1,000,000"


def test_treasury_auctions_query_adapter_uses_endpoint_schema_and_sort() -> None:
    row = auctions_row(
        "1979-11-15",
        "912827KC5",
        auction_date="1979-10-31",
        issue_date="1979-11-15",
        maturity_date="1989-11-15",
    )
    session = FakeSession(
        responses=[
            fiscal_payload_for_columns([row], TREASURY_AUCTIONS_QUERY_COLUMNS, total_pages=1)
        ],
        calls=[],
    )
    adapter = auctions_query_adapter(session=session, timeout=9.0, page_size=50)

    df = adapter.fetch(date(1979, 11, 1))

    assert session.calls == [
        {
            "url": TREASURY_AUCTIONS_QUERY_ENDPOINT,
            "params": {
                "filter": "record_date:gte:1979-11-01",
                "sort": "record_date,cusip,auction_date,issue_date,maturity_date",
                "page[number]": "1",
                "page[size]": "50",
            },
            "timeout": 9.0,
        }
    ]
    assert tuple(df.columns) == TREASURY_AUCTIONS_QUERY_COLUMNS
    assert df.loc[0, "cusip"] == "912827KC5"

    metadata = adapter.source_metadata()
    assert metadata is not None
    assert metadata["endpoint_url"] == TREASURY_AUCTIONS_QUERY_ENDPOINT
    assert metadata["rows_fetched"] == 1
    assert metadata["fiscal_data_meta"]["dataFormats"]["total_accepted"] == "10.2"


def test_treasury_auctions_query_cache_normalizes_total_accepted(tmp_path: Path) -> None:
    adapter = FakeAdapter(
        frames=[
            pd.DataFrame(
                [
                    auctions_row(
                        "1979-11-15",
                        "912827KC5",
                        auction_date="1979-10-31",
                        issue_date="1979-11-15",
                        maturity_date="1989-11-15",
                        total_accepted="2401000000",
                    )
                ]
            )
        ],
        starts=[],
        metadata={"fiscal_data_meta": {"dataFormats": {"total_accepted": "10.2"}}},
    )
    spec = treasury_auctions_spec(tmp_path, adapter)

    update_dataset(spec)

    cached = load_cache(spec)
    assert cached["record_date"].dt.date.tolist() == [date(1979, 11, 15)]
    assert cached.loc[0, "cusip"] == "912827KC5"
    assert cached.loc[0, "auction_date"] == "1979-10-31"
    assert cached.loc[0, "issue_date"] == "1979-11-15"
    assert cached.loc[0, "maturity_date"] == "1989-11-15"
    assert cached.loc[0, "total_accepted"] == 2401000000

    metadata = load_metadata(spec)
    assert metadata is not None
    assert metadata.source_units == "U.S. dollars"
    assert metadata.source_metadata == {
        "fiscal_data_meta": {"dataFormats": {"total_accepted": "10.2"}}
    }
