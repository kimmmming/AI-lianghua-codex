"""Tests for BaoStock source stock filtering."""

import pandas as pd

from core600.data_sources.baostock_source import BaoStockDataSource


class FakeLoginResult:
    """Fake BaoStock login result."""

    error_code = "0"
    error_msg = ""


class FakeQueryResult:
    """Fake BaoStock query result."""

    fields = ["code", "code_name", "ipoDate", "outDate", "type", "status"]
    error_code = "0"
    error_msg = ""

    def __init__(self) -> None:
        """Create fake rows."""

        self._rows = [
            ["sh.600000", "Stock A", "1999-11-10", "", "1", "1"],
            ["sh.000001", "Index A", "1991-07-15", "", "2", "1"],
        ]
        self._index = -1

    def next(self) -> bool:
        """Advance to the next row."""

        self._index += 1
        return self._index < len(self._rows)

    def get_row_data(self) -> list[str]:
        """Return the current row."""

        return self._rows[self._index]


class FakeBaoStockModule:
    """Fake baostock module for source tests."""

    def __init__(self) -> None:
        """Track logout calls."""

        self.logout_calls = 0

    def login(self) -> FakeLoginResult:
        """Return fake login result."""

        return FakeLoginResult()

    def logout(self) -> None:
        """Do nothing."""

        self.logout_calls += 1

    def query_stock_basic(self) -> FakeQueryResult:
        """Return fake stock basic query."""

        return FakeQueryResult()


def test_baostock_source_filters_to_stock_type(monkeypatch) -> None:
    """BaoStock source should keep only stock security type records."""

    source = BaoStockDataSource.__new__(BaoStockDataSource)
    source._bs = FakeBaoStockModule()
    source._logged_in = False

    result = source.fetch_stock_basic()

    assert isinstance(result, pd.DataFrame)
    assert result["ts_code"].tolist() == ["600000.SH"]
    assert result["security_type"].tolist() == ["1"]
