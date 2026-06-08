"""BaoStock data-source implementation for free public basic data."""

from datetime import date

import pandas as pd

from core600.data_sources.base import DataSource


def baostock_code_to_ts_code(code: str) -> str:
    """Convert BaoStock code format like sh.600000 to 600000.SH."""

    try:
        exchange, symbol = code.split(".", maxsplit=1)
    except ValueError as error:
        raise ValueError(f"Invalid BaoStock code: {code}") from error
    exchange_map = {"sh": "SH", "sz": "SZ", "bj": "BJ"}
    if exchange not in exchange_map:
        raise ValueError(f"Unsupported BaoStock exchange prefix: {exchange}")
    return f"{symbol}.{exchange_map[exchange]}"


def baostock_exchange_to_internal(code: str) -> str:
    """Convert BaoStock code prefix to an internal exchange code."""

    if code.startswith("sh."):
        return "SSE"
    if code.startswith("sz."):
        return "SZSE"
    if code.startswith("bj."):
        return "BSE"
    raise ValueError(f"Unsupported BaoStock code prefix: {code}")


def collect_baostock_rows(query_result: object) -> pd.DataFrame:
    """Collect rows from a BaoStock query result into a DataFrame."""

    fields = list(getattr(query_result, "fields"))
    rows: list[list[str]] = []
    while query_result.error_code == "0" and query_result.next():
        rows.append(query_result.get_row_data())
    if query_result.error_code != "0":
        raise RuntimeError(f"BaoStock query failed: {query_result.error_msg}")
    return pd.DataFrame(rows, columns=fields)


class BaoStockDataSource(DataSource):
    """Free public data source backed by BaoStock."""

    def __init__(self) -> None:
        """Create a BaoStock data source."""

        try:
            import baostock as bs
        except ImportError as error:
            raise RuntimeError("Missing dependency: install baostock before downloading data.") from error
        self._bs = bs
        self._logged_in = False

    def login(self) -> None:
        """Open a BaoStock session if one is not already active."""

        if self._logged_in:
            return
        login_result = self._bs.login()
        if login_result.error_code != "0":
            raise RuntimeError(f"BaoStock login failed: {login_result.error_msg}")
        self._logged_in = True

    def logout(self) -> None:
        """Close an active BaoStock session."""

        if not self._logged_in:
            return
        self._bs.logout()
        self._logged_in = False

    def fetch_stock_basic(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Fetch stock identity, listing status, and listing dates."""

        already_logged_in = self._logged_in
        self.login()
        try:
            raw = collect_baostock_rows(self._bs.query_stock_basic())
        finally:
            if not already_logged_in:
                self.logout()

        if raw.empty:
            return pd.DataFrame(
                columns=[
                    "ts_code",
                    "symbol",
                    "name",
                    "area",
                    "industry",
                    "market",
                    "list_date",
                    "delist_date",
                    "list_status",
                    "exchange",
                    "source_code",
                    "security_type",
                ]
            )

        raw = raw.loc[raw["type"] == "1"].copy()
        frame = pd.DataFrame(
            {
                "ts_code": raw["code"].map(baostock_code_to_ts_code),
                "symbol": raw["code"].str.split(".", expand=True)[1],
                "name": raw["code_name"],
                "area": pd.NA,
                "industry": pd.NA,
                "market": pd.NA,
                "list_date": raw["ipoDate"],
                "delist_date": raw["outDate"].replace("", pd.NA),
                "list_status": raw["status"].map({"1": "L", "0": "D"}).fillna("UNKNOWN"),
                "exchange": raw["code"].map(baostock_exchange_to_internal),
                "source_code": raw["code"],
                "security_type": raw["type"],
            }
        )
        return frame

    def fetch_trade_calendar(
        self,
        start_date: date,
        end_date: date,
        exchange: str | None = None,
    ) -> pd.DataFrame:
        """Fetch trading calendar information."""

        already_logged_in = self._logged_in
        self.login()
        try:
            raw = collect_baostock_rows(
                self._bs.query_trade_dates(
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                )
            )
        finally:
            if not already_logged_in:
                self.logout()

        if raw.empty:
            return pd.DataFrame(columns=["exchange", "cal_date", "is_open"])
        return pd.DataFrame(
            {
                "exchange": exchange or "CN_A",
                "cal_date": raw["calendar_date"],
                "is_open": raw["is_trading_day"].astype(int),
            }
        )

    def fetch_daily_history(
        self,
        source_code: str,
        start_date: date,
        end_date: date,
        fields: tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        """Fetch daily market, valuation, trading-status, and ST fields."""

        selected_fields = fields or (
            "date",
            "code",
            "open",
            "high",
            "low",
            "close",
            "preclose",
            "volume",
            "amount",
            "tradestatus",
            "pctChg",
            "peTTM",
            "pbMRQ",
            "psTTM",
            "pcfNcfTTM",
            "isST",
        )
        already_logged_in = self._logged_in
        self.login()
        try:
            raw = collect_baostock_rows(
                self._bs.query_history_k_data_plus(
                    source_code,
                    ",".join(selected_fields),
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    frequency="d",
                    adjustflag="3",
                )
            )
        finally:
            if not already_logged_in:
                self.logout()
        return raw

    def fetch_stock_industry(self) -> pd.DataFrame:
        """Fetch stock industry classification records."""

        already_logged_in = self._logged_in
        self.login()
        try:
            raw = collect_baostock_rows(self._bs.query_stock_industry())
        finally:
            if not already_logged_in:
                self.logout()
        if raw.empty:
            return pd.DataFrame(
                columns=[
                    "update_date",
                    "ts_code",
                    "source_code",
                    "name",
                    "industry",
                    "industry_classification",
                ]
            )
        return pd.DataFrame(
            {
                "update_date": raw["updateDate"],
                "ts_code": raw["code"].map(baostock_code_to_ts_code),
                "source_code": raw["code"],
                "name": raw["code_name"],
                "industry": raw["industry"].replace("", pd.NA),
                "industry_classification": raw["industryClassification"],
            }
        )

    def fetch_financial_statement(
        self,
        source_code: str,
        year: int,
        quarter: int,
        statement: str,
    ) -> pd.DataFrame:
        """Fetch one BaoStock quarterly financial statement group."""

        query_map = {
            "profit": self._bs.query_profit_data,
            "operation": self._bs.query_operation_data,
            "growth": self._bs.query_growth_data,
            "balance": self._bs.query_balance_data,
            "cashflow": self._bs.query_cash_flow_data,
            "dupont": self._bs.query_dupont_data,
        }
        if statement not in query_map:
            raise ValueError(f"Unsupported financial statement group: {statement}")

        already_logged_in = self._logged_in
        self.login()
        try:
            raw = collect_baostock_rows(
                query_map[statement](code=source_code, year=year, quarter=quarter)
            )
        finally:
            if not already_logged_in:
                self.logout()
        return raw

    def provider_name(self) -> str:
        """Return the provider name."""

        return "baostock"
