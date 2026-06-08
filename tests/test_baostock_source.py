"""Tests for BaoStock source normalization helpers."""

import pytest

from core600.data_sources.baostock_source import (
    baostock_code_to_ts_code,
    baostock_exchange_to_internal,
)


def test_baostock_code_to_ts_code() -> None:
    """BaoStock codes should convert to project security identifiers."""

    assert baostock_code_to_ts_code("sh.600000") == "600000.SH"
    assert baostock_code_to_ts_code("sz.000001") == "000001.SZ"


def test_baostock_exchange_to_internal() -> None:
    """BaoStock code prefixes should map to exchange codes."""

    assert baostock_exchange_to_internal("sh.600000") == "SSE"
    assert baostock_exchange_to_internal("sz.000001") == "SZSE"


def test_baostock_code_rejects_unknown_exchange() -> None:
    """Unknown exchange prefixes should fail explicitly."""

    with pytest.raises(ValueError, match="Unsupported"):
        baostock_code_to_ts_code("xx.000001")
