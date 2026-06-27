from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from macro_observatory.sources.nyfed import NYFED_RRP_COLUMNS, NyFedReverseRepoAdapter


@dataclass
class FakeResponse:
    payload: dict[str, Any]

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


@dataclass
class FakeSession:
    payload: dict[str, Any]
    calls: list[dict[str, Any]]

    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self.payload)


def test_nyfed_rrp_fetch_filters_sve_and_keeps_highest_amount_per_date() -> None:
    payload = {
        "repo": {
            "operations": [
                {
                    "operationId": "RP 051526 27",
                    "operationDate": "2026-05-15",
                    "operationType": "Reverse Repo",
                    "note": "",
                    "totalAmtAccepted": 647000000,
                },
                {
                    "operationId": "RP 051326 99",
                    "operationDate": "2026-05-13",
                    "operationType": "Reverse Repo",
                    "note": "This operation is a Small Value Exercise (SVE)",
                    "totalAmtAccepted": 110000000,
                },
                {
                    "operationId": "RP 051326 26",
                    "operationDate": "2026-05-13",
                    "operationType": "Reverse Repo",
                    "note": "",
                    "totalAmtAccepted": 3609000000,
                },
                {
                    "operationId": "RP 051426 01",
                    "operationDate": "2026-05-14",
                    "operationType": "Reverse Repo",
                    "note": "",
                    "totalAmtAccepted": 100,
                },
                {
                    "operationId": "RP 051426 02",
                    "operationDate": "2026-05-14",
                    "operationType": "Reverse Repo",
                    "note": "",
                    "totalAmtAccepted": 200,
                },
            ]
        }
    }
    session = FakeSession(payload=payload, calls=[])
    adapter = NyFedReverseRepoAdapter(session=session, timeout=12.0)

    df = adapter.fetch(date(2026, 5, 10))

    assert session.calls == [
        {
            "url": NyFedReverseRepoAdapter.api_url,
            "params": {"startDate": "2026-05-10"},
            "timeout": 12.0,
        }
    ]
    assert tuple(df.columns) == NYFED_RRP_COLUMNS
    assert df["operationDate"].tolist() == ["2026-05-13", "2026-05-14", "2026-05-15"]
    assert df["operationId"].tolist() == ["RP 051326 26", "RP 051426 02", "RP 051526 27"]
    assert df["totalAmtAccepted"].tolist() == [3609000000, 200, 647000000]


def test_nyfed_rrp_fetch_uses_full_history_start_for_cold_cache() -> None:
    session = FakeSession(payload={"repo": {"operations": []}}, calls=[])
    adapter = NyFedReverseRepoAdapter(session=session)

    df = adapter.fetch(None)

    assert session.calls[0]["params"] == {"startDate": "1900-01-01"}
    assert tuple(df.columns) == NYFED_RRP_COLUMNS
    assert df.empty
