"""Derived dataset builders."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from macro_observatory.cache import load_cache, replace_dataset
from macro_observatory.models import UpdateResult
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec
from macro_observatory.validation import require_columns

TREASURY_OCB_DATASET_ID = "treasury_dts_operating_cash_balance"
TREASURY_TGA_DATASET_ID = "treasury_tga"
TREASURY_TGA_COLUMNS = ("date", "tga", "source_account_type", "source_balance_field")


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


def build_treasury_tga(*, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build and cache the derived TGA dataset from the Treasury OCB source cache."""
    source_spec = get_dataset_spec(TREASURY_OCB_DATASET_ID, data_dir)
    target_spec = get_dataset_spec(TREASURY_TGA_DATASET_ID, data_dir)

    if not source_spec.cache_path.exists():
        raise MissingSourceCacheError(
            "Missing source cache for treasury_tga. Run "
            "`uv run macro-observatory update treasury_dts_operating_cash_balance` first."
        )

    source_df = load_cache(source_spec)
    derived_df = derive_treasury_tga(source_df)
    metadata: dict[str, Any] = {
        "derived_from": [TREASURY_OCB_DATASET_ID],
        "source_cache": str(source_spec.cache_path),
        "source_row_count": len(source_df),
        "selection_rules": [asdict(rule) for rule in TGA_SELECTION_RULES],
    }
    return replace_dataset(target_spec, derived_df, source_metadata=metadata)


def build_derived_dataset(dataset_id: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> UpdateResult:
    """Build one derived dataset by ID."""
    if dataset_id == TREASURY_TGA_DATASET_ID:
        return build_treasury_tga(data_dir=data_dir)
    raise DerivedDatasetError(
        f"Unknown derived dataset '{dataset_id}'. Known derived datasets: {TREASURY_TGA_DATASET_ID}"
    )
