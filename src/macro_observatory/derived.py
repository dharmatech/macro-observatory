"""Derived dataset builders."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from macro_observatory.cache import load_cache, load_metadata, replace_dataset
from macro_observatory.models import DatasetSpec, UpdateResult
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec
from macro_observatory.sources.treasury import TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT
from macro_observatory.validation import require_columns

FRED_WALCL_DATASET_ID = "fred_walcl"
FRED_RESPPLLOPNWW_DATASET_ID = "fred_resppllopnww"
NYFED_RRP_DATASET_ID = "nyfed_rrp"
TREASURY_OCB_DATASET_ID = "treasury_dts_operating_cash_balance"
TREASURY_DTS_DEPOSITS_WITHDRAWALS_DATASET_ID = "treasury_dts_deposits_withdrawals_operating_cash"
TREASURY_TGA_DATASET_ID = "treasury_tga"
TREASURY_DTS_DEPOSITS_WITHDRAWALS_EXPLORER_DATASET_ID = (
    "treasury_dts_deposits_withdrawals_operating_cash_explorer"
)
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


def _source_endpoint(source_spec: DatasetSpec) -> str:
    metadata = load_metadata(source_spec)
    if metadata is not None and metadata.source_metadata is not None:
        endpoint = metadata.source_metadata.get("endpoint_url")
        if isinstance(endpoint, str):
            return endpoint
    return TREASURY_DEPOSITS_WITHDRAWALS_OPERATING_CASH_ENDPOINT


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
        "source_endpoint": _source_endpoint(source_spec),
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
    if dataset_id == FED_NET_LIQUIDITY_DATASET_ID:
        return build_fed_net_liquidity(data_dir=data_dir)
    known = ", ".join(DERIVED_DATASET_IDS)
    raise DerivedDatasetError(
        f"Unknown derived dataset '{dataset_id}'. Known derived datasets: {known}"
    )
