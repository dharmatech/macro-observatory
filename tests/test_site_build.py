from pathlib import Path

import pytest

from macro_observatory import site_build


def test_build_static_site_runs_current_pipeline_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_get_dataset_spec(dataset_id: str, data_dir: Path) -> str:
        calls.append(("spec", dataset_id))
        assert data_dir == tmp_path / "data"
        return dataset_id

    def fake_update_dataset(spec: str) -> str:
        calls.append(("update", spec))
        return spec

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
    assert result.nojekyll_path == tmp_path / "site" / ".nojekyll"
    assert result.nojekyll_path.exists()


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
