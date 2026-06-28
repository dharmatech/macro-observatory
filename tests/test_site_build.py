from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest

from macro_observatory import site_build
from macro_observatory.models import UpdateResult


@dataclass(frozen=True)
class FakeSpec:
    cache_path: Path
    metadata_path: Path
    id: str = ""
    kind: Literal["source", "derived"] = "source"


def _write_fake_source_cache(data_dir: Path, dataset_id: str) -> None:
    cache_path = data_dir / "cache" / "sources" / f"{dataset_id}.parquet"
    metadata_path = data_dir / "cache" / "metadata" / f"{dataset_id}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("cache", encoding="utf-8")
    metadata_path.write_text("{}", encoding="utf-8")


def _fake_source_spec(data_dir: Path, dataset_id: str) -> FakeSpec:
    return FakeSpec(
        id=dataset_id,
        cache_path=data_dir / "cache" / "sources" / f"{dataset_id}.parquet",
        metadata_path=data_dir / "cache" / "metadata" / f"{dataset_id}.json",
    )


def _fake_update_result(data_dir: Path, dataset_id: str) -> UpdateResult:
    return UpdateResult(
        dataset_id=dataset_id,
        rows_before=0,
        rows_fetched=0,
        rows_after=0,
        min_date=None,
        max_date=None,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        cache_path=data_dir / "cache" / "sources" / f"{dataset_id}.parquet",
        metadata_path=data_dir / "cache" / "metadata" / f"{dataset_id}.json",
    )


def test_build_static_site_runs_current_pipeline_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_get_dataset_spec(dataset_id: str, data_dir: Path) -> str:
        calls.append(("spec", dataset_id))
        assert data_dir == tmp_path / "data"
        return dataset_id

    def fake_update_dataset(spec: str) -> UpdateResult:
        calls.append(("update", spec))
        return _fake_update_result(tmp_path / "data", spec)

    def fake_build_derived_dataset(dataset_id: str, *, data_dir: Path) -> str:
        calls.append(("build-derived", dataset_id))
        assert data_dir == tmp_path / "data"
        return dataset_id

    def fake_publish_dataset(dataset_id: str, *, data_dir: Path, site_dir: Path) -> str:
        calls.append(("publish", dataset_id))
        assert data_dir == tmp_path / "data"
        assert site_dir == tmp_path / "site"
        return dataset_id

    monkeypatch.setattr(site_build, "get_dataset_spec", fake_get_dataset_spec)
    monkeypatch.setattr(site_build, "update_dataset", fake_update_dataset)
    monkeypatch.setattr(site_build, "build_derived_dataset", fake_build_derived_dataset)
    monkeypatch.setattr(site_build, "publish_dataset", fake_publish_dataset)

    result = site_build.build_static_site(
        data_dir=tmp_path / "data",
        site_dir=tmp_path / "site",
    )

    expected_calls: list[tuple[str, str]] = []
    for dataset_id in site_build.SOURCE_DATASET_IDS:
        expected_calls.extend([("spec", dataset_id), ("update", dataset_id)])
    expected_calls.extend(
        ("build-derived", dataset_id) for dataset_id in site_build.DERIVED_DATASET_IDS
    )
    expected_calls.extend(("publish", dataset_id) for dataset_id in site_build.PUBLISH_DATASET_IDS)
    assert calls == expected_calls
    assert result.source_update_mode == "update"
    assert result.source_dataset_ids == site_build.SOURCE_DATASET_IDS
    assert result.nojekyll_path == tmp_path / "site" / ".nojekyll"
    assert result.nojekyll_path.exists()


