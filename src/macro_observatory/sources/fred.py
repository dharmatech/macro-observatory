"""FRED source adapter."""

from __future__ import annotations

import os
from datetime import date
from io import StringIO
from typing import Any

import pandas as pd
import requests


class FredSeriesAdapter:
    """Fetch one FRED series as a normalized dataframe."""

    api_url = "https://api.stlouisfed.org/fred/series/observations"
    csv_url = "https://fred.stlouisfed.org/graph/fredgraph.csv"

    def __init__(
        self,
        series_id: str,
        *,
        api_key: str | None = None,
        session: requests.Session | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.series_id = series_id
        self.api_key = api_key if api_key is not None else os.getenv("FRED_API_KEY")
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch(self, start_date: date | None) -> pd.DataFrame:
        """Fetch series observations from FRED.

        When ``FRED_API_KEY`` is configured, the official FRED API is used. If
        no key is available, the public CSV endpoint is used as a fallback.
        """
        if self.api_key:
            return self._fetch_api(start_date)
        return self._fetch_csv(start_date)

    def _fetch_api(self, start_date: date | None) -> pd.DataFrame:
        params: dict[str, Any] = {
            "series_id": self.series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": 100000,
        }
        if start_date is not None:
            params["observation_start"] = start_date.isoformat()

        response = self.session.get(self.api_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        observations = payload.get("observations", [])
        df = pd.DataFrame(observations)
        if df.empty:
            return pd.DataFrame(columns=["date", "value", "series_id"])
        df = df[["date", "value"]].copy()
        df["series_id"] = self.series_id
        df["value"] = pd.to_numeric(df["value"].replace(".", pd.NA), errors="coerce")
        return df

    def _fetch_csv(self, start_date: date | None) -> pd.DataFrame:
        response = self.session.get(
            self.csv_url,
            params={"id": self.series_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        value_column = self.series_id
        df = df.rename(columns={"observation_date": "date", value_column: "value"})
        df = df[["date", "value"]].copy()
        df["series_id"] = self.series_id
        df["value"] = pd.to_numeric(df["value"].replace(".", pd.NA), errors="coerce")
        if start_date is not None:
            df = df[pd.to_datetime(df["date"]).dt.date >= start_date]
        return df.reset_index(drop=True)
