"""Small dataframe validation helpers."""

from __future__ import annotations

import pandas as pd


class DatasetValidationError(ValueError):
    """Raised when a dataset does not match its expected shape."""


def require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        joined = ", ".join(missing)
        raise DatasetValidationError(f"Missing required columns: {joined}")


def normalize_date_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    require_columns(df, (column,))
    result = df.copy()
    result[column] = pd.to_datetime(result[column], errors="raise").dt.normalize()
    return result


def normalize_numeric_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        require_columns(result, (column,))
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result
