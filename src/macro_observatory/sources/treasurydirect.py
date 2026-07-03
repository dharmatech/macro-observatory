"""TreasuryDirect TA_WS source adapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol, cast

import pandas as pd
import requests

TREASURYDIRECT_SECURITIES_SEARCH_URL = "https://www.treasurydirect.gov/TA_WS/securities/search"
TREASURYDIRECT_QUERY_MODES = ("issueDate", "maturityDate", "auctionDate")
DEFAULT_TREASURYDIRECT_LOOKBACK_DAYS = 7
DEFAULT_TREASURYDIRECT_LOOKAHEAD_DAYS = 38
TREASURYDIRECT_REQUIRED_FIELDS = (
    "cusip",
    "securityType",
    "type",
    "auctionDate",
    "issueDate",
    "maturityDate",
    "totalAccepted",
    "offeringAmount",
    "somaTendered",
)
TREASURYDIRECT_PROVENANCE_COLUMNS = (
    "query_mode",
    "query_start_date",
    "query_end_date",
    "query_date",
    "retrieved_at",
    "is_current_window",
)
TREASURYDIRECT_SECURITIES_CURRENT_REQUIRED_COLUMNS = (
    *TREASURYDIRECT_PROVENANCE_COLUMNS,
    *TREASURYDIRECT_REQUIRED_FIELDS,
)
TREASURYDIRECT_AMOUNT_COLUMNS = ("totalAccepted", "offeringAmount", "somaTendered")


class HttpResponse(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...


class HttpSession(Protocol):
    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        timeout: float,
    ) -> HttpResponse: ...


@dataclass(frozen=True)
class TreasuryDirectCurrentWindow:
    """Concrete date window used for one TreasuryDirect current refresh."""

    as_of_date: date
    start_date: date
    end_date: date
    lookback_days: int
    lookahead_days: int


class TreasuryDirectSecuritiesCurrentWindowAdapter:
    """Fetch the current rolling TreasuryDirect securities window.

    This adapter intentionally performs a full fresh fetch of a bounded window
    each time. TreasuryDirect rows can be provisional while auctions and issue
    dates are still upcoming, so this source is replace-on-refresh rather than
    historical/incremental.
    """

    def __init__(
        self,
        *,
        lookback_days: int = DEFAULT_TREASURYDIRECT_LOOKBACK_DAYS,
        lookahead_days: int = DEFAULT_TREASURYDIRECT_LOOKAHEAD_DAYS,
        as_of_date: date | None = None,
        session: HttpSession | None = None,
        timeout: float = 30.0,
    ) -> None:
        if lookback_days < 0:
            raise ValueError("lookback_days must be non-negative")
        if lookahead_days < 0:
            raise ValueError("lookahead_days must be non-negative")
        self.lookback_days = lookback_days
        self.lookahead_days = lookahead_days
        self.as_of_date = as_of_date
        self.session = session or cast(HttpSession, requests.Session())
        self.timeout = timeout
        self._last_source_metadata: dict[str, Any] | None = None

    def fetch(self, start_date: date | None) -> pd.DataFrame:
        """Fetch current rows; ``start_date`` is ignored for protocol compatibility."""
        del start_date
        return self.fetch_current_window()

    def fetch_current_window(self) -> pd.DataFrame:
        """Fetch issue, maturity, and auction window rows with provenance."""
        window = self._current_window()
        retrieved_at = datetime.now(UTC).isoformat()
        frames: list[pd.DataFrame] = []
        row_counts_by_query_mode: dict[str, int] = {}

        for query_mode in TREASURYDIRECT_QUERY_MODES:
            rows = self._fetch_query(query_mode, window)
            row_counts_by_query_mode[query_mode] = len(rows)
            frames.append(self._dataframe_from_rows(rows, query_mode, window, retrieved_at))

        if frames:
            df = pd.concat(frames, ignore_index=True, sort=False)
        else:
            df = pd.DataFrame(columns=TREASURYDIRECT_SECURITIES_CURRENT_REQUIRED_COLUMNS)

        ordered_columns = [
            *TREASURYDIRECT_PROVENANCE_COLUMNS,
            *[column for column in TREASURYDIRECT_REQUIRED_FIELDS if column in df.columns],
        ]
        extra_columns = [column for column in df.columns if column not in ordered_columns]
        df = df.loc[:, [*ordered_columns, *extra_columns]].copy()

        self._last_source_metadata = self._build_source_metadata(
            window=window,
            retrieved_at=retrieved_at,
            row_counts_by_query_mode=row_counts_by_query_mode,
            rows_fetched=len(df),
        )
        return df

    def source_metadata(self) -> dict[str, Any] | None:
        """Return metadata captured during the most recent fetch."""
        if self._last_source_metadata is None:
            return None
        return dict(self._last_source_metadata)

    def _current_window(self) -> TreasuryDirectCurrentWindow:
        as_of = self.as_of_date or date.today()
        return TreasuryDirectCurrentWindow(
            as_of_date=as_of,
            start_date=as_of - timedelta(days=self.lookback_days),
            end_date=as_of + timedelta(days=self.lookahead_days),
            lookback_days=self.lookback_days,
            lookahead_days=self.lookahead_days,
        )

    def _fetch_query(
        self,
        query_mode: str,
        window: TreasuryDirectCurrentWindow,
    ) -> list[dict[str, Any]]:
        params = {
            query_mode: f"{window.start_date.isoformat()},{window.end_date.isoformat()}",
            "format": "json",
        }
        response = self.session.get(
            TREASURYDIRECT_SECURITIES_SEARCH_URL,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return self._rows_from_payload(payload, query_mode)

    def _rows_from_payload(self, payload: Any, query_mode: str) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            raise ValueError("TreasuryDirect securities response is not a JSON array")
        rows: list[dict[str, Any]] = []
        for row in payload:
            if not isinstance(row, dict):
                raise ValueError("TreasuryDirect securities response contains non-object rows")
            cast_row = cast(dict[str, Any], row)
            self._require_row_fields(cast_row, query_mode)
            rows.append(cast_row)
        return rows

    @staticmethod
    def _require_row_fields(row: dict[str, Any], query_mode: str) -> None:
        required = (*TREASURYDIRECT_REQUIRED_FIELDS, query_mode)
        missing = [field for field in required if field not in row]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"TreasuryDirect securities row is missing required fields: {joined}")

    @staticmethod
    def _query_date(row: dict[str, Any], query_mode: str) -> str:
        value = row.get(query_mode)
        if value is None:
            raise ValueError(f"TreasuryDirect securities row has null {query_mode}")
        return str(value)[:10]

    def _dataframe_from_rows(
        self,
        rows: Sequence[dict[str, Any]],
        query_mode: str,
        window: TreasuryDirectCurrentWindow,
        retrieved_at: str,
    ) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=TREASURYDIRECT_SECURITIES_CURRENT_REQUIRED_COLUMNS)

        enriched_rows: list[dict[str, Any]] = []
        for row in rows:
            enriched_rows.append(
                {
                    "query_mode": query_mode,
                    "query_start_date": window.start_date.isoformat(),
                    "query_end_date": window.end_date.isoformat(),
                    "query_date": self._query_date(row, query_mode),
                    "retrieved_at": retrieved_at,
                    "is_current_window": True,
                    **row,
                }
            )
        return pd.DataFrame(enriched_rows)

    @staticmethod
    def _build_source_metadata(
        *,
        window: TreasuryDirectCurrentWindow,
        retrieved_at: str,
        row_counts_by_query_mode: dict[str, int],
        rows_fetched: int,
    ) -> dict[str, Any]:
        return {
            "endpoint_url": TREASURYDIRECT_SECURITIES_SEARCH_URL,
            "query_modes": list(TREASURYDIRECT_QUERY_MODES),
            "window_start_date": window.start_date.isoformat(),
            "window_end_date": window.end_date.isoformat(),
            "as_of_date": window.as_of_date.isoformat(),
            "lookback_days": window.lookback_days,
            "lookahead_days": window.lookahead_days,
            "retrieved_at": retrieved_at,
            "rows_fetched": rows_fetched,
            "row_counts_by_query_mode": row_counts_by_query_mode,
            "required_fields": list(TREASURYDIRECT_REQUIRED_FIELDS),
        }


def treasurydirect_securities_current_adapter(
    *,
    lookback_days: int = DEFAULT_TREASURYDIRECT_LOOKBACK_DAYS,
    lookahead_days: int = DEFAULT_TREASURYDIRECT_LOOKAHEAD_DAYS,
    as_of_date: date | None = None,
    session: HttpSession | None = None,
    timeout: float = 30.0,
) -> TreasuryDirectSecuritiesCurrentWindowAdapter:
    """Build the adapter for the current TreasuryDirect securities window."""
    return TreasuryDirectSecuritiesCurrentWindowAdapter(
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
        as_of_date=as_of_date,
        session=session,
        timeout=timeout,
    )
