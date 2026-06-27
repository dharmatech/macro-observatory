from __future__ import annotations

from pathlib import Path

import pytest

from macro_observatory.cli import build_parser
from macro_observatory.server import SiteDirectoryError, display_url, resolve_site_dir


def test_resolve_site_dir_accepts_existing_directory(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    assert resolve_site_dir(site_dir) == site_dir.resolve()


def test_resolve_site_dir_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(SiteDirectoryError, match="does not exist"):
        resolve_site_dir(tmp_path / "missing-site")


def test_display_url_uses_localhost_for_local_bindings() -> None:
    assert display_url("127.0.0.1", 8123) == "http://localhost:8123/"
    assert display_url("0.0.0.0", 8123) == "http://localhost:8123/"
    assert display_url("example.test", 8123) == "http://example.test:8123/"


def test_serve_site_parser_accepts_site_dir_host_and_port() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "serve-site",
            "--site-dir",
            "scratch-site",
            "--host",
            "0.0.0.0",
            "--port",
            "8123",
        ]
    )

    assert args.command == "serve-site"
    assert args.site_dir == "scratch-site"
    assert args.host == "0.0.0.0"
    assert args.port == 8123