def test_build_static_site_from_cache_skips_source_updates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    data_dir = tmp_path / "data"

    for dataset_id in site_build.SOURCE_DATASET_IDS:
        _write_fake_source_cache(data_dir, dataset_id)

    def fake_get_dataset_spec(dataset_id: str, data_dir_arg: Path) -> FakeSpec:
        calls.append(("spec", dataset_id))
        assert data_dir_arg == data_dir
        return _fake_source_spec(data_dir, dataset_id)

    def fail_update_dataset(spec: FakeSpec) -> str:
        raise AssertionError(f"from-cache build should not update sources: {spec}")

    def fake_build_derived_dataset(dataset_id: str, *, data_dir: Path) -> str:
        calls.append(("build-derived", dataset_id))
        assert data_dir == tmp_path / "data"
        return dataset_id

    def fake_publish_dataset(dataset_id: str, *, data_dir: Path, site_dir: Path) -> str:
        calls.append(("publish", dataset_id))
        assert data_dir == tmp_path / "data"
        assert site_dir == tmp_path / "site"
        return dataset_id

    monkeypatch.setattr(site_build, "get_dataset_spec", fake_get_dataset_spec)
    monkeypatch.setattr(site_build, "update_dataset", fail_update_dataset)
    monkeypatch.setattr(site_build, "build_derived_dataset", fake_build_derived_dataset)
    monkeypatch.setattr(site_build, "publish_dataset", fake_publish_dataset)

    result = site_build.build_static_site(
        data_dir=data_dir,
        site_dir=tmp_path / "site",
        from_cache=True,
    )

    expected_calls: list[tuple[str, str]] = [
        ("spec", dataset_id) for dataset_id in site_build.SOURCE_DATASET_IDS
    ]
    expected_calls.extend(
        ("build-derived", dataset_id) for dataset_id in site_build.DERIVED_DATASET_IDS
    )
    expected_calls.extend(("publish", dataset_id) for dataset_id in site_build.PUBLISH_DATASET_IDS)
    assert calls == expected_calls
    assert result.source_update_mode == "from-cache"
    assert result.source_dataset_ids == ()
    assert result.source_results == ()
    assert result.nojekyll_path == tmp_path / "site" / ".nojekyll"
    assert result.nojekyll_path.exists()


def test_build_static_site_targeted_updates_only_selected_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    data_dir = tmp_path / "data"
    selected_dataset_ids = (
        "nyfed_rrp",
        "nyfed_rrp",
        "treasury_dts_operating_cash_balance",
    )

    for dataset_id in site_build.SOURCE_DATASET_IDS:
        _write_fake_source_cache(data_dir, dataset_id)

    def fake_get_dataset_spec(dataset_id: str, data_dir_arg: Path) -> FakeSpec:
        calls.append(("spec", dataset_id))
        assert data_dir_arg == data_dir
        return _fake_source_spec(data_dir, dataset_id)

    def fake_update_dataset(spec: FakeSpec) -> UpdateResult:
        calls.append(("update", spec.id))
        return _fake_update_result(data_dir, spec.id)

    def fake_build_derived_dataset(dataset_id: str, *, data_dir: Path) -> str:
        calls.append(("build-derived", dataset_id))
        assert data_dir == tmp_path / "data"
        return dataset_id

    def fake_publish_dataset(dataset_id: str, *, data_dir: Path, site_dir: Path) -> str:
        calls.append(("publish", dataset_id))
        assert data_dir == tmp_path / "data"
        assert site_dir == tmp_path / "site"
        return dataset_id

    monkeypatch.setattr(site_build, "get_dataset_spec", fake_get_dataset_spec)
    monkeypatch.setattr(site_build, "update_dataset", fake_update_dataset)
    monkeypatch.setattr(site_build, "build_derived_dataset", fake_build_derived_dataset)
    monkeypatch.setattr(site_build, "publish_dataset", fake_publish_dataset)

    result = site_build.build_static_site(
        data_dir=data_dir,
        site_dir=tmp_path / "site",
        source_dataset_ids=selected_dataset_ids,
    )

    expected_selected = ("nyfed_rrp", "treasury_dts_operating_cash_balance")
    expected_calls: list[tuple[str, str]] = [
        ("spec", dataset_id) for dataset_id in expected_selected
    ]
    expected_calls.extend(("spec", dataset_id) for dataset_id in site_build.SOURCE_DATASET_IDS)
    expected_calls.extend(("update", dataset_id) for dataset_id in expected_selected)
    expected_calls.extend(
        ("build-derived", dataset_id) for dataset_id in site_build.DERIVED_DATASET_IDS
    )
    expected_calls.extend(("publish", dataset_id) for dataset_id in site_build.PUBLISH_DATASET_IDS)
    assert calls == expected_calls
    assert result.source_update_mode == "targeted"
    assert result.source_dataset_ids == expected_selected
    assert tuple(update.dataset_id for update in result.source_results) == expected_selected
    assert result.nojekyll_path == tmp_path / "site" / ".nojekyll"
    assert result.nojekyll_path.exists()


