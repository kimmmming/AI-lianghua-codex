"""Tushare data-source implementation for basic security metadata."""

from datetime import date
import os

import pandas as pd

from core600.data_sources.base import DataSource


class TushareDataSource(DataSource):
    """Tushare Pro implementation.

    The token must come from the `TUSHARE_TOKEN` environment variable or the
    explicit constructor argument. Tokens must never be committed to source.
    """

    def __init__(self, token: str | None = None) -> None:
        """Create a Tushare data source."""

        resolved_token = token or os.getenv("TUSHARE_TOKEN")
        if not resolved_token:
            raise RuntimeError(
                "Missing TUSHARE_TOKEN. Set it in the environment before downloading real data."
            )
        try:
            import tushare as ts
        except ImportError as error:
            raise RuntimeError("Missing dependency: install tushare before downloading data.") from error

        self._pro = ts.pro_api(resolved_token)

    def fetch_stock_basic(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Fetch current, delisted, and suspended stock basic information."""

        fields = ",".join(
            [
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
            ]
        )
        frames = [
            self._pro.stock_basic(list_status=status, fields=fields)
            for status in ["L", "D", "P"]
        ]
        return pd.concat(frames, ignore_index=True)

    def fetch_trade_calendar(
        self,
        start_date: date,
        end_date: date,
        exchange: str | None = None,
    ) -> pd.DataFrame:
        """Fetch trading calendar information."""

        return self._pro.trade_cal(
            exchange=exchange or "",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )

    def provider_name(self) -> str:
        """Return the provider name."""

        return "tushare"
