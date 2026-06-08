"""Tests for command-line behavior."""

import pytest

from core600.cli import main


def test_download_basic_data_cli_fails_clearly_without_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should report missing token without pretending to download data."""

    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    with pytest.raises(SystemExit) as error:
        main(
            [
                "download-basic-data",
                "--source",
                "tushare",
                "--start-date",
                "2026-06-05",
                "--end-date",
                "2026-06-05",
                "--as-of-date",
                "2026-06-05",
            ]
        )

    assert error.value.code == 2
    assert "TUSHARE_TOKEN" in capsys.readouterr().err


def test_download_basic_data_cli_defaults_to_baostock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should use the free BaoStock source by default."""

    class FakeResult:
        stock_basic_rows = 1
        trade_calendar_rows = 1
        stock_basic_path = tmp_path / "stock.parquet"
        trade_calendar_path = tmp_path / "calendar.parquet"
        metadata_path = tmp_path / "metadata.json"

    captured = {}

    def fake_create_data_source(source_name: str):
        captured["source_name"] = source_name
        return object()

    def fake_download_basic_data(**kwargs):
        return FakeResult()

    monkeypatch.setattr("core600.cli.create_data_source", fake_create_data_source)
    monkeypatch.setattr("core600.cli.download_basic_data", fake_download_basic_data)

    exit_code = main(
        [
            "download-basic-data",
            "--start-date",
            "2026-06-05",
            "--end-date",
            "2026-06-05",
            "--as-of-date",
            "2026-06-05",
        ]
    )

    assert exit_code == 0
    assert captured["source_name"] == "baostock"
    assert "stock_basic_rows=1" in capsys.readouterr().out
