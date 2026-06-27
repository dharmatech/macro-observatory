"""New York Fed source adapters."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol, cast

import pandas as pd
import requests

NYFED_RRP_COLUMNS = (
    "operationDate",
    "totalAmtAccepted",
    "operationId",
    "operationType",
    "note",
)


class HttpResponse(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> dict[str, Any]: ...


class HttpSession(Protocol):
    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        timeout: float,
    ) -> HttpResponse: ...


class NyFedReverseRepoAdapter:
    """Fetch New York Fed reverse repo operation amounts as a flat daily series."""

    api_url = "https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json"
    full_history_start = date(1900, 1, 1)

    def __init__(
        self,
        *,
        session: HttpSession | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.session = session or cast(HttpSession, requests.Session())
        self.timeout = timeout

    def fetch(self, start_date: date | None) -> pd.DataFrame:
        """Fetch reverse repo operation rows from the New York Fed Markets API."""
        query_start = start_date or self.full_history_start
        response = self.session.get(
            self.api_url,
            params={"startDate": query_start.isoformat()},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        operations = self._operations_from_payload(payload)
        if not operations:
            return pd.DataFrame(columns=NYFED_RRP_COLUMNS)

        df = pd.DataFrame(operations)
        missing = [column for column in NYFED_RRP_COLUMNS if column not in df.columns]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"New York Fed RRP response missing columns: {joined}")

        df = df.loc[:, list(NYFED_RRP_COLUMNS)].copy()
        df["note"] = df["note"].fillna("").astype(str)
        df["totalAmtAccepted"] = pd.to_numeric(df["totalAmtAccepted"], errors="coerce")
        df = self._drop_small_value_exercises(df)
        df = self._dedupe_operation_dates(df)
        return df.reset_index(drop=True)

    @staticmethod
    def _operations_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
        repo = payload.get("repo", {})
        operations = repo.get("operations", []) if isinstance(repo, dict) else []
        if operations is None:
            return []
        if not isinstance(operations, list):
            raise ValueError("New York Fed RRP response field repo.operations is not a list")
        return [operation for operation in operations if isinstance(operation, dict)]

    @staticmethod
    def _drop_small_value_exercises(df: pd.DataFrame) -> pd.DataFrame:
        notes = df["note"].fillna("").astype(str)
        is_small_value = notes.str.contains("small value exercise", case=False, regex=False)
        is_sve = notes.str.contains(r"\bSVE\b", case=False, regex=True)
        return df.loc[~(is_small_value | is_sve)].copy()

    @staticmethod
    def _dedupe_operation_dates(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        sorted_df = df.sort_values(
            ["operationDate", "totalAmtAccepted", "operationId"],
            ascending=[True, False, True],
        )
        deduped = sorted_df.drop_duplicates(subset=["operationDate"], keep="first")
        return deduped.sort_values("operationDate").reset_index(drop=True)