def test_build_static_site_targeted_fails_when_source_cache_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    data_dir = tmp_path / "data"

    def fake_get_dataset_spec(dataset_id: str, data_dir_arg: Path) -> FakeSpec:
        calls.append(("spec", dataset_id))
        assert data_dir_arg == data_dir
        return _fake_source_spec(data_dir, dataset_id)

    def fail_update_dataset(spec: FakeSpec) -> str:
        raise AssertionError(f"targeted build should validate cache before updating: {spec}")

    monkeypatch.setattr(site_build, "get_dataset_spec", fake_get_dataset_spec)
    monkeypatch.setattr(site_build, "update_dataset", fail_update_dataset)

    with pytest.raises(site_build.BuildSiteError, match="Cannot build from cache"):
        site_build.build_static_site(
            data_dir=data_dir,
            site_dir=tmp_path / "site",
            source_dataset_ids=("nyfed_rrp",),
        )

    assert calls == [
        ("spec", "nyfed_rrp"),
        *[("spec", dataset_id) for dataset_id in site_build.SOURCE_DATASET_IDS],
    ]


def test_build_static_site_from_cache_fails_when_source_cache_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    data_dir = tmp_path / "data"

    def fake_get_dataset_spec(dataset_id: str, data_dir_arg: Path) -> FakeSpec:
        calls.append(("spec", dataset_id))
        assert data_dir_arg == data_dir
        return _fake_source_spec(data_dir, dataset_id)

    def fail_update_dataset(spec: FakeSpec) -> str:
        raise AssertionError(f"from-cache build should not update sources: {spec}")

    monkeypatch.setattr(site_build, "get_dataset_spec", fake_get_dataset_spec)
    monkeypatch.setattr(site_build, "update_dataset", fail_update_dataset)

    with pytest.raises(site_build.BuildSiteError, match="Cannot build from cache"):
        site_build.build_static_site(
            data_dir=data_dir,
            site_dir=tmp_path / "site",
            from_cache=True,
        )

    assert calls == [("spec", dataset_id) for dataset_id in site_build.SOURCE_DATASET_IDS]


def test_build_static_site_rejects_source_dataset_with_from_cache(tmp_path: Path) -> None:
    with pytest.raises(site_build.BuildSiteError, match="cannot be combined"):
        site_build.build_static_site(
            data_dir=tmp_path / "data",
            site_dir=tmp_path / "site",
            from_cache=True,
            source_dataset_ids=("nyfed_rrp",),
        )


def test_build_static_site_rejects_derived_source_dataset(tmp_path: Path) -> None:
    with pytest.raises(site_build.BuildSiteError, match="is derived"):
        site_build.build_static_site(
            data_dir=tmp_path / "data",
            site_dir=tmp_path / "site",
            source_dataset_ids=("treasury_tga",),
        )


def test_build_static_site_rejects_unknown_source_dataset(tmp_path: Path) -> None:
    with pytest.raises(site_build.BuildSiteError, match="Unknown source dataset"):
        site_build.build_static_site(
            data_dir=tmp_path / "data",
            site_dir=tmp_path / "site",
            source_dataset_ids=("not_a_dataset",),
        )


def test_build_static_site_requires_fred_api_key_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    with pytest.raises(site_build.BuildSiteError, match="FRED_API_KEY is required"):
        site_build.build_static_site(
            data_dir=tmp_path / "data",
            site_dir=tmp_path / "site",
            require_fred_api_key=True,
        )
