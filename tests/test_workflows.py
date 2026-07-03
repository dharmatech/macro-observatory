from pathlib import Path


def test_scheduled_refresh_includes_treasurydirect_intraday_group() -> None:
    workflow = Path(".github/workflows/scheduled-refresh.yml").read_text(encoding="utf-8")

    assert 'cron: "7 16,17,18,19 * * 1-5"' in workflow
    assert "TreasuryDirect current window intraday" in workflow
    assert "treasurydirect_current_intraday" in workflow
    assert 'source_datasets="treasurydirect_securities_current"' in workflow
    assert 'build_args="--source-dataset treasurydirect_securities_current"' in workflow

    assert workflow.count('refresh_group="treasurydirect_current_intraday"') == 2
    assert workflow.count('requires_fred_api_key="false"') >= 8
