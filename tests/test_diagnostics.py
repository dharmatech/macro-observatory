from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import pytest

from macro_observatory.cli import main
from macro_observatory.diagnostics import build_storage_report, render_storage_report


def write_file(path: Path, size_bytes: int, modified: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size_bytes)
    timestamp = modified.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_build_storage_report_tracks_known_files_and_missing_files(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    site_dir = tmp_path / "site"
    write_file(
        data_dir / "cache" / "sources" / "fred_walcl.parquet",
        17_470,
        datetime(2024, 1, 2, 3, 4, 5),
    )
    write_file(
        site_dir / "data" / "fed-net-liquidity.json",
        1_384_525,
        datetime(2024, 1, 2, 3, 4, 5),
    )

    report = build_storage_report(data_dir=data_dir, site_dir=site_dir)

    assert any(
        entry.path.name == "fred_walcl.parquet"
        and entry.group == "source cache"
        and entry.size_bytes == 17_470
        for entry in report.entries
    )
    assert any(
        entry.path.name == "fed-net-liquidity.json"
        and entry.group == "site data"
        and entry.size_bytes == 1_384_525
        for entry in report.entries
    )
    assert report.totals_by_group["source cache"] == 17_470
    assert report.totals_by_group["site data"] == 1_384_525
    assert report.overall_total_bytes == 1_401_995
    assert any(
        entry.path.name == "nyfed_rrp.parquet" and entry.size_bytes is None
        for entry in report.entries
    )


def test_render_storage_report_uses_fixed_kb_columns_and_totals(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    site_dir = tmp_path / "site"
    modified = datetime(2024, 1, 2, 3, 4, 5)
    write_file(data_dir / "cache" / "sources" / "fred_walcl.parquet", 17_470, modified)
    write_file(site_dir / "data" / "fed-net-liquidity.json", 1_384_525, modified)

    text = render_storage_report(build_storage_report(data_dir=data_dir, site_dir=site_dir))

    assert "Group              Size KB  Modified             File" in text
    assert re.search(r"source cache\s+17\.1\s+2024-01-02 03:04:05", text)
    assert re.search(r"site data\s+1,352\.1\s+2024-01-02 03:04:05", text)
    assert "nyfed_rrp.parquet" in text
    assert "missing" in text
    assert "source cache         17.1 KB" in text
    assert "site data         1,352.1 KB" in text
    assert "overall           1,369.1 KB" in text
    assert " MB" not in text

    rows = [line for line in text.splitlines()[2:] if line and line != "Totals"]
    data_rows = [line for line in rows if not line.endswith(" KB")]
    size_fields = [line[18:25] for line in data_rows]
    assert all(len(size_field) == 7 for size_field in size_fields)
    assert "1,352.1" in size_fields


def test_storage_report_cli_uses_data_dir_and_site_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = tmp_path / "data"
    site_dir = tmp_path / "site"
    write_file(
        data_dir / "cache" / "derived" / "fed_net_liquidity.parquet",
        312_065,
        datetime(2024, 1, 2, 3, 4, 5),
    )

    exit_code = main(
        [
            "--data-dir",
            str(data_dir),
            "storage-report",
            "--site-dir",
            str(site_dir),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "derived cache" in output
    assert "304.8" in output
    assert (data_dir / "cache" / "derived" / "fed_net_liquidity.parquet").as_posix() in output
