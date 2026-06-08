"""Download and persist daily market data from public sources."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
from pathlib import Path

import pandas as pd

from core600.basic_data import stringify_datetime_columns
from core600.data_quality import require_columns
from core600.data_sources.baostock_source import BaoStockDataSource, baostock_code_to_ts_code
from core600.reporting import output_path_with_as_of_date
from core600.universe import build_universe_as_of


MARKET_DATA_COLUMNS = {
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
}


@dataclass(frozen=True)
class MarketDataDownloadResult:
    """Paths and row counts from a market-data download run."""

    market_data_path: Path
    metadata_path: Path
    securities_requested: int
    securities_with_rows: int
    market_data_rows: int


def select_market_data_securities(
    stock_basic: pd.DataFrame,
    as_of_date: date,
    max_securities: int | None = None,
) -> pd.DataFrame:
    """Select securities that are listed as of the requested date."""

    universe = build_universe_as_of(stock_basic, as_of_date)
    if "source_code" not in universe.columns:
        raise ValueError("Missing required column: source_code")
    selected = universe.sort_values("ts_code").reset_index(drop=True)
    if max_securities is not None:
        if max_securities <= 0:
            raise ValueError("max_securities must be positive.")
        selected = selected.head(max_securities)
    return selected


def prepare_daily_history(
    frame: pd.DataFrame,
    ts_code: str,
    source_code: str,
    as_of_date: date,
    downloaded_at: datetime,
) -> pd.DataFrame:
    """Normalize and validate daily history records."""

    if frame.empty:
        return pd.DataFrame()
    require_columns(frame, MARKET_DATA_COLUMNS)
    prepared = frame.copy()
    prepared["ts_code"] = ts_code
    prepared["source_code"] = source_code
    prepared["trade_date"] = pd.to_datetime(prepared["date"], errors="coerce")
    if prepared["trade_date"].isna().any():
        raise ValueError(f"Market data contains invalid trade dates for {source_code}.")
    prepared["as_of_date"] = pd.Timestamp(as_of_date)
    prepared["downloaded_at_utc"] = pd.Timestamp(downloaded_at)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "preclose",
        "volume",
        "amount",
        "pctChg",
        "peTTM",
        "pbMRQ",
        "psTTM",
        "pcfNcfTTM",
    ]
    for column in numeric_columns:
        prepared[column] = pd.to_numeric(prepared[column].replace("", pd.NA), errors="coerce")

    prepared["isST"] = pd.to_numeric(prepared["isST"].replace("", pd.NA), errors="coerce")
    prepared["tradestatus"] = pd.to_numeric(
        prepared["tradestatus"].replace("", pd.NA),
        errors="coerce",
    )
    prepared["provider_ts_code"] = prepared["code"].map(baostock_code_to_ts_code)
    if not (prepared["provider_ts_code"] == ts_code).all():
        raise ValueError(f"BaoStock code conversion mismatch for {source_code}.")

    prepared = stringify_datetime_columns(
        prepared,
        ["trade_date", "as_of_date"],
    )
    return prepared.drop(columns=["date", "provider_ts_code"])


def download_market_data(
    source: BaoStockDataSource,
    stock_basic_path: Path,
    output_dir: Path,
    start_date: date,
    end_date: date,
    as_of_date: date,
    max_securities: int | None = None,
    batch_size: int = 200,
    resume: bool = True,
    skip_source_codes: set[str] | None = None,
) -> MarketDataDownloadResult:
    """Download daily market data for listed securities and save a Parquet file."""

    if start_date > end_date:
        raise ValueError("start_date must not be after end_date.")
    if as_of_date < end_date:
        raise ValueError("as_of_date must be on or after end_date for this data snapshot.")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    stock_basic = pd.read_parquet(stock_basic_path)
    securities = select_market_data_securities(stock_basic, as_of_date, max_securities)
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded_at = datetime.now(UTC)

    batch_dir = output_dir / f"market_daily_{as_of_date.isoformat()}_batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_paths: list[Path] = []
    source.login()
    try:
        for batch_start in range(0, len(securities), batch_size):
            batch = securities.iloc[batch_start : batch_start + batch_size]
            batch_number = batch_start // batch_size + 1
            batch_path = batch_dir / f"batch_{batch_number:05d}.parquet"
            batch_paths.append(batch_path)
            if resume and batch_path.exists():
                continue

            frames: list[pd.DataFrame] = []
            for row in batch.itertuples(index=False):
                if skip_source_codes and row.source_code in skip_source_codes:
                    continue
                raw = source.fetch_daily_history(
                    source_code=row.source_code,
                    start_date=start_date,
                    end_date=end_date,
                )
                prepared = prepare_daily_history(
                    raw,
                    ts_code=row.ts_code,
                    source_code=row.source_code,
                    as_of_date=as_of_date,
                    downloaded_at=downloaded_at,
                )
                if not prepared.empty:
                    frames.append(prepared)

            batch_data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            batch_data.to_parquet(batch_path, index=False)
            print(
                f"batch={batch_number} securities={len(batch)} rows={len(batch_data)} path={batch_path}",
                flush=True,
            )
    finally:
        source.logout()

    completed_batch_paths = [path for path in batch_paths if path.exists()]
    batch_frames = [pd.read_parquet(path) for path in completed_batch_paths]
    market_data = pd.concat(batch_frames, ignore_index=True) if batch_frames else pd.DataFrame()
    market_data_path = output_path_with_as_of_date(output_dir, "market_daily", as_of_date, ".parquet")
    metadata_path = output_path_with_as_of_date(output_dir, "market_daily_metadata", as_of_date, ".json")
    market_data.to_parquet(market_data_path, index=False)
    metadata = {
        "provider": source.provider_name(),
        "downloaded_at_utc": downloaded_at.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "stock_basic_path": str(stock_basic_path),
        "securities_requested": int(len(securities)),
        "securities_with_rows": int(market_data["ts_code"].nunique()) if "ts_code" in market_data else 0,
        "market_data_rows": int(len(market_data)),
        "max_securities": max_securities,
        "skipped_source_codes": sorted(skip_source_codes or []),
        "batch_size": batch_size,
        "batch_dir": str(batch_dir),
        "completed_batches": len(completed_batch_paths),
        "expected_batches": len(batch_paths),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return MarketDataDownloadResult(
        market_data_path=market_data_path,
        metadata_path=metadata_path,
        securities_requested=len(securities),
        securities_with_rows=int(market_data["ts_code"].nunique()) if "ts_code" in market_data else 0,
        market_data_rows=len(market_data),
    )
