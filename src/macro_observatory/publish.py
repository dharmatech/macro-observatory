"""Publish browser-facing static data artifacts."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from macro_observatory.cache import load_cache, load_metadata
from macro_observatory.models import DatasetMetadata
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec
from macro_observatory.validation import require_columns

DEFAULT_SITE_DIR = Path("site")
ARTIFACT_SCHEMA_VERSION = 1
FED_NET_LIQUIDITY_DATASET_ID = "fed_net_liquidity"
FED_NET_LIQUIDITY_ARTIFACT_STEM = "fed-net-liquidity"
TGA_EXPLORER_DATASET_ID = "treasury_dts_deposits_withdrawals_operating_cash_explorer"
TGA_EXPLORER_ARTIFACT_STEM = "tga-explorer"
TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID = "treasury_securities_net_issuance"
TREASURY_SECURITIES_NET_ISSUANCE_ARTIFACT_STEM = "treasury-securities-net-issuance"
FRED_SP500_DATASET_ID = "fred_sp500"
FRED_SP500_ARTIFACT_STEM = "sp500"
TGA_EXPLORER_RENDER_GUARDRAIL_ROWS = 10_000
TREASURY_SECURITIES_RENDER_GUARDRAIL_POINTS = 25_000
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
TGA_EXPLORER_COLUMNS = (
    "record_date",
    "transaction_catg",
    "transaction_type",
    "transaction_today_amt",
    "transaction_mtd_amt",
    "transaction_fytd_amt",
)
TREASURY_SECURITIES_NET_ISSUANCE_COLUMNS = (
    "frequency",
    "date",
    "security_type",
    "issued",
    "maturing",
    "net_issuance",
)
FRED_SP500_COLUMNS = ("date", "value")
FED_NET_LIQUIDITY_SERIES: dict[str, dict[str, str]] = {
    "walcl": {"label": "WALCL", "units": "U.S. dollars", "role": "component"},
    "rrp": {"label": "RRP", "units": "U.S. dollars", "role": "component"},
    "tga": {"label": "TGA", "units": "U.S. dollars", "role": "component"},
    "rem": {"label": "REM", "units": "U.S. dollars", "role": "component"},
    "fed_net_liquidity": {
        "label": "Fed Net Liquidity",
        "units": "U.S. dollars",
        "role": "total",
    },
}
TREASURY_SECURITIES_NET_ISSUANCE_SERIES: dict[str, dict[str, str]] = {
    "issued": {"label": "Issued", "units": "U.S. dollars", "role": "component"},
    "maturing": {"label": "Maturing", "units": "U.S. dollars", "role": "component"},
    "net_issuance": {
        "label": "Net Issuance",
        "units": "U.S. dollars",
        "role": "primary_metric",
    },
}

FRED_SP500_SERIES: dict[str, dict[str, str]] = {
    "value": {"label": "S&P 500", "units": "index points", "role": "market_context"},
}

TGA_EXPLORER_SERIES: dict[str, dict[str, str]] = {
    "transaction_today_amt": {
        "label": "Transaction Today Amount",
        "units": "millions of U.S. dollars",
        "role": "metric",
    },
    "transaction_mtd_amt": {
        "label": "Transaction Month-to-Date Amount",
        "units": "millions of U.S. dollars",
        "role": "metric",
    },
    "transaction_fytd_amt": {
        "label": "Transaction Fiscal-Year-to-Date Amount",
        "units": "millions of U.S. dollars",
        "role": "metric",
    },
}

MetadataExtraBuilder = Callable[[pd.DataFrame, DatasetMetadata], dict[str, Any]]
JsonOrientation = Literal["records", "split"]


class PublishDatasetError(RuntimeError):
    """Raised when browser-facing artifacts cannot be published."""


@dataclass(frozen=True)
class PublishConfig:
    """Configuration for one browser-facing dataset artifact set."""

    dataset_id: str
    artifact_stem: str
    columns: tuple[str, ...]
    series: dict[str, dict[str, str]]
    date_column: str = "date"
    metadata_extra_builder: MetadataExtraBuilder | None = None
    json_orientation: JsonOrientation = "records"


@dataclass(frozen=True)
class PublishResult:
    """Summary of a completed publish operation."""

    dataset_id: str
    rows_published: int
    min_date: date | None
    max_date: date | None
    output_dir: Path
    json_path: Path
    csv_path: Path
    metadata_path: Path


def _string_values(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str).unique().tolist()
    return sorted(values)


def _source_cache_file(source_metadata: dict[str, Any]) -> str | None:
    value = source_metadata.get("source_cache")
    if not isinstance(value, str) or not value:
        return None
    return Path(value).name


def _tga_explorer_metadata_extra(
    published_df: pd.DataFrame,
    metadata: DatasetMetadata,
) -> dict[str, Any]:
    source_metadata = metadata.source_metadata or {}
    payload: dict[str, Any] = {
        "source_endpoint": source_metadata.get("source_endpoint"),
        "source_cache_file": _source_cache_file(source_metadata),
        "source_row_count": source_metadata.get("source_row_count"),
        "category_count": int(published_df["transaction_catg"].nunique(dropna=True)),
        "transaction_types": _string_values(published_df, "transaction_type"),
        "metric_columns": [
            "transaction_today_amt",
            "transaction_mtd_amt",
            "transaction_fytd_amt",
        ],
        "category_column": "transaction_catg",
        "transaction_type_column": "transaction_type",
        "date_column": "record_date",
        "excluded_categories": source_metadata.get("excluded_categories", []),
        "sign_policy": source_metadata.get("sign_policy"),
        "render_guardrail": {"max_rows": TGA_EXPLORER_RENDER_GUARDRAIL_ROWS},
    }
    return payload


def _fred_sp500_metadata_extra(
    published_df: pd.DataFrame,
    metadata: DatasetMetadata,
) -> dict[str, Any]:
    source_metadata = metadata.source_metadata or {}
    payload: dict[str, Any] = {
        "series_id": source_metadata.get("series_id", "SP500"),
        "source_url": source_metadata.get("source_url", "https://fred.stlouisfed.org/series/SP500"),
        "source_dataset_ids": [metadata.dataset_id],
        "date_column": "date",
        "value_column": "value",
        "market_context_role": "daily_price_overlay",
        "data_policy": (
            "Published as an independent daily market-context series, not merged into "
            "Treasury Securities Net Issuance rows. The chart overlay should use a "
            "secondary y-axis and stop at the latest available SP500 observation."
        ),
        "rights_note": (
            "FRED's SP500 page identifies third-party copyright/licensing caveats. "
            "Review source terms before redistribution or commercial use."
        ),
    }
    return payload


def _treasury_securities_net_issuance_metadata_extra(
    published_df: pd.DataFrame,
    metadata: DatasetMetadata,
) -> dict[str, Any]:
    source_metadata = metadata.source_metadata or {}
    payload: dict[str, Any] = {
        "source_endpoint": source_metadata.get("source_endpoint"),
        "source_cache_file": _source_cache_file(source_metadata),
        "source_row_count": source_metadata.get("source_row_count"),
        "valid_total_accepted_rows": source_metadata.get("valid_total_accepted_rows"),
        "null_total_accepted_rows": source_metadata.get("null_total_accepted_rows"),
        "frequencies": source_metadata.get("frequencies", []),
        "default_frequency": "ME",
        "security_types": _string_values(published_df, "security_type"),
        "value_columns": source_metadata.get(
            "value_columns",
            ["issued", "maturing", "net_issuance"],
        ),
        "primary_metric": "net_issuance",
        "date_column": "date",
        "frequency_column": "frequency",
        "security_type_column": "security_type",
        "security_type_normalization": source_metadata.get("security_type_normalization", {}),
        "date_policy": source_metadata.get("date_policy"),
        "resample_policy": source_metadata.get("resample_policy"),
        "future_maturity_policy": (
            "Future maturity dates are intentionally preserved so known scheduled "
            "maturities remain visible beyond the current date."
        ),
        "render_guardrail": {"max_points": TREASURY_SECURITIES_RENDER_GUARDRAIL_POINTS},
    }
    return payload


PUBLISH_CONFIGS = {
    FED_NET_LIQUIDITY_DATASET_ID: PublishConfig(
        dataset_id=FED_NET_LIQUIDITY_DATASET_ID,
        artifact_stem=FED_NET_LIQUIDITY_ARTIFACT_STEM,
        columns=FED_NET_LIQUIDITY_COLUMNS,
        series=FED_NET_LIQUIDITY_SERIES,
    ),
    TGA_EXPLORER_DATASET_ID: PublishConfig(
        dataset_id=TGA_EXPLORER_DATASET_ID,
        artifact_stem=TGA_EXPLORER_ARTIFACT_STEM,
        columns=TGA_EXPLORER_COLUMNS,
        series=TGA_EXPLORER_SERIES,
        date_column="record_date",
        metadata_extra_builder=_tga_explorer_metadata_extra,
        json_orientation="split",
    ),
    TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID: PublishConfig(
        dataset_id=TREASURY_SECURITIES_NET_ISSUANCE_DATASET_ID,
        artifact_stem=TREASURY_SECURITIES_NET_ISSUANCE_ARTIFACT_STEM,
        columns=TREASURY_SECURITIES_NET_ISSUANCE_COLUMNS,
        series=TREASURY_SECURITIES_NET_ISSUANCE_SERIES,
        metadata_extra_builder=_treasury_securities_net_issuance_metadata_extra,
        json_orientation="split",
    ),
    FRED_SP500_DATASET_ID: PublishConfig(
        dataset_id=FRED_SP500_DATASET_ID,
        artifact_stem=FRED_SP500_ARTIFACT_STEM,
        columns=FRED_SP500_COLUMNS,
        series=FRED_SP500_SERIES,
        metadata_extra_builder=_fred_sp500_metadata_extra,
        json_orientation="split",
    ),
}


def _get_publish_config(dataset_id: str) -> PublishConfig:
    try:
        return PUBLISH_CONFIGS[dataset_id]
    except KeyError as exc:
        known = ", ".join(sorted(PUBLISH_CONFIGS))
        raise PublishDatasetError(
            f"Dataset '{dataset_id}' does not have a publish config. "
            f"Known publishable datasets: {known}"
        ) from exc


def _date_or_none(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _build_command(dataset_id: str, kind: str) -> str:
    command = "build-derived" if kind == "derived" else "update"
    return f"uv run macro-observatory {command} {dataset_id}"


def _prepare_published_dataframe(df: pd.DataFrame, config: PublishConfig) -> pd.DataFrame:
    require_columns(df, config.columns)
    published = df.loc[:, list(config.columns)].copy()
    published[config.date_column] = pd.to_datetime(
        published[config.date_column], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    return published


def _payload_for_json(df: pd.DataFrame, config: PublishConfig) -> Any:
    json_safe = df.astype(object).where(pd.notna(df), None)
    if config.json_orientation == "records":
        return cast(list[dict[str, Any]], json_safe.to_dict(orient="records"))
    return {
        "columns": list(df.columns),
        "data": json_safe.values.tolist(),
    }


def _write_json(path: Path, payload: Any, *, compact: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if compact:
            json.dump(payload, f, allow_nan=False, separators=(",", ":"))
        else:
            json.dump(payload, f, allow_nan=False, indent=2, sort_keys=True)
        f.write("\n")


def _metadata_payload(
    *,
    config: PublishConfig,
    metadata: DatasetMetadata,
    published_df: pd.DataFrame,
    json_path: Path,
    csv_path: Path,
    metadata_path: Path,
) -> dict[str, Any]:
    source_metadata = metadata.source_metadata or {}
    payload: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "dataset_id": metadata.dataset_id,
        "title": metadata.title,
        "source_name": metadata.source_name,
        "row_count": len(published_df),
        "date_range": {
            "min": _date_or_none(metadata.min_date),
            "max": _date_or_none(metadata.max_date),
        },
        "dataset_built_at": metadata.last_successful_update.isoformat(),
        "columns": list(config.columns),
        "json_orientation": config.json_orientation,
        "series": config.series,
        "source_units": metadata.source_units,
        "display_units": metadata.display_units,
        "source_dataset_ids": source_metadata.get("derived_from", []),
        "source_rows": source_metadata.get("source_rows", {}),
        "artifacts": {
            "json": json_path.name,
            "csv": csv_path.name,
            "metadata": metadata_path.name,
        },
    }
    for key in ("formula", "forward_fill_policy", "unit_policy"):
        if key in source_metadata:
            payload[key] = source_metadata[key]
    if config.metadata_extra_builder is not None:
        payload.update(config.metadata_extra_builder(published_df, metadata))
    return payload


def publish_dataset(
    dataset_id: str,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    site_dir: Path = DEFAULT_SITE_DIR,
) -> PublishResult:
    """Publish compact browser-facing artifacts for one dataset."""
    config = _get_publish_config(dataset_id)
    spec = get_dataset_spec(dataset_id, data_dir)
    if not spec.cache_path.exists():
        raise PublishDatasetError(
            f"Missing cache for {dataset_id}. Run `{_build_command(dataset_id, spec.kind)}` first."
        )
    metadata = load_metadata(spec)
    if metadata is None:
        raise PublishDatasetError(
            f"Missing metadata for {dataset_id}. "
            f"Run `{_build_command(dataset_id, spec.kind)}` first."
        )

    df = load_cache(spec)
    published_df = _prepare_published_dataframe(df, config)
    output_dir = site_dir / "data"
    json_path = output_dir / f"{config.artifact_stem}.json"
    csv_path = output_dir / f"{config.artifact_stem}.csv"
    metadata_path = output_dir / f"{config.artifact_stem}-metadata.json"

    _write_json(json_path, _payload_for_json(published_df, config), compact=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    published_df.to_csv(csv_path, index=False)
    _write_json(
        metadata_path,
        _metadata_payload(
            config=config,
            metadata=metadata,
            published_df=published_df,
            json_path=json_path,
            csv_path=csv_path,
            metadata_path=metadata_path,
        ),
        compact=False,
    )

    return PublishResult(
        dataset_id=dataset_id,
        rows_published=len(published_df),
        min_date=metadata.min_date,
        max_date=metadata.max_date,
        output_dir=output_dir,
        json_path=json_path,
        csv_path=csv_path,
        metadata_path=metadata_path,
    )
