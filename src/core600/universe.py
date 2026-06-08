"""Universe construction placeholders."""

from datetime import date

import pandas as pd

from core600.data_quality import validate_listing_dates


def build_universe_as_of(securities: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    """Return securities eligible for consideration by listing dates only."""

    validate_listing_dates(securities)

    frame = securities.copy()
    as_of_timestamp = pd.Timestamp(as_of_date)
    list_dates = pd.to_datetime(frame["list_date"])
    delist_dates = pd.to_datetime(frame["delist_date"], errors="coerce")
    is_listed = list_dates <= as_of_timestamp
    is_not_delisted = delist_dates.isna() | (delist_dates > as_of_timestamp)
    return frame.loc[is_listed & is_not_delisted].copy()
