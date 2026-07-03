from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from macro_observatory import cli
from macro_observatory.cache import load_cache, load_metadata, update_dataset
from macro_observatory.models import DatasetSpec
from macro_observatory.registry import build_registry
from macro_observatory.sources.treasurydirect import (
    TREASURYDIRECT_SECURITIES_SEARCH_URL,
    TreasuryDirectSecuritiesCurrentWindowAdapter,
)


def security_row(
    cusip: str,
    *,
    security_type: str = "Bill",
    issue_date: str = "2026-07-02T00:00:00",
    maturity_date: str = "2026-08-06T00:00:00",
    auction_date: str = "2026-06-30T00:00:00",
    total_accepted: str = "1000000000",
    offering_amount: str = "2000000000",
    soma_tendered: str = "300000000",
) -> dict[str, Any]:
    return {
        "cusip": cusip,
        "securityType": security_type,
        "type": security_type,
        "securityTerm": "4-Week",
        "auctionDate": auction_date,
        "issueDate": issue_date,
        "maturityDate": maturity_date,
        "totalAccepted": total_accepted,
        "offeringAmount": offering_amount,
        "somaTendered": soma_tendered,
    }


@dataclass
class FakeResponse:
    payload: Any

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


@dataclass
class FakeSession:
    responses: list[Any]
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
class FakeCurrentWindowAdapter:
    df: pd.DataFrame
    metadata: dict[str, Any]
    lookback_days: int
    lookahead_days: int

    def fetch_current_window(self) -> pd.DataFrame:
        return self.df

    def source_metadata(self) -> dict[str, Any]:
        return self.metadata


def test_treasurydirect_current_window_fetches_three_query_modes() -> None:
    session = FakeSession(
        responses=[
            [security_row("912797AB1", issue_date="2026-07-02T00:00:00")],
            [security_row("912797AB2", maturity_date="2026-07-03T00:00:00")],
            [security_row("912797AB3", auction_date="2026-07-01T00:00:00")],
        ],
        calls=[],
    )
    adapter = TreasuryDirectSecuritiesCurrentWindowAdapter(
        lookback_days=7,
        lookahead_days=38,
        as_of_date=date(2026, 7, 3),
        session=session,
        timeout=12.0,
    )

    df = adapter.fetch_current_window()

    assert [call["url"] for call in session.calls] == [TREASURYDIRECT_SECURITIES_SEARCH_URL] * 3
    assert [call["params"] for call in session.calls] == [
        {"issueDate": "2026-06-26,2026-08-10", "format": "json"},
        {"maturityDate": "2026-06-26,2026-08-10", "format": "json"},
        {"auctionDate": "2026-06-26,2026-08-10", "format": "json"},
    ]
    assert [call["timeout"] for call in session.calls] == [12.0, 12.0, 12.0]
    assert df["query_mode"].tolist() == ["issueDate", "maturityDate", "auctionDate"]
    assert df["query_start_date"].tolist() == ["2026-06-26"] * 3
    assert df["query_end_date"].tolist() == ["2026-08-10"] * 3
    assert df["query_date"].tolist() == ["2026-07-02", "2026-07-03", "2026-07-01"]
    assert df["is_current_window"].tolist() == [True, True, True]

    metadata = adapter.source_metadata()
    assert metadata is not None
    assert metadata["endpoint_url"] == TREASURYDIRECT_SECURITIES_SEARCH_URL
    assert metadata["window_start_date"] == "2026-06-26"
    assert metadata["window_end_date"] == "2026-08-10"
    assert metadata["lookback_days"] == 7
    assert metadata["lookahead_days"] == 38
    assert metadata["row_counts_by_query_mode"] == {
        "issueDate": 1,
        "maturityDate": 1,
        "auctionDate": 1,
    }


def test_treasurydirect_current_window_rejects_missing_required_fields() -> None:
    row = security_row("912797AB1")
    del row["somaTendered"]
    session = FakeSession(responses=[[row]], calls=[])
    adapter = TreasuryDirectSecuritiesCurrentWindowAdapter(
        as_of_date=date(2026, 7, 3),
        session=session,
    )

    with pytest.raises(ValueError, match="somaTendered"):
        adapter.fetch_current_window()


