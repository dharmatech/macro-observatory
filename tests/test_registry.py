from pathlib import Path

from macro_observatory.registry import build_registry, get_dataset_spec
from macro_observatory.sources.fred import FredSeriesAdapter


def test_registry_contains_initial_fred_sources(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)

    assert sorted(registry) == ["fred_resppllopnww", "fred_walcl"]

    resp = registry["fred_resppllopnww"]
    assert resp.title == "Earnings Remittances Due to the U.S. Treasury (RESPPLLOPNWW)"
    assert resp.source_name == "FRED"
    assert isinstance(resp.adapter, FredSeriesAdapter)
    assert resp.adapter.series_id == "RESPPLLOPNWW"
    assert resp.cache_path == tmp_path / "cache" / "sources" / "fred_resppllopnww.parquet"
    assert resp.metadata_path == tmp_path / "cache" / "metadata" / "fred_resppllopnww.json"
    assert resp.source_units == "millions of U.S. dollars"
    assert resp.display_units == "millions of U.S. dollars"


def test_get_dataset_spec_error_lists_known_ids(tmp_path: Path) -> None:
    try:
        get_dataset_spec("missing", tmp_path)
    except KeyError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected KeyError")

    assert "fred_resppllopnww" in message
    assert "fred_walcl" in message
