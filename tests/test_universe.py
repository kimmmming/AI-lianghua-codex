"""Tests for universe construction."""

from datetime import date

import pandas as pd

from core600.universe import build_universe_as_of


def test_build_universe_as_of_includes_historical_delisted_before_delist() -> None:
    """A later-delisted stock remains eligible before its delisting date."""

    securities = pd.DataFrame(
        [
            {"ts_code": "000001.SZ", "list_date": "1991-04-03", "delist_date": None},
            {"ts_code": "000002.SZ", "list_date": "2000-01-01", "delist_date": "2020-01-01"},
            {"ts_code": "000003.SZ", "list_date": "2030-01-01", "delist_date": None},
        ]
    )

    result = build_universe_as_of(securities, date(2019, 12, 31))

    assert result["ts_code"].tolist() == ["000001.SZ", "000002.SZ"]


def test_build_universe_as_of_excludes_stock_after_delist_date() -> None:
    """A delisted stock should not remain eligible after delisting."""

    securities = pd.DataFrame(
        [
            {"ts_code": "000001.SZ", "list_date": "1991-04-03", "delist_date": None},
            {"ts_code": "000002.SZ", "list_date": "2000-01-01", "delist_date": "2020-01-01"},
        ]
    )

    result = build_universe_as_of(securities, date(2020, 1, 2))

    assert result["ts_code"].tolist() == ["000001.SZ"]


def test_build_universe_rejects_duplicate_security_ids() -> None:
    """The historical universe must not contain duplicated identifiers."""

    securities = pd.DataFrame(
        [
            {"ts_code": "000001.SZ", "list_date": "1991-04-03", "delist_date": None},
            {"ts_code": "000001.SZ", "list_date": "1991-04-03", "delist_date": None},
        ]
    )

    try:
        build_universe_as_of(securities, date(2026, 6, 5))
    except ValueError as error:
        assert "Duplicate security identifiers" in str(error)
    else:
        raise AssertionError("Expected duplicate security identifiers to be rejected.")
