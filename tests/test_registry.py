from pathlib import Path

from macro_observatory.registry import build_registry, get_dataset_spec
from macro_observatory.sources.fred import FredSeriesAdapter
from macro_observatory.sources.nyfed import NyFedReverseRepoAdapter
from macro_observatory.sources.treasury import TreasuryFiscalDataAdapter


def test_registry_contains_initial_source_datasets(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)

    assert sorted(registry) == [
        "fred_resppllopnww",
        "fred_walcl",
        "nyfed_rrp",
        "treasury_dts_operating_cash_balance",
    ]

    resp = registry["fred_resppllopnww"]
    assert resp.title == "Earnings Remittances Due to the U.S. Treasury (RESPPLLOPNWW)"
    assert resp.source_name == "FRED"
    assert isinstance(resp.adapter, FredSeriesAdapter)
    assert resp.adapter.series_id == "RESPPLLOPNWW"
    assert resp.cache_path == tmp_path / "cache" / "sources" / "fred_resppllopnww.parquet"
    assert resp.metadata_path == tmp_path / "cache" / "metadata" / "fred_resppllopnww.json"
    assert resp.source_units == "millions of U.S. dollars"
    assert resp.display_units == "millions of U.S. dollars"

    rrp = registry["nyfed_rrp"]
    assert rrp.title == "New York Fed Reverse Repo Operations (RRP)"
    assert rrp.source_name == "New York Fed"
    assert isinstance(rrp.adapter, NyFedReverseRepoAdapter)
    assert rrp.date_column == "operationDate"
    assert rrp.primary_key == ("operationDate",)
    assert rrp.cache_path == tmp_path / "cache" / "sources" / "nyfed_rrp.parquet"
    assert rrp.metadata_path == tmp_path / "cache" / "metadata" / "nyfed_rrp.json"
    assert rrp.source_units == "U.S. dollars"
    assert rrp.display_units == "U.S. dollars"

    treasury = registry["treasury_dts_operating_cash_balance"]
    assert treasury.title == "Treasury Daily Treasury Statement Operating Cash Balance"
    assert treasury.source_name == "Treasury Fiscal Data"
    assert isinstance(treasury.adapter, TreasuryFiscalDataAdapter)
    assert treasury.date_column == "record_date"
    assert treasury.primary_key == ("record_date", "account_type", "src_line_nbr")
    assert (
        treasury.cache_path
        == tmp_path / "cache" / "sources" / "treasury_dts_operating_cash_balance.parquet"
    )
    assert (
        treasury.metadata_path
        == tmp_path / "cache" / "metadata" / "treasury_dts_operating_cash_balance.json"
    )
    assert treasury.source_units == "millions of U.S. dollars"
    assert treasury.display_units == "millions of U.S. dollars"


def test_get_dataset_spec_error_lists_known_ids(tmp_path: Path) -> None:
    try:
        get_dataset_spec("missing", tmp_path)
    except KeyError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected KeyError")

    assert "fred_resppllopnww" in message
    assert "fred_walcl" in message
    assert "nyfed_rrp" in message
    assert "treasury_dts_operating_cash_balance" in message
