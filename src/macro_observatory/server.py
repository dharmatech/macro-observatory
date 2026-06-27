"""Local static-site server helpers."""

from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from macro_observatory.publish import DEFAULT_SITE_DIR

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class SiteDirectoryError(RuntimeError):
    """Raised when a static site directory cannot be served."""


def resolve_site_dir(site_dir: Path = DEFAULT_SITE_DIR) -> Path:
    """Resolve and validate a static site directory."""
    resolved = site_dir.resolve()
    if not resolved.exists():
        raise SiteDirectoryError(f"Static site directory does not exist: {site_dir}")
    if not resolved.is_dir():
        raise SiteDirectoryError(f"Static site path is not a directory: {site_dir}")
    return resolved


def display_url(host: str, port: int) -> str:
    """Return a browser-friendly URL for a local server binding."""
    display_host = "localhost" if host in {"127.0.0.1", "0.0.0.0", "::"} else host
    return f"http://{display_host}:{port}/"


def make_site_handler(site_dir: Path) -> type[SimpleHTTPRequestHandler]:
    """Create a request handler rooted at ``site_dir``."""
    directory = str(site_dir)

    class SiteRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=directory, **kwargs)

    return SiteRequestHandler


def serve_site(
    *,
    site_dir: Path = DEFAULT_SITE_DIR,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    """Serve the generated static site until interrupted."""
    resolved_site_dir = resolve_site_dir(site_dir)
    handler = make_site_handler(resolved_site_dir)
    with ThreadingHTTPServer((host, port), handler) as httpd:
        actual_port = int(httpd.server_address[1])
        print(f"Serving {resolved_site_dir} at {display_url(host, actual_port)}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Stopped.")
