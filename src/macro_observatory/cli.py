"""Command-line interface for dataset inspection and updates."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from macro_observatory.cache import load_metadata, update_dataset
from macro_observatory.data import load_dataset
from macro_observatory.derived import DerivedDatasetError, build_derived_dataset
from macro_observatory.diagnostics import build_storage_report, render_storage_report
from macro_observatory.models import UpdateResult
from macro_observatory.publish import (
    DEFAULT_SITE_DIR,
    PublishDatasetError,
    PublishResult,
    publish_dataset,
)
from macro_observatory.registry import DEFAULT_DATA_DIR, build_registry, get_dataset_spec
from macro_observatory.server import DEFAULT_HOST, DEFAULT_PORT, SiteDirectoryError, serve_site


def _data_dir(value: str | None) -> Path:
    return Path(value) if value else DEFAULT_DATA_DIR


def _print_dataframe(df: pd.DataFrame, rows: int) -> None:
    if df.empty:
        print("No rows")
        return
    print(df.tail(rows).to_string(index=False))


def _datasets(args: argparse.Namespace) -> int:
    registry = build_registry(_data_dir(args.data_dir))
    for spec in registry.values():
        print(f"{spec.id}\t{spec.title}")
    return 0


def _print_result(prefix: str, result: UpdateResult, *, rows_label: str = "rows fetched") -> None:
    print(f"{prefix} {result.dataset_id}")
    print(f"rows before: {result.rows_before:,}")
    print(f"{rows_label}: {result.rows_fetched:,}")
    print(f"rows after: {result.rows_after:,}")
    print(f"date range: {result.min_date} to {result.max_date}")
    print(f"cache: {result.cache_path}")
    print(f"metadata: {result.metadata_path}")


def _print_publish_result(result: PublishResult) -> None:
    print(f"published {result.dataset_id}")
    print(f"rows published: {result.rows_published:,}")
    print(f"date range: {result.min_date} to {result.max_date}")
    print(f"output dir: {result.output_dir}")
    print(f"json: {result.json_path}")
    print(f"csv: {result.csv_path}")
    print(f"metadata: {result.metadata_path}")


def _update(args: argparse.Namespace) -> int:
    spec = get_dataset_spec(args.dataset_id, _data_dir(args.data_dir))
    if spec.kind == "derived":
        print(f"Dataset '{spec.id}' is derived. Use `build-derived {spec.id}` instead.")
        return 1
    result = update_dataset(spec)
    _print_result("updated", result)
    return 0


def _build_derived(args: argparse.Namespace) -> int:
    try:
        result = build_derived_dataset(args.dataset_id, data_dir=_data_dir(args.data_dir))
    except DerivedDatasetError as exc:
        print(str(exc))
        return 1
    _print_result("built", result, rows_label="rows built")
    return 0


def _publish(args: argparse.Namespace) -> int:
    site_dir = Path(args.site_dir) if args.site_dir else DEFAULT_SITE_DIR
    try:
        result = publish_dataset(
            args.dataset_id,
            data_dir=_data_dir(args.data_dir),
            site_dir=site_dir,
        )
    except PublishDatasetError as exc:
        print(str(exc))
        return 1
    _print_publish_result(result)
    return 0


def _storage_report(args: argparse.Namespace) -> int:
    site_dir = Path(args.site_dir) if args.site_dir else DEFAULT_SITE_DIR
    report = build_storage_report(data_dir=_data_dir(args.data_dir), site_dir=site_dir)
    print(render_storage_report(report))
    return 0


def _serve_site(args: argparse.Namespace) -> int:
    site_dir = Path(args.site_dir) if args.site_dir else DEFAULT_SITE_DIR
    try:
        serve_site(site_dir=site_dir, host=args.host, port=args.port)
    except SiteDirectoryError as exc:
        print(str(exc))
        return 1
    except OSError as exc:
        print(f"Could not start static site server: {exc}")
        return 1
    return 0


def _info(args: argparse.Namespace) -> int:
    spec = get_dataset_spec(args.dataset_id, _data_dir(args.data_dir))
    metadata = load_metadata(spec)
    if metadata is None:
        command = "build-derived" if spec.kind == "derived" else "update"
        print(f"No metadata for {spec.id}. Run {command} first.")
        return 1
    print(f"dataset: {metadata.dataset_id}")
    print(f"title: {metadata.title}")
    print(f"kind: {spec.kind}")
    print(f"source: {metadata.source_name}")
    print(f"rows: {metadata.row_count:,}")
    print(f"date range: {metadata.min_date} to {metadata.max_date}")
    print(f"last update: {metadata.last_successful_update.isoformat()}")
    print(f"cache: {metadata.cache_path}")
    print(f"columns: {', '.join(metadata.columns)}")
    if metadata.source_units:
        print(f"source units: {metadata.source_units}")
    if metadata.display_units:
        print(f"display units: {metadata.display_units}")
    if metadata.source_metadata:
        keys = ", ".join(sorted(metadata.source_metadata))
        print(f"source metadata keys: {keys}")
    return 0


def _show(args: argparse.Namespace) -> int:
    df = load_dataset(args.dataset_id, data_dir=_data_dir(args.data_dir))
    _print_dataframe(df, args.rows)
    return 0


def _export(args: argparse.Namespace) -> int:
    df = load_dataset(args.dataset_id, data_dir=_data_dir(args.data_dir))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "csv":
        df.to_csv(output, index=False)
    elif args.format == "parquet":
        df.to_parquet(output, index=False)
    else:
        raise ValueError(f"Unsupported format: {args.format}")
    print(f"wrote {output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="macro-observatory")
    parser.add_argument("--data-dir", help="Data directory containing cache files")
    subparsers = parser.add_subparsers(dest="command", required=True)

    datasets_parser = subparsers.add_parser("datasets", help="List known datasets")
    datasets_parser.set_defaults(func=_datasets)

    update_parser = subparsers.add_parser("update", help="Update one source dataset")
    update_parser.add_argument("dataset_id")
    update_parser.set_defaults(func=_update)

    build_derived_parser = subparsers.add_parser("build-derived", help="Build one derived dataset")
    build_derived_parser.add_argument("dataset_id")
    build_derived_parser.set_defaults(func=_build_derived)

    publish_parser = subparsers.add_parser("publish", help="Publish browser-facing artifacts")
    publish_parser.add_argument("dataset_id")
    publish_parser.add_argument("--site-dir", help="Static site output directory")
    publish_parser.set_defaults(func=_publish)

    storage_report_parser = subparsers.add_parser(
        "storage-report", help="Show known project data file sizes"
    )
    storage_report_parser.add_argument("--site-dir", help="Static site output directory")
    storage_report_parser.set_defaults(func=_storage_report)

    serve_site_parser = subparsers.add_parser("serve-site", help="Serve the static site locally")
    serve_site_parser.add_argument("--site-dir", help="Static site directory")
    serve_site_parser.add_argument("--host", default=DEFAULT_HOST, help="Host interface to bind")
    serve_site_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    serve_site_parser.set_defaults(func=_serve_site)

    info_parser = subparsers.add_parser("info", help="Show dataset metadata")
    info_parser.add_argument("dataset_id")
    info_parser.set_defaults(func=_info)

    show_parser = subparsers.add_parser("show", help="Show recent cached rows")
    show_parser.add_argument("dataset_id")
    show_parser.add_argument("--rows", type=int, default=5)
    show_parser.set_defaults(func=_show)

    export_parser = subparsers.add_parser("export", help="Export one cached dataset")
    export_parser.add_argument("dataset_id")
    export_parser.add_argument("--format", choices=("csv", "parquet"), default="csv")
    export_parser.add_argument("--output", required=True)
    export_parser.set_defaults(func=_export)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
