"""Tests for basic data download orchestration."""

from datetime import date
import json
from pathlib import Path

import pandas as pd
import pytest

from core600.basic_data import download_basic_data, prepare_stock_basic
from core600.data_sources.base import DataSource


class FakeDataSource(DataSource):
    """Small fake data source for deterministic tests."""

    def fetch_stock_basic(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Return fake stock-basic records."""

        return pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "Example A",
                    "area": "Shenzhen",
                    "industry": "Bank",
                    "market": "Main",
                    "list_date": "19910403",
                    "delist_date": None,
                    "list_status": "L",
                    "exchange": "SZSE",
                },
                {
                    "ts_code": "000002.SZ",
                    "symbol": "000002",
                    "name": "Example B",
                    "area": "Shenzhen",
                    "industry": "Real Estate",
                    "market": "Main",
                    "list_date": "20000101",
                    "delist_date": "20200101",
                    "list_status": "D",
                    "exchange": "SZSE",
                },
            ]
        )

    def fetch_trade_calendar(
        self,
        start_date: date,
        end_date: date,
        exchange: str | None = None,
    ) -> pd.DataFrame:
        """Return fake trade-calendar records."""

        return pd.DataFrame(
            [
                {
                    "exchange": exchange,
                    "cal_date": "20260605",
                    "is_open": 1,
                    "pretrade_date": "20260604",
                }
            ]
        )

    def provider_name(self) -> str:
        """Return the fake provider name."""

        return "fake"


def test_prepare_stock_basic_preserves_delisted_stock() -> None:
    """Delisted securities should remain in the basic stock table."""

    prepared = prepare_stock_basic(
        FakeDataSource().fetch_stock_basic(),
        as_of_date=date(2026, 6, 5),
        downloaded_at=pd.Timestamp("2026-06-05T00:00:00Z").to_pydatetime(),
    )

    assert prepared["list_status"].tolist() == ["L", "D"]


def test_download_basic_data_writes_paths_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Basic data download should write auditable outputs."""

    def fake_to_parquet(self: pd.DataFrame, path: Path, index: bool = False) -> None:
        path.write_text(self.to_csv(index=index), encoding="utf-8")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)

    result = download_basic_data(
        source=FakeDataSource(),
        output_dir=tmp_path,
        start_date=date(2026, 6, 5),
        end_date=date(2026, 6, 5),
        as_of_date=date(2026, 6, 5),
        exchanges=("SSE", "SZSE"),
    )

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))

    assert result.stock_basic_path.name == "stock_basic_2026-06-05.parquet"
    assert result.trade_calendar_path.name == "trade_calendar_2026-06-05.parquet"
    assert metadata["provider"] == "fake"
    assert metadata["stock_basic_rows"] == 2
    assert metadata["trade_calendar_rows"] == 2
