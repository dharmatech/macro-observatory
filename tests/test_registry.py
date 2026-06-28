from pathlib import Path

import pytest

from macro_observatory.cache import update_dataset
from macro_observatory.registry import build_registry, get_dataset_spec
from macro_observatory.sources.fred import FredSeriesAdapter
from macro_observatory.sources.nyfed import NyFedReverseRepoAdapter
from macro_observatory.sources.treasury import TreasuryFiscalDataAdapter


def test_registry_contains_initial_source_and_derived_datasets(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)

    assert sorted(registry) == [
        "fed_net_liquidity",
        "fred_resppllopnww",
        "fred_sp500",
        "fred_walcl",
        "nyfed_rrp",
        "treasury_dts_deposits_withdrawals_operating_cash",
        "treasury_dts_deposits_withdrawals_operating_cash_explorer",
        "treasury_dts_operating_cash_balance",
        "treasury_od_auctions_query",
        "treasury_securities_net_issuance",
        "treasury_tga",
    ]

    resp = registry["fred_resppllopnww"]
    assert resp.title == "Earnings Remittances Due to the U.S. Treasury (RESPPLLOPNWW)"
    assert resp.source_name == "FRED"
    assert resp.kind == "source"
    assert isinstance(resp.adapter, FredSeriesAdapter)
    assert resp.adapter.series_id == "RESPPLLOPNWW"
    assert resp.cache_path == tmp_path / "cache" / "sources" / "fred_resppllopnww.parquet"
    assert resp.metadata_path == tmp_path / "cache" / "metadata" / "fred_resppllopnww.json"
    assert resp.source_units == "millions of U.S. dollars"
    assert resp.display_units == "millions of U.S. dollars"

    sp500 = registry["fred_sp500"]
    assert sp500.title == "S&P 500 Index (SP500)"
    assert sp500.source_name == "FRED"
    assert sp500.kind == "source"
    assert isinstance(sp500.adapter, FredSeriesAdapter)
    assert sp500.adapter.series_id == "SP500"
    assert sp500.cache_path == tmp_path / "cache" / "sources" / "fred_sp500.parquet"
    assert sp500.metadata_path == tmp_path / "cache" / "metadata" / "fred_sp500.json"
    assert sp500.source_units == "index points"
    assert sp500.display_units == "index points"

    rrp = registry["nyfed_rrp"]
    assert rrp.title == "New York Fed Reverse Repo Operations (RRP)"
    assert rrp.source_name == "New York Fed"
    assert rrp.kind == "source"
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
    assert treasury.kind == "source"
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

    deposits_withdrawals = registry["treasury_dts_deposits_withdrawals_operating_cash"]
    assert (
        deposits_withdrawals.title
        == "Treasury Daily Treasury Statement Deposits and Withdrawals of Operating Cash"
    )
    assert deposits_withdrawals.source_name == "Treasury Fiscal Data"
    assert deposits_withdrawals.kind == "source"
    assert isinstance(deposits_withdrawals.adapter, TreasuryFiscalDataAdapter)
    assert deposits_withdrawals.date_column == "record_date"
    assert deposits_withdrawals.primary_key == (
        "record_date",
        "account_type",
        "transaction_type",
        "transaction_catg",
        "src_line_nbr",
    )
    assert deposits_withdrawals.cache_path == (
        tmp_path / "cache" / "sources" / "treasury_dts_deposits_withdrawals_operating_cash.parquet"
    )
    assert deposits_withdrawals.metadata_path == (
        tmp_path / "cache" / "metadata" / "treasury_dts_deposits_withdrawals_operating_cash.json"
    )
    assert deposits_withdrawals.source_units == "millions of U.S. dollars"
    assert deposits_withdrawals.display_units == "millions of U.S. dollars"

    auctions = registry["treasury_od_auctions_query"]
    assert auctions.title == "Treasury Auctions Query"
    assert auctions.source_name == "Treasury Fiscal Data"
    assert auctions.kind == "source"
    assert isinstance(auctions.adapter, TreasuryFiscalDataAdapter)
    assert auctions.date_column == "record_date"
    assert auctions.primary_key == (
        "record_date",
        "cusip",
        "auction_date",
        "issue_date",
        "maturity_date",
    )
    assert (
        auctions.cache_path == tmp_path / "cache" / "sources" / "treasury_od_auctions_query.parquet"
    )
    assert (
        auctions.metadata_path
        == tmp_path / "cache" / "metadata" / "treasury_od_auctions_query.json"
    )
    assert auctions.source_units == "U.S. dollars"
    assert auctions.display_units == "U.S. dollars"

    tga = registry["treasury_tga"]
    assert tga.title == "Treasury General Account (TGA)"
    assert tga.source_name == "Macro Observatory Derived"
    assert tga.kind == "derived"
    assert tga.adapter is None
    assert tga.date_column == "date"
    assert tga.primary_key == ("date",)
    assert tga.cache_path == tmp_path / "cache" / "derived" / "treasury_tga.parquet"
    assert tga.metadata_path == tmp_path / "cache" / "metadata" / "treasury_tga.json"
    assert tga.source_units == "millions of U.S. dollars"
    assert tga.display_units == "millions of U.S. dollars"

    tga_explorer = registry["treasury_dts_deposits_withdrawals_operating_cash_explorer"]
    assert tga_explorer.title == "Treasury DTS Deposits and Withdrawals Explorer Dataset"
    assert tga_explorer.source_name == "Macro Observatory Derived"
    assert tga_explorer.kind == "derived"
    assert tga_explorer.adapter is None
    assert tga_explorer.date_column == "record_date"
    assert tga_explorer.cache_path == (
        tmp_path
        / "cache"
        / "derived"
        / "treasury_dts_deposits_withdrawals_operating_cash_explorer.parquet"
    )
    assert tga_explorer.metadata_path == (
        tmp_path
        / "cache"
        / "metadata"
        / "treasury_dts_deposits_withdrawals_operating_cash_explorer.json"
    )
    assert tga_explorer.source_units == "millions of U.S. dollars"
    assert tga_explorer.display_units == "millions of U.S. dollars"

    treasury_securities = registry["treasury_securities_net_issuance"]
    assert treasury_securities.title == "Treasury Securities Net Issuance"
    assert treasury_securities.source_name == "Macro Observatory Derived"
    assert treasury_securities.kind == "derived"
    assert treasury_securities.adapter is None
    assert treasury_securities.date_column == "date"
    assert treasury_securities.primary_key == ("frequency", "date", "security_type")
    assert treasury_securities.cache_path == (
        tmp_path / "cache" / "derived" / "treasury_securities_net_issuance.parquet"
    )
    assert treasury_securities.metadata_path == (
        tmp_path / "cache" / "metadata" / "treasury_securities_net_issuance.json"
    )
    assert treasury_securities.source_units == "U.S. dollars"
    assert treasury_securities.display_units == "U.S. dollars"

    net_liquidity = registry["fed_net_liquidity"]
    assert net_liquidity.title == "Fed Net Liquidity"
    assert net_liquidity.source_name == "Macro Observatory Derived"
    assert net_liquidity.kind == "derived"
    assert net_liquidity.adapter is None
    assert net_liquidity.date_column == "date"
    assert net_liquidity.primary_key == ("date",)
    assert net_liquidity.cache_path == tmp_path / "cache" / "derived" / "fed_net_liquidity.parquet"
    assert net_liquidity.metadata_path == tmp_path / "cache" / "metadata" / "fed_net_liquidity.json"
    assert net_liquidity.source_units == "U.S. dollars"
    assert net_liquidity.display_units == "U.S. dollars"


def test_get_dataset_spec_error_lists_known_ids(tmp_path: Path) -> None:
    try:
        get_dataset_spec("missing", tmp_path)
    except KeyError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected KeyError")

    assert "fed_net_liquidity" in message
    assert "fred_resppllopnww" in message
    assert "fred_sp500" in message
    assert "fred_walcl" in message
    assert "nyfed_rrp" in message
    assert "treasury_dts_deposits_withdrawals_operating_cash" in message
    assert "treasury_dts_deposits_withdrawals_operating_cash_explorer" in message
    assert "treasury_dts_operating_cash_balance" in message
    assert "treasury_od_auctions_query" in message
    assert "treasury_securities_net_issuance" in message
    assert "treasury_tga" in message


def test_update_dataset_rejects_derived_specs(tmp_path: Path) -> None:
    spec = get_dataset_spec("treasury_tga", tmp_path)

    with pytest.raises(ValueError, match="build-derived"):
        update_dataset(spec)
