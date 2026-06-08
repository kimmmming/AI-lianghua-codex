"""Tests for no-lookahead safeguards."""

from datetime import date

import pandas as pd
import pytest

from core600.data_quality import validate_announcement_dates


def test_validate_announcement_dates_rejects_future_announcements() -> None:
    """Financial data announced after as_of_date must not be usable."""

    frame = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "report_period": "2025-12-31",
                "announcement_date": "2026-06-06",
            }
        ]
    )

    with pytest.raises(ValueError, match="after as_of_date"):
        validate_announcement_dates(frame, date(2026, 6, 5))


def test_validate_announcement_dates_requires_report_period() -> None:
    """Financial records must preserve report_period for auditability."""

    frame = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "announcement_date": "2026-06-05",
            }
        ]
    )

    with pytest.raises(ValueError, match="report_period"):
        validate_announcement_dates(frame, date(2026, 6, 5))


def test_validate_announcement_dates_rejects_missing_announcement_date() -> None:
    """Missing announcement dates are not safe to treat as usable data."""

    frame = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "report_period": "2025-12-31",
                "announcement_date": None,
            }
        ]
    )

    with pytest.raises(ValueError, match="missing or invalid"):
        validate_announcement_dates(frame, date(2026, 6, 5))
