"""Derived dataset builders."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd

from macro_observatory.cache import load_cache, load_metadata, replace_dataset
from macro_observatory.models import DatasetSpec, UpdateResult
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec
from macro_observatory.sources.treasury import (
    TREASURY_AUCTIONS_QUERY_ENDPOINT,
    TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT,
)
from macro_observatory.validation import require_columns

FRED_WALCL_DATASET_ID = "fred_walcl"
FRED_RESPPLLOPNWW_DATASET_ID = "fred_resppllopnww"
NYFED_RRP_DATASET_ID = "nyfed_rrp"
TREASURY_OCB_DATASET_ID = "treasury_dts_operating_cash_balance"
TREASURY_DTS_DEPOSITS_WITHDRAWALS_DATASET_ID = "treasury_dts_deposits_withdrawals_operating_cash"
TREASURY_AUCTIONS_QUERY_DATASET_ID = "treasury_od_auctions_query"
TREASURYDIRECT_SECURITIES_CURRENT_DATASET_ID = "treasurydirect_securities_current"
TREASURY_TGA_DATASET_ID = "treasury_tga"
TREASURY_DTS_DEPOSITS_WITHDRAWALS_EXPLORER_DATASET_ID = (
    "treasury_dts_deposits_withdrawals_operating_cash_explorer"
)
TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID = "treasury_securities_net_issuance"
TREASURYDIRECT_ISSUED_MATURING_CURRENT_DATASET_ID = "treasurydirect_issued_maturing_current"
FED_NET_LIQUIDITY_DATASET_ID = "fed_net_liquidity"
MILLIONS_TO_DOLLARS = 1_000_000.0

TREASURY_TGA_COLUMNS = ("date", "tga", "source_account_type", "source_balance_field")
TGA_EXPLORER_COLUMNS = (
    "record_date",
    "account_type",
    "transaction_type",
    "transaction_catg",
    "src_line_nbr",
    "transaction_today_amt",
    "transaction_mtd_amt",
    "transaction_fytd_amt",
)
TGA_EXPLORER_AMOUNT_COLUMNS = (
    "transaction_today_amt",
    "transaction_mtd_amt",
    "transaction_fytd_amt",
)
TGA_EXPLORER_BASE_EXCLUDED_CATEGORIES = (
    "null",
    "Sub-Total Withdrawals",
    "Sub-Total Deposits",
    "Transfers from Depositaries",
    "Transfers from Federal Reserve Account (Table V)",
    "Transfers to Depositaries",
    "Transfers to Federal Reserve Account (Table V)",
    "ShTransfersCtohFederalmReserve Account (Table V)",
)
TREASURY_SECURITIES_NET_ISSUANCE_COLUMNS = (
    "frequency",
    "date",
    "security_type",
    "issued",
    "maturing",
    "net_issuance",
)
TREASURY_SECURITIES_NET_ISSUANCE_VALUE_COLUMNS = ("issued", "maturing", "net_issuance")
TREASURY_SECURITIES_NET_ISSUANCE_FREQUENCIES = ("D", "W", "ME", "QE", "YE")
TREASURY_SECURITY_TYPE_REPLACEMENTS = {
    "TIPS Note": "Note",
    "FRN Note": "Note",
    "TIPS Bond": "Bond",
    "CMB": "Bill",
    "null": "Unknown",
}
TREASURYDIRECT_SECURITY_TYPES = ("Bill", "Note", "Bond")
TREASURYDIRECT_ISSUED_MATURING_COLUMNS = (
    "date",
    "issued_bills",
    "maturing_bills",
    "bills_change",
    "issued_notes",
    "maturing_notes",
    "notes_change",
    "issued_bonds",
    "maturing_bonds",
    "bonds_change",
    "issued",
    "maturing",
    "change",
    "change_with_weekend",
    "weekend",
    "auction",
    "auction_issuing",
    "offering_amount",
    "soma_tendered",
    "projected_change",
    "projected_change_bills",
    "projected_change_notes",
    "projected_change_bonds",
)
TREASURYDIRECT_ISSUED_MATURING_VALUE_COLUMNS = (
    "issued_bills",
    "maturing_bills",
    "bills_change",
    "issued_notes",
    "maturing_notes",
    "notes_change",
    "issued_bonds",
    "maturing_bonds",
    "bonds_change",
    "issued",
    "maturing",
    "change",
    "change_with_weekend",
    "weekend",
    "offering_amount",
    "soma_tendered",
    "projected_change",
    "projected_change_bills",
    "projected_change_notes",
    "projected_change_bonds",
)
FED_NET_LIQUIDITY_COLUMNS = (
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
)
FED_NET_LIQUIDITY_INPUTS = (
    FRED_WALCL_DATASET_ID,
    FRED_RESPPLLOPNWW_DATASET_ID,
    NYFED_RRP_DATASET_ID,
    TREASURY_TGA_DATASET_ID,
)
DERIVED_DATASET_IDS = (
    TREASURY_TGA_DATASET_ID,
    TREASURY_DTS_DEPOSITS_WITHDRAWALS_EXPLORER_DATASET_ID,
    TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID,
    TREASURYDIRECT_ISSUED_MATURING_CURRENT_DATASET_ID,
    FED_NET_LIQUIDITY_DATASET_ID,
)


class DerivedDatasetError(RuntimeError):
    """Raised when a derived dataset cannot be built."""


class MissingSourceCacheError(DerivedDatasetError):
    """Raised when a required source cache has not been built yet."""


@dataclass(frozen=True)
class TgaSelectionRule:
    """One rule for selecting the continuous TGA value from Treasury OCB rows."""

    account_type: str
    balance_field: str
    priority: int


TGA_SELECTION_RULES = (
    TgaSelectionRule(
        account_type="Federal Reserve Account",
        balance_field="close_today_bal",
        priority=1,
    ),
    TgaSelectionRule(
        account_type="Treasury General Account (TGA)",
        balance_field="close_today_bal",
        priority=2,
    ),
    TgaSelectionRule(
        account_type="Treasury General Account (TGA) Closing Balance",
        balance_field="open_today_bal",
        priority=3,
    ),
)


def _build_command(dataset_id: str) -> str:
    if dataset_id in DERIVED_DATASET_IDS:
        return f"uv run macro-observatory build-derived {dataset_id}"
    if dataset_id == TREASURYDIRECT_SECURITIES_CURRENT_DATASET_ID:
        return f"uv run macro-observatory refresh-current {dataset_id}"
    return f"uv run macro-observatory update {dataset_id}"


def _require_cache(spec: DatasetSpec, *, target_dataset_id: str) -> None:
    if spec.cache_path.exists():
        return
    raise MissingSourceCacheError(
        f"Missing required cache for {target_dataset_id}: {spec.id}. "
        f"Run `{_build_command(spec.id)}` first."
    )


def derive_treasury_tga(source_df: pd.DataFrame) -> pd.DataFrame:
    """Derive the continuous TGA series from the full Treasury OCB source cache."""
    required_columns = ("record_date", "account_type", "close_today_bal", "open_today_bal")
    require_columns(source_df, required_columns)

    frames: list[pd.DataFrame] = []
    for rule in TGA_SELECTION_RULES:
        columns = ["record_date", "account_type", rule.balance_field]
        selected = source_df.loc[source_df["account_type"] == rule.account_type, columns].copy()
        if selected.empty:
            continue
        selected = selected.rename(
            columns={
                "record_date": "date",
                "account_type": "source_account_type",
                rule.balance_field: "tga",
            }
        )
        selected["source_balance_field"] = rule.balance_field
        selected["_priority"] = rule.priority
        frames.append(selected)

    if not frames:
        raise DerivedDatasetError("No Treasury rows matched the known TGA account types.")

    result = pd.concat(frames, ignore_index=True)
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result["tga"] = pd.to_numeric(result["tga"], errors="coerce")
    result = result.dropna(subset=["tga"])
    if result.empty:
        raise DerivedDatasetError(
            "Known TGA account rows were present, but all TGA values were null."
        )

    result = result.sort_values(["date", "_priority"])
    result = result.drop_duplicates(subset=["date"], keep="last")
    result = result.sort_values("date").reset_index(drop=True)
    return result.loc[:, list(TREASURY_TGA_COLUMNS)].copy()


def derive_tga_explorer(source_df: pd.DataFrame) -> pd.DataFrame:
    """Build the reduced, reusable TGA Explorer dataset from DTS deposits/withdrawals."""
    require_columns(source_df, TGA_EXPLORER_COLUMNS)

    result = source_df.loc[:, list(TGA_EXPLORER_COLUMNS)].copy()
    result["record_date"] = pd.to_datetime(result["record_date"], errors="raise").dt.normalize()
    result["src_line_nbr"] = pd.to_numeric(result["src_line_nbr"], errors="coerce")
    for column in TGA_EXPLORER_AMOUNT_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    category = result["transaction_catg"].astype("string")
    result = result.loc[~category.isin(TGA_EXPLORER_BASE_EXCLUDED_CATEGORIES)].copy()
    result = result.sort_values(
        ["record_date", "account_type", "transaction_type", "src_line_nbr"]
    ).reset_index(drop=True)
    return result.loc[:, list(TGA_EXPLORER_COLUMNS)].copy()


def _treasury_securities_source_frame(source_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = ("issue_date", "maturity_date", "security_type", "total_accepted")
    require_columns(source_df, required_columns)

    result = source_df.loc[:, list(required_columns)].copy()
    result["issue_date"] = pd.to_datetime(result["issue_date"], errors="coerce").dt.normalize()
    result["maturity_date"] = pd.to_datetime(
        result["maturity_date"], errors="coerce"
    ).dt.normalize()
    result["total_accepted"] = pd.to_numeric(result["total_accepted"], errors="coerce")
    security_type = result["security_type"].astype("string")
    security_type = security_type.replace(TREASURY_SECURITY_TYPE_REPLACEMENTS)
    result["security_type"] = security_type.fillna("Unknown").astype(str)
    return result


def _treasury_securities_amounts(
    source_df: pd.DataFrame,
    *,
    date_column: str,
    output_column: str,
) -> pd.DataFrame:
    selected = source_df.dropna(subset=[date_column, "total_accepted"])
    if selected.empty:
        return pd.DataFrame(columns=["date", "security_type", output_column])

    result = selected.groupby([date_column, "security_type"], as_index=False).agg(
        total_accepted=("total_accepted", "sum")
    )
    result = result.rename(columns={date_column: "date", "total_accepted": output_column})
    return result.loc[:, ["date", "security_type", output_column]].copy()


def _daily_treasury_securities_net_issuance(source_df: pd.DataFrame) -> pd.DataFrame:
    prepared = _treasury_securities_source_frame(source_df)
    valid_amounts = prepared.dropna(subset=["total_accepted"])
    if valid_amounts.empty:
        raise DerivedDatasetError("Treasury auctions source has no numeric total_accepted rows.")

    issued = _treasury_securities_amounts(
        prepared,
        date_column="issue_date",
        output_column="issued",
    )
    maturing = _treasury_securities_amounts(
        prepared,
        date_column="maturity_date",
        output_column="maturing",
    )
    result = issued.merge(maturing, on=["date", "security_type"], how="outer")
    result[["issued", "maturing"]] = result[["issued", "maturing"]].fillna(0.0)
    result = result.groupby(["date", "security_type"], as_index=False)[["issued", "maturing"]].sum()
    result["net_issuance"] = result["issued"] - result["maturing"]
    return result.sort_values(["date", "security_type"]).reset_index(drop=True)


def _resample_treasury_securities_metric(
    daily_df: pd.DataFrame,
    *,
    frequency: str,
    value_column: str,
) -> pd.DataFrame:
    pivot = (
        daily_df.pivot(index="date", columns="security_type", values=value_column)
        .fillna(0.0)
        .sort_index()
    )
    resampled = pivot.resample(frequency).sum()
    if frequency == "ME":
        month_start = resampled.reset_index()
        month_start["date"] = month_start["date"].dt.to_period("M").dt.to_timestamp()
        resampled = month_start.set_index("date")

    return resampled.reset_index().melt(
        id_vars="date",
        var_name="security_type",
        value_name=value_column,
    )


def _resample_treasury_securities_net_issuance(
    daily_df: pd.DataFrame,
    frequency: str,
) -> pd.DataFrame:
    frames = [
        _resample_treasury_securities_metric(
            daily_df,
            frequency=frequency,
            value_column=value_column,
        )
        for value_column in TREASURY_SECURITIES_NET_ISSUANCE_VALUE_COLUMNS
    ]
    result = frames[0]
    for frame in frames[1:]:
        result = result.merge(frame, on=["date", "security_type"], how="inner")
    result["frequency"] = frequency
    return result.loc[:, list(TREASURY_SECURITIES_NET_ISSUANCE_COLUMNS)].copy()


def derive_treasury_securities_net_issuance(source_df: pd.DataFrame) -> pd.DataFrame:
    """Build Treasury securities net issuance across legacy pandas frequencies."""
    daily = _daily_treasury_securities_net_issuance(source_df)
    if daily.empty:
        raise DerivedDatasetError("Treasury auctions source produced no issuance rows.")

    result = pd.concat(
        [
            _resample_treasury_securities_net_issuance(daily, frequency)
            for frequency in TREASURY_SECURITIES_NET_ISSUANCE_FREQUENCIES
        ],
        ignore_index=True,
    )
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    frequency_order = {
        frequency: index
        for index, frequency in enumerate(TREASURY_SECURITIES_NET_ISSUANCE_FREQUENCIES)
    }
    result["_frequency_order"] = result["frequency"].map(frequency_order)
    result = result.sort_values(["_frequency_order", "date", "security_type"]).reset_index(
        drop=True
    )
    return result.loc[:, list(TREASURY_SECURITIES_NET_ISSUANCE_COLUMNS)].copy()


def _treasurydirect_current_source_frame(source_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = (
        "query_mode",
        "query_start_date",
        "query_end_date",
        "cusip",
        "securityType",
        "auctionDate",
        "issueDate",
        "maturityDate",
        "totalAccepted",
        "offeringAmount",
        "somaTendered",
    )
    require_columns(source_df, required_columns)
    if source_df.empty:
        raise DerivedDatasetError("TreasuryDirect current source cache is empty.")

    result = source_df.loc[:, list(required_columns)].copy()
    for column in (
        "query_start_date",
        "query_end_date",
        "auctionDate",
        "issueDate",
        "maturityDate",
    ):
        result[column] = pd.to_datetime(result[column], errors="coerce").dt.normalize()
    for column in ("totalAccepted", "offeringAmount", "somaTendered"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["securityType"] = result["securityType"].astype("string").fillna("Unknown")
    result["query_mode"] = result["query_mode"].astype("string")
    return result


def _treasurydirect_report_dates(prepared: pd.DataFrame) -> pd.DatetimeIndex:
    start_values = prepared["query_start_date"].dropna()
    end_values = prepared["query_end_date"].dropna()
    if start_values.empty or end_values.empty:
        raise DerivedDatasetError("TreasuryDirect current source is missing query window dates.")

    start_date = start_values.min()
    end_date = end_values.max()
    if not isinstance(start_date, pd.Timestamp) or not isinstance(end_date, pd.Timestamp):
        raise DerivedDatasetError("TreasuryDirect query window dates could not be parsed.")
    if end_date <= start_date:
        raise DerivedDatasetError("TreasuryDirect query window end date must be after start date.")

    return pd.date_range(start=start_date, end=end_date - pd.Timedelta(days=1), freq="D")


def _sum_amount(df: pd.DataFrame, column: str) -> float:
    if df.empty:
        return 0.0
    return float(df[column].sum(skipna=True))


def _optional_sum_amount(df: pd.DataFrame, column: str) -> float | None:
    if df.empty:
        return None
    values = df[column].dropna()
    if values.empty:
        return None
    return float(values.sum())


def _projected_change(
    *,
    issued_rows: pd.DataFrame,
    maturing_amount: float,
    security_type: str | None = None,
) -> float | None:
    selected = issued_rows
    if security_type is not None:
        selected = selected.loc[selected["securityType"] == security_type]

    offering_amount = _optional_sum_amount(selected, "offeringAmount")
    if offering_amount is None:
        return None
    soma_tendered = _optional_sum_amount(selected, "somaTendered") or 0.0
    return offering_amount + soma_tendered - maturing_amount


def _treasurydirect_auction_issuing(auctioned: pd.DataFrame, current_date: pd.Timestamp) -> str:
    selected = auctioned.loc[auctioned["issueDate"] == current_date]
    if selected.empty:
        return ""
    auction_dates = selected["auctionDate"].dropna().dt.date.astype(str).sort_values().unique()
    return " ".join(str(value) for value in auction_dates)


def _treasurydirect_report_row(
    prepared: pd.DataFrame, current_date: pd.Timestamp
) -> dict[str, Any]:
    issued = prepared.loc[
        (prepared["query_mode"] == "issueDate") & (prepared["issueDate"] == current_date)
    ]
    maturing = prepared.loc[
        (prepared["query_mode"] == "maturityDate") & (prepared["maturityDate"] == current_date)
    ]
    auctioned = prepared.loc[prepared["query_mode"] == "auctionDate"]
    auctioned_today = auctioned.loc[auctioned["auctionDate"] == current_date]

    row: dict[str, Any] = {"date": current_date}
    issued_total = _sum_amount(issued, "totalAccepted")
    maturing_total = _sum_amount(maturing, "totalAccepted")

    for security_type in TREASURYDIRECT_SECURITY_TYPES:
        key = security_type.lower()
        issued_type = issued.loc[issued["securityType"] == security_type]
        maturing_type = maturing.loc[maturing["securityType"] == security_type]
        issued_amount = _sum_amount(issued_type, "totalAccepted")
        maturing_amount = _sum_amount(maturing_type, "totalAccepted")
        row[f"issued_{key}s"] = issued_amount
        row[f"maturing_{key}s"] = maturing_amount
        row[f"{key}s_change"] = issued_amount - maturing_amount

    row["issued"] = issued_total
    row["maturing"] = maturing_total
    row["change"] = issued_total - maturing_total
    row["change_with_weekend"] = pd.NA
    row["weekend"] = pd.NA
    row["auction"] = "*" if not auctioned_today.empty else ""
    row["auction_issuing"] = _treasurydirect_auction_issuing(auctioned, current_date)
    row["offering_amount"] = _optional_sum_amount(issued, "offeringAmount")
    row["soma_tendered"] = _optional_sum_amount(issued, "somaTendered")
    row["projected_change"] = _projected_change(
        issued_rows=issued,
        maturing_amount=maturing_total,
    )
    for security_type in TREASURYDIRECT_SECURITY_TYPES:
        key = security_type.lower()
        row[f"projected_change_{key}s"] = _projected_change(
            issued_rows=issued,
            maturing_amount=float(row[f"maturing_{key}s"]),
            security_type=security_type,
        )
    return row


def _apply_treasurydirect_weekend_rollover(report_df: pd.DataFrame) -> pd.DataFrame:
    result = report_df.copy()
    weekend = 0.0
    for index in result.index:
        current_date = cast(pd.Timestamp, result.at[index, "date"])
        change = cast(float, result.at[index, "change"])
        if current_date.dayofweek in (5, 6):
            weekend += change
            continue
        if weekend != 0.0:
            result.at[index, "change_with_weekend"] = change + weekend
            result.at[index, "weekend"] = weekend
            weekend = 0.0
    return result


def _filter_treasurydirect_report_rows(report_df: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(report_df["date"], errors="raise")
    is_weekend = dates.dt.dayofweek.isin((5, 6))
    has_weekend_change = report_df["change"] != 0.0
    return report_df.loc[(~is_weekend) | has_weekend_change].copy()


def derive_treasurydirect_issued_maturing(source_df: pd.DataFrame) -> pd.DataFrame:
    """Build the current TreasuryDirect issued/maturing report table."""
    prepared = _treasurydirect_current_source_frame(source_df)
    report_dates = _treasurydirect_report_dates(prepared)
    rows = [_treasurydirect_report_row(prepared, current_date) for current_date in report_dates]
    if not rows:
        raise DerivedDatasetError("TreasuryDirect current window produced no report dates.")

    result = pd.DataFrame(rows)
    result = _apply_treasurydirect_weekend_rollover(result)
    result = _filter_treasurydirect_report_rows(result)
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result = result.sort_values("date").reset_index(drop=True)
    return result.loc[:, list(TREASURYDIRECT_ISSUED_MATURING_COLUMNS)].copy()


def _component_frame(
    df: pd.DataFrame,
    *,
    date_column: str,
    value_column: str,
    output_column: str,
    multiplier: float,
) -> pd.DataFrame:
    require_columns(df, (date_column, value_column))
    result = df.loc[:, [date_column, value_column]].copy()
    result = result.rename(columns={date_column: "date", value_column: output_column})
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result[output_column] = pd.to_numeric(result[output_column], errors="coerce") * multiplier
    result = result.drop_duplicates(subset=["date"], keep="last")
    return result.sort_values("date").reset_index(drop=True)


def derive_fed_net_liquidity(
    *,
    walcl_df: pd.DataFrame,
    rem_df: pd.DataFrame,
    rrp_df: pd.DataFrame,
    tga_df: pd.DataFrame,
) -> pd.DataFrame:
    """Derive Fed net liquidity from the four component datasets."""
    components = [
        _component_frame(
            walcl_df,
            date_column="date",
            value_column="value",
            output_column="walcl",
            multiplier=MILLIONS_TO_DOLLARS,
        ),
        _component_frame(
            rrp_df,
            date_column="operationDate",
            value_column="totalAmtAccepted",
            output_column="rrp",
            multiplier=1.0,
        ),
        _component_frame(
            tga_df,
            date_column="date",
            value_column="tga",
            output_column="tga",
            multiplier=MILLIONS_TO_DOLLARS,
        ),
        _component_frame(
            rem_df,
            date_column="date",
            value_column="value",
            output_column="rem",
            multiplier=MILLIONS_TO_DOLLARS,
        ),
    ]

    result = components[0]
    for component in components[1:]:
        result = result.merge(component, on="date", how="outer")

    result = result.sort_values("date").reset_index(drop=True)
    value_columns = ["walcl", "rrp", "tga", "rem"]
    result[value_columns] = result[value_columns].ffill()
    result["fed_net_liquidity"] = result["walcl"] - result["rrp"] - result["tga"] - result["rem"]

    for column in [*value_columns, "fed_net_liquidity"]:
        result[f"{column}_diff"] = result[column].diff()

    return result.loc[:, list(FED_NET_LIQUIDITY_COLUMNS)].copy()


def build_treasury_tga(*, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build and cache the derived TGA dataset from the Treasury OCB source cache."""
    source_spec = get_dataset_spec(TREASURY_OCB_DATASET_ID, data_dir)
    target_spec = get_dataset_spec(TREASURY_TGA_DATASET_ID, data_dir)

    _require_cache(source_spec, target_dataset_id=TREASURY_TGA_DATASET_ID)

    source_df = load_cache(source_spec)
    derived_df = derive_treasury_tga(source_df)
    metadata: dict[str, Any] = {
        "derived_from": [TREASURY_OCB_DATASET_ID],
        "source_cache": str(source_spec.cache_path),
        "source_row_count": len(source_df),
        "selection_rules": [asdict(rule) for rule in TGA_SELECTION_RULES],
    }
    return replace_dataset(target_spec, derived_df, source_metadata=metadata)


