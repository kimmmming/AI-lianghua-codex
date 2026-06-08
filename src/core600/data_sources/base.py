"""Abstract data-source contract for A-share data."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Protocol

import pandas as pd


class SupportsDataFrame(Protocol):
    """Protocol for objects that can be represented as a DataFrame."""

    def to_dataframe(self) -> pd.DataFrame:
        """Return the object as a DataFrame."""


class DataSource(ABC):
    """Abstract interface for replaceable market data providers."""

    @abstractmethod
    def fetch_stock_basic(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Fetch stock identity, listing status, and listing date information."""

    @abstractmethod
    def fetch_trade_calendar(
        self,
        start_date: date,
        end_date: date,
        exchange: str | None = None,
    ) -> pd.DataFrame:
        """Fetch exchange trading calendar records for a date range."""

    @abstractmethod
    def provider_name(self) -> str:
        """Return a stable provider name for metadata and audit logs."""
