"""AKShare data-source placeholder.

AKShare is reserved as a supplemental or validation source after the primary
data schema has been defined.
"""

from datetime import date

import pandas as pd

from core600.data_sources.base import DataSource


class AKShareDataSource(DataSource):
    """Placeholder implementation for AKShare."""

    def fetch_stock_basic(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Fetch stock basic information.

        Raises:
            NotImplementedError: Stage 1 does not download real data.
        """

        raise NotImplementedError("AKShare integration is reserved for a later stage.")

    def fetch_trade_calendar(
        self,
        start_date: date,
        end_date: date,
        exchange: str | None = None,
    ) -> pd.DataFrame:
        """Fetch trading calendar information.

        Raises:
            NotImplementedError: Stage 1 does not download real data.
        """

        raise NotImplementedError("AKShare integration is reserved for a later stage.")

    def provider_name(self) -> str:
        """Return the provider name."""

        return "akshare"