def _source_endpoint(source_spec: DatasetSpec, *, fallback: str) -> str:
    metadata = load_metadata(source_spec)
    if metadata is not None and metadata.source_metadata is not None:
        endpoint = metadata.source_metadata.get("endpoint_url")
        if isinstance(endpoint, str):
            return endpoint
    return fallback


def build_tga_explorer(*, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build and cache the reduced dataset used by the TGA Explorer page."""
    source_spec = get_dataset_spec(TREASURY_DTS_DEPOSITS_WITHDRAWALS_DATASET_ID, data_dir)
    target_spec = get_dataset_spec(TREASURY_DTS_DEPOSITS_WITHDRAWALS_EXPLORER_DATASET_ID, data_dir)

    _require_cache(
        source_spec,
        target_dataset_id=TREASURY_DTS_DEPOSITS_WITHDRAWALS_EXPLORER_DATASET_ID,
    )

    source_df = load_cache(source_spec)
    derived_df = derive_tga_explorer(source_df)
    metadata: dict[str, Any] = {
        "derived_from": [TREASURY_DTS_DEPOSITS_WITHDRAWALS_DATASET_ID],
        "source_endpoint": _source_endpoint(
            source_spec,
            fallback=TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT,
        ),
        "source_cache": str(source_spec.cache_path),
        "source_row_count": len(source_df),
        "source_rows": {TREASURY_DTS_DEPOSITS_WITHDRAWALS_DATASET_ID: len(source_df)},
        "excluded_categories": list(TGA_EXPLORER_BASE_EXCLUDED_CATEGORIES),
        "output_columns": list(TGA_EXPLORER_COLUMNS),
        "amount_columns": list(TGA_EXPLORER_AMOUNT_COLUMNS),
        "sign_policy": (
            "Amounts are cached in Treasury's published sign. The browser renders "
            "Withdrawals as negative values before charting."
        ),
    }
    return replace_dataset(target_spec, derived_df, source_metadata=metadata)


def build_treasury_securities_net_issuance(*, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build and cache the derived Treasury securities net issuance dataset."""
    source_spec = get_dataset_spec(TREASURY_AUCTIONS_QUERY_DATASET_ID, data_dir)
    target_spec = get_dataset_spec(TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID, data_dir)

    _require_cache(source_spec, target_dataset_id=TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID)

    source_df = load_cache(source_spec)
    prepared = _treasury_securities_source_frame(source_df)
    derived_df = derive_treasury_securities_net_issuance(source_df)
    valid_amounts = prepared.dropna(subset=["total_accepted"])
    metadata: dict[str, Any] = {
        "derived_from": [TREASURY_AUCTIONS_QUERY_DATASET_ID],
        "source_endpoint": _source_endpoint(
            source_spec,
            fallback=TREASURY_AUCTIONS_QUERY_ENDPOINT,
        ),
        "source_cache": str(source_spec.cache_path),
        "source_row_count": len(source_df),
        "source_rows": {TREASURY_AUCTIONS_QUERY_DATASET_ID: len(source_df)},
        "valid_total_accepted_rows": len(valid_amounts),
        "null_total_accepted_rows": int(prepared["total_accepted"].isna().sum()),
        "issue_date_null_rows": int(valid_amounts["issue_date"].isna().sum()),
        "maturity_date_null_rows": int(valid_amounts["maturity_date"].isna().sum()),
        "output_columns": list(TREASURY_SECURITIES_NET_ISSUANCE_COLUMNS),
        "value_columns": list(TREASURY_SECURITIES_NET_ISSUANCE_VALUE_COLUMNS),
        "frequencies": list(TREASURY_SECURITIES_NET_ISSUANCE_FREQUENCIES),
        "security_types": sorted(str(value) for value in valid_amounts["security_type"].unique()),
        "security_type_normalization": dict(TREASURY_SECURITY_TYPE_REPLACEMENTS),
        "date_policy": (
            "Issued amounts are grouped by issue_date. Maturing amounts are grouped by "
            "maturity_date. Future maturities are intentionally preserved."
        ),
        "formula": "net_issuance = issued - maturing",
        "resample_policy": (
            "The daily security-type pivot is resampled with pandas sum() for D, W, ME, "
            "QE, and YE. W uses pandas' default W-SUN boundary. ME labels are converted "
            "to month starts to match the legacy Streamlit page."
        ),
    }
    return replace_dataset(target_spec, derived_df, source_metadata=metadata)


def build_treasurydirect_issued_maturing(*, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build and cache the current TreasuryDirect issued/maturing report table."""
    source_spec = get_dataset_spec(TREASURYDIRECT_SECURITIES_CURRENT_DATASET_ID, data_dir)
    target_spec = get_dataset_spec(TREASURYDIRECT_ISSUED_MATURING_CURRENT_DATASET_ID, data_dir)

    _require_cache(
        source_spec,
        target_dataset_id=TREASURYDIRECT_ISSUED_MATURING_CURRENT_DATASET_ID,
    )

    source_df = load_cache(source_spec)
    derived_df = derive_treasurydirect_issued_maturing(source_df)
    prepared = _treasurydirect_current_source_frame(source_df)
    report_dates = _treasurydirect_report_dates(prepared)
    source_metadata = load_metadata(source_spec)
    source_source_metadata = (
        source_metadata.source_metadata
        if source_metadata is not None and source_metadata.source_metadata is not None
        else {}
    )
    metadata: dict[str, Any] = {
        "derived_from": [TREASURYDIRECT_SECURITIES_CURRENT_DATASET_ID],
        "source_endpoint": source_source_metadata.get("endpoint_url"),
        "source_cache": str(source_spec.cache_path),
        "source_row_count": len(source_df),
        "source_rows": {TREASURYDIRECT_SECURITIES_CURRENT_DATASET_ID: len(source_df)},
        "query_window_start_date": report_dates.min().date().isoformat(),
        "query_window_end_date_exclusive": (report_dates.max() + pd.Timedelta(days=1))
        .date()
        .isoformat(),
        "output_columns": list(TREASURYDIRECT_ISSUED_MATURING_COLUMNS),
        "value_columns": list(TREASURYDIRECT_ISSUED_MATURING_VALUE_COLUMNS),
        "security_types": list(TREASURYDIRECT_SECURITY_TYPES),
        "formula": "change = issued - maturing",
        "projected_formula": "projected_change = offering_amount + soma_tendered - maturing",
        "date_policy": (
            "The source current-window query_start_date is included and query_end_date is "
            "excluded, matching the legacy PowerShell date-range behavior."
        ),
        "weekend_policy": (
            "Weekend completed changes accumulate into the next weekday as "
            "change_with_weekend and weekend. Weekend rows are kept only when change is non-zero."
        ),
        "projection_policy": (
            "Projected values are null when no issue-date source rows exist for the date or "
            "security type. Amounts are stored in raw U.S. dollars."
        ),
    }
    return replace_dataset(target_spec, derived_df, source_metadata=metadata)


def build_fed_net_liquidity(*, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build and cache the derived Fed net liquidity dataset."""
    specs = {
        dataset_id: get_dataset_spec(dataset_id, data_dir)
        for dataset_id in FED_NET_LIQUIDITY_INPUTS
    }
    target_spec = get_dataset_spec(FED_NET_LIQUIDITY_DATASET_ID, data_dir)
    for spec in specs.values():
        _require_cache(spec, target_dataset_id=FED_NET_LIQUIDITY_DATASET_ID)

    source_frames = {dataset_id: load_cache(spec) for dataset_id, spec in specs.items()}
    derived_df = derive_fed_net_liquidity(
        walcl_df=source_frames[FRED_WALCL_DATASET_ID],
        rem_df=source_frames[FRED_RESPPLLOPNWW_DATASET_ID],
        rrp_df=source_frames[NYFED_RRP_DATASET_ID],
        tga_df=source_frames[TREASURY_TGA_DATASET_ID],
    )
    metadata: dict[str, Any] = {
        "derived_from": list(FED_NET_LIQUIDITY_INPUTS),
        "formula": "fed_net_liquidity = walcl - rrp - tga - rem",
        "unit_policy": {
            "output_units": "U.S. dollars",
            "million_dollar_inputs_scaled_by": int(MILLIONS_TO_DOLLARS),
            "million_dollar_inputs": [
                FRED_WALCL_DATASET_ID,
                FRED_RESPPLLOPNWW_DATASET_ID,
                TREASURY_TGA_DATASET_ID,
            ],
            "dollar_inputs": [NYFED_RRP_DATASET_ID],
        },
        "forward_fill_policy": (
            "Components are outer-merged by date, sorted by date, forward-filled, "
            "then fed_net_liquidity and diff columns are computed."
        ),
        "source_rows": {dataset_id: len(frame) for dataset_id, frame in source_frames.items()},
    }
    return replace_dataset(target_spec, derived_df, source_metadata=metadata)


def build_derived_dataset(dataset_id: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build one derived dataset by ID."""
    if dataset_id == TREASURY_TGA_DATASET_ID:
        return build_treasury_tga(data_dir=data_dir)
    if dataset_id == TREASURY_DTS_DEPOSITS_WITHDRAWALS_EXPLORER_DATASET_ID:
        return build_tga_explorer(data_dir=data_dir)
    if dataset_id == TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID:
        return build_treasury_securities_net_issuance(data_dir=data_dir)
    if dataset_id == TREASURYDIRECT_ISSUED_MATURING_CURRENT_DATASET_ID:
        return build_treasurydirect_issued_maturing(data_dir=data_dir)
    if dataset_id == FED_NET_LIQUIDITY_DATASET_ID:
        return build_fed_net_liquidity(data_dir=data_dir)
    known = ", ".join(DERIVED_DATASET_IDS)
    raise DerivedDatasetError(
        f"Unknown derived dataset '{dataset_id}'. Known derived datasets: {known}"
    )
