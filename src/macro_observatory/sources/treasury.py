"""Treasury Fiscal Data source adapters."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol, cast

import pandas as pd
import requests

TREASURY_FISCAL_SERVICE_BASE_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
)

TREASURY_OPERATING_CASH_BALANCE_ENDPOINT = (
    f"{TREASURY_FISCAL_SERVICE_BASE_URL}v1/accounting/dts/operating_cash_balance"
)

TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT = (
    f"{TREASURY_FISCAL_SERVICE_BASE_URL}v1/accounting/dts/deposits_withdrawals_operating_cash"
)

TREASURY_AUCTIONS_QUERY_ENDPOINT = (
    f"{TREASURY_FISCAL_SERVICE_BASE_URL}v1/accounting/od/auctions_query"
)

TREASURY_OPERATING_CASH_BALANCE_COLUMNS = (
    "record_date",
    "account_type",
    "close_today_bal",
    "open_today_bal",
    "open_month_bal",
    "open_fiscal_year_bal",
    "table_nbr",
    "table_nm",
    "sub_table_name",
    "src_line_nbr",
    "record_fiscal_year",
    "record_fiscal_quarter",
    "record_calendar_year",
    "record_calendar_quarter",
    "record_calendar_month",
    "record_calendar_day",
)

TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_COLUMNS = (
    "record_date",
    "account_type",
    "transaction_type",
    "transaction_catg",
    "transaction_catg_desc",
    "transaction_today_amt",
    "transaction_mtd_amt",
    "transaction_fytd_amt",
    "table_nbr",
    "table_nm",
    "src_line_nbr",
    "record_fiscal_year",
    "record_fiscal_quarter",
    "record_calendar_year",
    "record_calendar_quarter",
    "record_calendar_month",
    "record_calendar_day",
)


TREASURY_AUCTIONS_QUERY_COLUMNS = (
    "record_date",
    "cusip",
    "security_type",
    "security_term",
    "auction_date",
    "issue_date",
    "maturity_date",
    "price_per100",
    "accrued_int_per100",
    "accrued_int_per1000",
    "adj_accrued_int_per1000",
    "adj_price",
    "allocation_pctage",
    "allocation_pctage_decimals",
    "announcemtd_cusip",
    "announcemt_date",
    "auction_format",
    "avg_med_discnt_rate",
    "avg_med_investment_rate",
    "avg_med_price",
    "avg_med_discnt_margin",
    "avg_med_yield",
    "back_dated",
    "back_dated_date",
    "bid_to_cover_ratio",
    "callable",
    "call_date",
    "called_date",
    "cash_management_bill_cmb",
    "closing_time_comp",
    "closing_time_noncomp",
    "comp_accepted",
    "comp_bid_decimals",
    "comp_tendered",
    "comp_tenders_accepted",
    "corpus_cusip",
    "cpi_base_reference_period",
    "currently_outstanding",
    "dated_date",
    "direct_bidder_accepted",
    "direct_bidder_tendered",
    "est_pub_held_mat_by_type_amt",
    "fima_included",
    "fima_noncomp_accepted",
    "fima_noncomp_tendered",
    "first_int_period",
    "first_int_payment_date",
    "floating_rate",
    "frn_index_determination_date",
    "frn_index_determination_rate",
    "high_discnt_rate",
    "high_investment_rate",
    "high_price",
    "high_discnt_margin",
    "high_yield",
    "index_ratio_on_issue_date",
    "indirect_bidder_accepted",
    "indirect_bidder_tendered",
    "int_payment_frequency",
    "int_rate",
    "low_discnt_rate",
    "low_investment_rate",
    "low_price",
    "low_discnt_margin",
    "low_yield",
    "mat_date",
    "max_comp_award",
    "max_noncomp_award",
    "max_single_bid",
    "min_bid_amt",
    "min_strip_amt",
    "min_to_issue",
    "multiples_to_bid",
    "multiples_to_issue",
    "nlp_exclusion_amt",
    "nlp_reporting_threshold",
    "noncomp_accepted",
    "noncomp_tenders_accepted",
    "offering_amt",
    "original_cusip",
    "original_dated_date",
    "original_issue_date",
    "original_security_term",
    "pdf_filenm_announcemt",
    "pdf_filenm_comp_results",
    "pdf_filenm_noncomp_results",
    "primary_dealer_accepted",
    "primary_dealer_tendered",
    "ref_cpi_on_dated_date",
    "ref_cpi_on_issue_date",
    "reopening",
    "security_term_day_month",
    "security_term_week_year",
    "series",
    "soma_accepted",
    "soma_holdings",
    "soma_included",
    "soma_tendered",
    "spread",
    "std_int_payment_per1000",
    "strippable",
    "tiin_conversion_factor_per1000",
    "total_accepted",
    "total_tendered",
    "treas_retail_accepted",
    "treas_retail_tenders_accepted",
    "unadj_accrued_int_per1000",
    "unadj_price",
    "xml_filenm_announcemt",
    "xml_filenm_comp_results",
    "inflation_index_security",
    "tint_cusip_1",
    "tint_cusip_2",
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


class TreasuryFiscalDataAdapter:
    """Fetch all rows for a Treasury Fiscal Data endpoint with pagination."""

    full_history_start = date(1900, 1, 1)

    def __init__(
        self,
        endpoint_url: str,
        *,
        date_field: str = "record_date",
        page_size: int = 10000,
        sort: str = "record_date,src_line_nbr",
        session: HttpSession | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.date_field = date_field
        self.page_size = page_size
        self.sort = sort
        self.session = session or cast(HttpSession, requests.Session())
        self.timeout = timeout
        self._last_source_metadata: dict[str, Any] | None = None

    def fetch(self, start_date: date | None) -> pd.DataFrame:
        """Fetch endpoint rows whose date field is greater than or equal to start_date."""
        query_start = start_date or self.full_history_start
        rows: list[dict[str, Any]] = []
        first_meta: dict[str, Any] = {}
        page_number = 1
        pages_fetched = 0

        while True:
            payload = self._fetch_page(query_start, page_number)
            meta = self._meta_from_payload(payload)
            if page_number == 1:
                first_meta = meta

            page_rows = self._rows_from_payload(payload)
            rows.extend(page_rows)
            pages_fetched += 1

            total_pages = self._total_pages(meta)
            if total_pages is not None:
                if page_number >= total_pages:
                    break
            elif self._next_link(payload) is None:
                break

            page_number += 1

        self._last_source_metadata = self._build_source_metadata(
            query_start=query_start,
            pages_fetched=pages_fetched,
            rows_fetched=len(rows),
            meta=first_meta,
        )
        return self._dataframe_from_rows(rows, first_meta)

    def source_metadata(self) -> dict[str, Any] | None:
        """Return Fiscal Data metadata captured during the most recent fetch."""
        if self._last_source_metadata is None:
            return None
        return dict(self._last_source_metadata)

    def _fetch_page(self, query_start: date, page_number: int) -> dict[str, Any]:
        response = self.session.get(
            self.endpoint_url,
            params={
                "filter": f"{self.date_field}:gte:{query_start.isoformat()}",
                "sort": self.sort,
                "page[number]": str(page_number),
                "page[size]": str(self.page_size),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise ValueError("Treasury Fiscal Data response field data is not a list")
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError("Treasury Fiscal Data response data contains non-object rows")
        return [cast(dict[str, Any], row) for row in rows]

    @staticmethod
    def _meta_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
        meta = payload.get("meta", {})
        if not isinstance(meta, dict):
            raise ValueError("Treasury Fiscal Data response field meta is not an object")
        return cast(dict[str, Any], meta)

    @staticmethod
    def _total_pages(meta: dict[str, Any]) -> int | None:
        value = meta.get("total-pages")
        if value is None:
            return None
        return int(value)

    @staticmethod
    def _next_link(payload: dict[str, Any]) -> str | None:
        links = payload.get("links", {})
        if not isinstance(links, dict):
            return None
        value = links.get("next")
        return str(value) if value is not None else None

    @staticmethod
    def _columns_from_meta(meta: dict[str, Any]) -> list[str]:
        labels = meta.get("labels", {})
        if isinstance(labels, dict):
            return [str(column) for column in labels]
        data_types = meta.get("dataTypes", {})
        if isinstance(data_types, dict):
            return [str(column) for column in data_types]
        return []

    def _dataframe_from_rows(
        self, rows: list[dict[str, Any]], meta: dict[str, Any]
    ) -> pd.DataFrame:
        columns = self._columns_from_meta(meta)
        if not rows:
            return pd.DataFrame(columns=columns)

        df = pd.DataFrame(rows)
        ordered_columns = [column for column in columns if column in df.columns]
        extra_columns = [column for column in df.columns if column not in ordered_columns]
        if ordered_columns:
            return df.loc[:, [*ordered_columns, *extra_columns]].copy()
        return df

    def _build_source_metadata(
        self,
        *,
        query_start: date,
        pages_fetched: int,
        rows_fetched: int,
        meta: dict[str, Any],
    ) -> dict[str, Any]:
        fiscal_data_meta = {
            key: meta[key]
            for key in ("labels", "dataTypes", "dataFormats", "total-count", "total-pages")
            if key in meta
        }
        return {
            "endpoint_url": self.endpoint_url,
            "date_field": self.date_field,
            "query_start_date": query_start.isoformat(),
            "page_size": self.page_size,
            "pages_fetched": pages_fetched,
            "rows_fetched": rows_fetched,
            "fiscal_data_meta": fiscal_data_meta,
        }


def operating_cash_balance_adapter(
    *,
    session: HttpSession | None = None,
    timeout: float = 30.0,
    page_size: int = 10000,
) -> TreasuryFiscalDataAdapter:
    """Build the adapter for the Daily Treasury Statement operating cash balance endpoint."""
    return TreasuryFiscalDataAdapter(
        TREASURY_OPERATING_CASH_BALANCE_ENDPOINT,
        session=session,
        timeout=timeout,
        page_size=page_size,
    )


def deposits_withdrawals_operating_cash_adapter(
    *,
    session: HttpSession | None = None,
    timeout: float = 30.0,
    page_size: int = 10000,
) -> TreasuryFiscalDataAdapter:
    """Build the adapter for Daily Treasury Statement deposits/withdrawals rows."""
    return TreasuryFiscalDataAdapter(
        TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT,
        session=session,
        timeout=timeout,
        page_size=page_size,
    )


def auctions_query_adapter(
    *,
    session: HttpSession | None = None,
    timeout: float = 30.0,
    page_size: int = 10000,
) -> TreasuryFiscalDataAdapter:
    """Build the adapter for the Treasury auction query endpoint."""
    return TreasuryFiscalDataAdapter(
        TREASURY_AUCTIONS_QUERY_ENDPOINT,
        sort="record_date,cusip,auction_date,issue_date,maturity_date",
        session=session,
        timeout=timeout,
        page_size=page_size,
    )