def test_treasurydirect_registry_spec(tmp_path: Path) -> None:
    spec = build_registry(tmp_path)["treasurydirect_securities_current"]

    assert spec.title == "TreasuryDirect Securities Current Window"
    assert spec.source_name == "TreasuryDirect TA_WS"
    assert isinstance(spec.adapter, TreasuryDirectSecuritiesCurrentWindowAdapter)
    assert spec.date_column == "query_date"
    assert spec.update_strategy == "replace"
    assert (
        spec.cache_path
        == tmp_path / "cache" / "sources" / "treasurydirect_securities_current.parquet"
    )
    assert (
        spec.metadata_path
        == tmp_path / "cache" / "metadata" / "treasurydirect_securities_current.json"
    )
    assert "somaTendered" in spec.required_columns
    assert spec.numeric_columns == ("totalAccepted", "offeringAmount", "somaTendered")


def test_treasurydirect_replace_update_rewrites_current_window(tmp_path: Path) -> None:
    first_spec = build_registry(tmp_path)["treasurydirect_securities_current"]
    first_adapter = TreasuryDirectSecuritiesCurrentWindowAdapter(
        as_of_date=date(2026, 7, 3),
        session=FakeSession(responses=[[security_row("OLD1")], [], []], calls=[]),
    )
    first_spec = DatasetSpec(**{**first_spec.__dict__, "adapter": first_adapter})
    update_dataset(first_spec)

    second_spec = build_registry(tmp_path)["treasurydirect_securities_current"]
    second_adapter = TreasuryDirectSecuritiesCurrentWindowAdapter(
        as_of_date=date(2026, 7, 4),
        session=FakeSession(responses=[[security_row("NEW1")], [], []], calls=[]),
    )
    second_spec = DatasetSpec(**{**second_spec.__dict__, "adapter": second_adapter})

    result = update_dataset(second_spec)

    assert result.rows_before == 1
    assert result.rows_fetched == 1
    assert result.rows_after == 1
    cached = load_cache(second_spec)
    assert cached["cusip"].tolist() == ["NEW1"]
    assert cached["query_date"].dt.date.tolist() == [date(2026, 7, 2)]
    assert cached.loc[0, "totalAccepted"] == 1_000_000_000

    metadata = load_metadata(second_spec)
    assert metadata is not None
    assert metadata.source_metadata is not None
    assert metadata.source_metadata["as_of_date"] == "2026-07-04"


def test_refresh_current_cli_uses_window_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, int]] = []

    def fake_adapter_factory(
        *, lookback_days: int, lookahead_days: int
    ) -> FakeCurrentWindowAdapter:
        calls.append({"lookback_days": lookback_days, "lookahead_days": lookahead_days})
        return FakeCurrentWindowAdapter(
            df=pd.DataFrame(
                [
                    {
                        "query_mode": "issueDate",
                        "query_start_date": "2026-06-26",
                        "query_end_date": "2026-08-10",
                        "query_date": "2026-07-02",
                        "retrieved_at": "2026-07-03T12:00:00+00:00",
                        "is_current_window": True,
                        **security_row("912797AB1"),
                    }
                ]
            ),
            metadata={"lookback_days": lookback_days, "lookahead_days": lookahead_days},
            lookback_days=lookback_days,
            lookahead_days=lookahead_days,
        )

    monkeypatch.setattr(cli, "treasurydirect_securities_current_adapter", fake_adapter_factory)

    exit_code = cli.main(
        [
            "--data-dir",
            str(tmp_path / "data"),
            "refresh-current",
            "treasurydirect_securities_current",
            "--lookback-days",
            "10",
            "--lookahead-days",
            "42",
        ]
    )

    assert exit_code == 0
    assert calls == [{"lookback_days": 10, "lookahead_days": 42}]
    output = capsys.readouterr().out
    assert "refreshed treasurydirect_securities_current" in output
    cached = load_cache(build_registry(tmp_path / "data")["treasurydirect_securities_current"])
    assert cached["cusip"].tolist() == ["912797AB1"]
