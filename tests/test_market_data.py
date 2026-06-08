"""Tests for market-data download preparation."""

from datetime import date

import pandas as pd
import pytest

from core600.market_data import prepare_daily_history, select_market_data_securities


def test_select_market_data_securities_uses_as_of_universe() -> None:
    """Only stocks listed as of the requested date should be downloaded."""

    stock_basic = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "source_code": "sz.000001",
                "list_date": "1991-04-03",
                "delist_date": None,
            },
            {
                "ts_code": "000002.SZ",
                "source_code": "sz.000002",
                "list_date": "2000-01-01",
                "delist_date": "2020-01-01",
            },
        ]
    )

    result = select_market_data_securities(stock_basic, date(2026, 6, 6))

    assert result["ts_code"].tolist() == ["000001.SZ"]


def test_prepare_daily_history_normalizes_numeric_and_dates() -> None:
    """Daily market records should be normalized for downstream scoring."""

    raw = pd.DataFrame(
        [
            {
                "date": "2026-06-05",
                "code": "sz.000001",
                "open": "10.0",
                "high": "11.0",
                "low": "9.9",
                "close": "10.5",
                "preclose": "10.1",
                "volume": "100",
                "amount": "1000",
                "tradestatus": "1",
                "pctChg": "1.0",
                "peTTM": "8.5",
                "pbMRQ": "1.1",
                "psTTM": "2.2",
                "pcfNcfTTM": "5.0",
                "isST": "0",
            }
        ]
    )

    result = prepare_daily_history(
        raw,
        ts_code="000001.SZ",
        source_code="sz.000001",
        as_of_date=date(2026, 6, 6),
        downloaded_at=pd.Timestamp("2026-06-06T00:00:00Z").to_pydatetime(),
    )

    assert result.loc[0, "trade_date"] == "2026-06-05"
    assert result.loc[0, "close"] == 10.5
    assert result.loc[0, "isST"] == 0


def test_prepare_daily_history_rejects_code_mismatch() -> None:
    """Provider records must match the requested security identifier."""

    raw = pd.DataFrame(
        [
            {
                "date": "2026-06-05",
                "code": "sh.600000",
                "open": "10.0",
                "high": "11.0",
                "low": "9.9",
                "close": "10.5",
                "preclose": "10.1",
                "volume": "100",
                "amount": "1000",
                "tradestatus": "1",
                "pctChg": "1.0",
                "peTTM": "8.5",
                "pbMRQ": "1.1",
                "psTTM": "2.2",
                "pcfNcfTTM": "5.0",
                "isST": "0",
            }
        ]
    )

    with pytest.raises(ValueError, match="mismatch"):
        prepare_daily_history(
            raw,
            ts_code="000001.SZ",
            source_code="sz.000001",
            as_of_date=date(2026, 6, 6),
            downloaded_at=pd.Timestamp("2026-06-06T00:00:00Z").to_pydatetime(),
        )


def test_select_market_data_securities_rejects_invalid_max() -> None:
    """max_securities should be positive when provided."""

    stock_basic = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "source_code": "sz.000001",
                "list_date": "1991-04-03",
                "delist_date": None,
            }
        ]
    )

    with pytest.raises(ValueError, match="max_securities"):
        select_market_data_securities(stock_basic, date(2026, 6, 6), max_securities=0)
