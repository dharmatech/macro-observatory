"""Storage diagnostics for generated data files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from macro_observatory.publish import DEFAULT_SITE_DIR, PUBLISH_CONFIGS
from macro_observatory.registry import DEFAULT_DATA_DIR, build_registry

SIZE_UNIT = "KB"
BYTES_PER_KB = 1024
TABLE_HEADER = "Group              Size KB  Modified             File"
TABLE_SEPARATOR = "----------------  -------  -------------------  ----"
TOTALS_HEADER = "Totals"


@dataclass(frozen=True)
class StorageReportEntry:
    """One expected project data file and its local storage state."""

    group: str
    path: Path
    size_bytes: int | None
    modified: datetime | None


@dataclass(frozen=True)
class StorageReport:
    """Storage diagnostics for known cache, metadata, and published files."""

    entries: tuple[StorageReportEntry, ...]

    @property
    def totals_by_group(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for entry in self.entries:
            if entry.size_bytes is None:
                totals.setdefault(entry.group, 0)
                continue
            totals[entry.group] = totals.get(entry.group, 0) + entry.size_bytes
        return totals

    @property
    def overall_total_bytes(self) -> int:
        return sum(size for size in self.totals_by_group.values())


def _site_artifact_paths(site_dir: Path) -> list[Path]:
    data_dir = site_dir / "data"
    paths: list[Path] = []
    for config in PUBLISH_CONFIGS.values():
        paths.extend(
            [
                data_dir / f"{config.artifact_stem}.json",
                data_dir / f"{config.artifact_stem}.csv",
                data_dir / f"{config.artifact_stem}-metadata.json",
            ]
        )
    return paths


def _entry(group: str, path: Path) -> StorageReportEntry:
    if not path.exists():
        return StorageReportEntry(group=group, path=path, size_bytes=None, modified=None)
    stat = path.stat()
    return StorageReportEntry(
        group=group,
        path=path,
        size_bytes=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime),
    )


def build_storage_report(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    site_dir: Path = DEFAULT_SITE_DIR,
) -> StorageReport:
    """Build a storage report for known project data files."""
    registry = build_registry(data_dir)
    entries: list[StorageReportEntry] = []

    for spec in registry.values():
        group = "source cache" if spec.kind == "source" else "derived cache"
        entries.append(_entry(group, spec.cache_path))

    for spec in registry.values():
        entries.append(_entry("metadata", spec.metadata_path))

    for path in _site_artifact_paths(site_dir):
        entries.append(_entry("site data", path))

    return StorageReport(entries=tuple(entries))


def _size_kb(size_bytes: int) -> float:
    return size_bytes / BYTES_PER_KB


def _format_size_kb(size_bytes: int | None) -> str:
    if size_bytes is None:
        return ""
    return f"{_size_kb(size_bytes):,.1f}"


def _format_modified(modified: datetime | None) -> str:
    if modified is None:
        return "missing"
    return modified.strftime("%Y-%m-%d %H:%M:%S")


def _format_path(path: Path) -> str:
    return path.as_posix()


def _format_entry(entry: StorageReportEntry) -> str:
    return (
        f"{entry.group:<16}  "
        f"{_format_size_kb(entry.size_bytes):>7}  "
        f"{_format_modified(entry.modified):<19}  "
        f"{_format_path(entry.path)}"
    )


def _format_total(group: str, size_bytes: int) -> str:
    return f"{group:<16}  {_format_size_kb(size_bytes):>7} {SIZE_UNIT}"


def render_storage_report(report: StorageReport) -> str:
    """Render a storage report as fixed-width text."""
    lines = [TABLE_HEADER, TABLE_SEPARATOR]
    lines.extend(_format_entry(entry) for entry in report.entries)
    lines.append("")
    lines.append(TOTALS_HEADER)
    for group, size_bytes in report.totals_by_group.items():
        lines.append(_format_total(group, size_bytes))
    lines.append(_format_total("overall", report.overall_total_bytes))
    return "\n".join(lines)
