"""Tests for financial data preparation."""

from datetime import date

import pandas as pd

from core600.financial_data import prepare_financial_records, recent_quarters


def test_recent_quarters_newest_first() -> None:
    """Recent quarters should be returned newest first."""

    assert recent_quarters(date(2026, 6, 7), 4) == [(2026, 2), (2026, 1), (2025, 4), (2025, 3)]


def test_prepare_financial_records_filters_future_pub_date() -> None:
    """Financial records announced after as_of_date must be filtered out."""

    raw = pd.DataFrame(
        [
            {
                "code": "sz.000001",
                "pubDate": "2026-06-01",
                "statDate": "2026-03-31",
                "profit_roeAvg": "10.5",
            },
            {
                "code": "sz.000001",
                "pubDate": "2026-06-08",
                "statDate": "2026-03-31",
                "profit_roeAvg": "99.9",
            },
        ]
    )

    result = prepare_financial_records(
        raw,
        ts_code="000001.SZ",
        source_code="sz.000001",
        as_of_date=date(2026, 6, 7),
        downloaded_at=pd.Timestamp("2026-06-07T00:00:00Z").to_pydatetime(),
    )

    assert len(result) == 1
    assert result.loc[0, "announcement_date"] == "2026-06-01"
    assert result.loc[0, "profit_roeAvg"] == 10.5
