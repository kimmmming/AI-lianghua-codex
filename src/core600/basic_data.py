"""Download and persist basic A-share security metadata."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
from pathlib import Path

import pandas as pd

from core600.data_quality import validate_listing_dates, validate_trade_calendar
from core600.data_sources.base import DataSource
from core600.reporting import output_path_with_as_of_date


@dataclass(frozen=True)
class BasicDataDownloadResult:
    """Paths and row counts from a basic-data download run."""

    stock_basic_path: Path
    trade_calendar_path: Path
    metadata_path: Path
    stock_basic_rows: int
    trade_calendar_rows: int


def normalize_tushare_date_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Normalize data-source date columns to pandas datetime values."""

    normalized = frame.copy()
    for column in columns:
        if column in normalized.columns:
            compact = pd.to_datetime(normalized[column], format="%Y%m%d", errors="coerce")
            flexible = pd.to_datetime(normalized[column], errors="coerce")
            normalized[column] = compact.fillna(flexible)
    return normalized


def stringify_datetime_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert datetime columns to ISO date/time strings for portable Parquet output."""

    converted = frame.copy()
    for column in columns:
        if column in converted.columns:
            values = pd.to_datetime(converted[column], errors="coerce")
            converted[column] = values.dt.strftime("%Y-%m-%d")
            converted.loc[values.isna(), column] = pd.NA
    if "downloaded_at_utc" in converted.columns:
        timestamps = pd.to_datetime(converted["downloaded_at_utc"], errors="coerce", utc=True)
        converted["downloaded_at_utc"] = timestamps.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return converted


def prepare_stock_basic(
    frame: pd.DataFrame,
    as_of_date: date,
    downloaded_at: datetime,
) -> pd.DataFrame:
    """Normalize and validate stock-basic records."""

    prepared = normalize_tushare_date_columns(frame, ["list_date", "delist_date"])
    prepared["as_of_date"] = pd.Timestamp(as_of_date)
    prepared["downloaded_at_utc"] = pd.Timestamp(downloaded_at)
    validate_listing_dates(prepared)
    return stringify_datetime_columns(prepared, ["list_date", "delist_date", "as_of_date"])


def prepare_trade_calendar(
    frame: pd.DataFrame,
    as_of_date: date,
    downloaded_at: datetime,
) -> pd.DataFrame:
    """Normalize and validate trade-calendar records."""

    prepared = normalize_tushare_date_columns(frame, ["cal_date", "pretrade_date"])
    prepared["as_of_date"] = pd.Timestamp(as_of_date)
    prepared["downloaded_at_utc"] = pd.Timestamp(downloaded_at)
    validate_trade_calendar(prepared)
    return stringify_datetime_columns(
        prepared,
        ["cal_date", "pretrade_date", "as_of_date"],
    )


def download_basic_data(
    source: DataSource,
    output_dir: Path,
    start_date: date,
    end_date: date,
    as_of_date: date,
    exchanges: tuple[str, ...] = ("SSE", "SZSE"),
) -> BasicDataDownloadResult:
    """Download stock basic information and trading calendars, then save Parquet files."""

    if start_date > end_date:
        raise ValueError("start_date must not be after end_date.")
    if as_of_date < end_date:
        raise ValueError("as_of_date must be on or after end_date for this data snapshot.")

    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded_at = datetime.now(UTC)

    stock_basic = prepare_stock_basic(source.fetch_stock_basic(as_of_date), as_of_date, downloaded_at)
    calendars = [
        source.fetch_trade_calendar(start_date=start_date, end_date=end_date, exchange=exchange)
        for exchange in exchanges
    ]
    trade_calendar = prepare_trade_calendar(
        pd.concat(calendars, ignore_index=True),
        as_of_date,
        downloaded_at,
    )

    stock_basic_path = output_path_with_as_of_date(output_dir, "stock_basic", as_of_date, ".parquet")
    trade_calendar_path = output_path_with_as_of_date(
        output_dir,
        "trade_calendar",
        as_of_date,
        ".parquet",
    )
    metadata_path = output_path_with_as_of_date(output_dir, "basic_data_metadata", as_of_date, ".json")

    stock_basic.to_parquet(stock_basic_path, index=False)
    trade_calendar.to_parquet(trade_calendar_path, index=False)
    metadata = {
        "provider": source.provider_name(),
        "downloaded_at_utc": downloaded_at.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "exchanges": list(exchanges),
        "stock_basic_rows": int(len(stock_basic)),
        "trade_calendar_rows": int(len(trade_calendar)),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return BasicDataDownloadResult(
        stock_basic_path=stock_basic_path,
        trade_calendar_path=trade_calendar_path,
        metadata_path=metadata_path,
        stock_basic_rows=len(stock_basic),
        trade_calendar_rows=len(trade_calendar),
    )
