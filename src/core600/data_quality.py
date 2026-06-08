"""Data-quality checks for Core 600 inputs and outputs."""

from datetime import date

import pandas as pd


def require_columns(frame: pd.DataFrame, required_columns: set[str]) -> None:
    """Validate that required columns are present."""

    missing_columns = required_columns - set(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")


def validate_announcement_dates(frame: pd.DataFrame, as_of_date: date) -> None:
    """Validate financial dates and reject records announced after as_of_date."""

    require_columns(frame, {"report_period", "announcement_date"})

    report_periods = pd.to_datetime(frame["report_period"], errors="coerce").dt.date
    announcement_dates = pd.to_datetime(frame["announcement_date"], errors="coerce").dt.date
    if report_periods.isna().any() or announcement_dates.isna().any():
        raise ValueError("Financial records contain missing or invalid financial dates.")
    if (announcement_dates > as_of_date).any():
        raise ValueError("Found financial records announced after as_of_date.")


def validate_unique_security_ids(frame: pd.DataFrame, id_column: str = "ts_code") -> None:
    """Validate that security identifiers are unique."""

    if id_column not in frame.columns:
        raise ValueError(f"Missing required column: {id_column}")
    if frame[id_column].duplicated().any():
        raise ValueError(f"Duplicate security identifiers found in {id_column}.")


def validate_listing_dates(frame: pd.DataFrame) -> None:
    """Validate security identity and listing-date consistency."""

    require_columns(frame, {"ts_code", "list_date", "delist_date"})
    validate_unique_security_ids(frame)

    list_dates = pd.to_datetime(frame["list_date"], errors="coerce").dt.date
    delist_dates = pd.to_datetime(frame["delist_date"], errors="coerce").dt.date
    if list_dates.isna().any():
        raise ValueError("Security records contain missing or invalid list_date.")

    has_delist_date = delist_dates.notna()
    invalid_order = has_delist_date & (list_dates >= delist_dates)
    if invalid_order.any():
        raise ValueError("Security records contain list_date that is not before delist_date.")


def validate_trade_calendar(frame: pd.DataFrame) -> None:
    """Validate trading-calendar schema and uniqueness."""

    require_columns(frame, {"exchange", "cal_date", "is_open"})
    calendar_dates = pd.to_datetime(frame["cal_date"], errors="coerce").dt.date
    if calendar_dates.isna().any():
        raise ValueError("Trade calendar contains missing or invalid cal_date.")
    if frame[["exchange", "cal_date"]].duplicated().any():
        raise ValueError("Trade calendar contains duplicated exchange/cal_date rows.")
    invalid_open_flags = ~frame["is_open"].isin([0, 1, "0", "1"])
    if invalid_open_flags.any():
        raise ValueError("Trade calendar contains invalid is_open values.")
