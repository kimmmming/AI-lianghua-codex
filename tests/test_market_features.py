"""Tests for market feature calculations."""

from datetime import date, timedelta

import pandas as pd

from core600.market_features import calculate_market_features, max_drawdown


def make_market_frame(days: int = 130) -> pd.DataFrame:
    """Create deterministic market records for one security."""

    start = date(2026, 1, 1)
    return pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "trade_date": (start + timedelta(days=idx)).isoformat(),
                "close": 10 + idx * 0.1,
                "amount": 1000 + idx,
                "tradestatus": 1,
                "pctChg": 1.0,
                "peTTM": 8.0,
                "pbMRQ": 1.1,
                "psTTM": 2.0,
                "pcfNcfTTM": 4.0,
                "isST": 0,
            }
            for idx in range(days)
        ]
    )


def test_max_drawdown() -> None:
    """Maximum drawdown should be the worst peak-to-trough loss."""

    assert max_drawdown(pd.Series([10, 12, 9, 11])) == -0.25


def test_calculate_market_features_outputs_one_row_per_security() -> None:
    """Market features should aggregate daily rows into security-level records."""

    result = calculate_market_features(make_market_frame(), date(2026, 6, 6))

    assert len(result) == 1
    assert result.loc[0, "ts_code"] == "000001.SZ"
    assert result.loc[0, "valid_trading_days_60d"] == 60
    assert not bool(result.loc[0, "has_st_60d"])


def test_calculate_market_features_flags_recent_st() -> None:
    """Recent ST flags should be preserved for hard exclusions."""

    frame = make_market_frame()
    frame.loc[len(frame) - 1, "isST"] = 1

    result = calculate_market_features(frame, date(2026, 6, 6))

    assert bool(result.loc[0, "has_st_60d"])
