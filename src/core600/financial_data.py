"""Download and prepare quarterly financial indicators."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
from pathlib import Path

import pandas as pd

from core600.data_sources.baostock_source import BaoStockDataSource, baostock_code_to_ts_code
from core600.market_data import select_market_data_securities
from core600.reporting import output_path_with_as_of_date


FINANCIAL_GROUPS = ("profit", "growth", "balance", "cashflow", "operation")


@dataclass(frozen=True)
class FinancialDownloadResult:
    """Paths and row counts from a financial-data download run."""

    financial_path: Path
    metadata_path: Path
    securities_requested: int
    securities_with_rows: int
    financial_rows: int


def recent_quarters(as_of_date: date, lookback_quarters: int = 6) -> list[tuple[int, int]]:
    """Return recent year/quarter pairs, newest first."""

    current_quarter = (as_of_date.month - 1) // 3 + 1
    year = as_of_date.year
    quarter = current_quarter
    pairs: list[tuple[int, int]] = []
    for _ in range(lookback_quarters):
        pairs.append((year, quarter))
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    return pairs


def prefix_financial_columns(frame: pd.DataFrame, group: str) -> pd.DataFrame:
    """Prefix non-key financial columns with their statement group."""

    if frame.empty:
        return frame
    renamed = {}
    for column in frame.columns:
        if column not in {"code", "pubDate", "statDate"}:
            renamed[column] = f"{group}_{column}"
    return frame.rename(columns=renamed)


def merge_financial_groups(group_frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge statement-group frames on code/pubDate/statDate."""

    non_empty = [frame for frame in group_frames if not frame.empty]
    if not non_empty:
        return pd.DataFrame()
    merged = non_empty[0]
    for frame in non_empty[1:]:
        merged = merged.merge(frame, on=["code", "pubDate", "statDate"], how="outer")
    return merged


def prepare_financial_records(
    frame: pd.DataFrame,
    ts_code: str,
    source_code: str,
    as_of_date: date,
    downloaded_at: datetime,
) -> pd.DataFrame:
    """Normalize and validate financial records for one security."""

    if frame.empty:
        return pd.DataFrame()
    prepared = frame.copy()
    prepared["ts_code"] = ts_code
    prepared["source_code"] = source_code
    prepared["provider_ts_code"] = prepared["code"].map(baostock_code_to_ts_code)
    if not (prepared["provider_ts_code"] == ts_code).all():
        raise ValueError(f"BaoStock code conversion mismatch for {source_code}.")

    prepared["announcement_date"] = pd.to_datetime(prepared["pubDate"], errors="coerce")
    prepared["report_period"] = pd.to_datetime(prepared["statDate"], errors="coerce")
    as_of_timestamp = pd.Timestamp(as_of_date)
    prepared = prepared.loc[
        prepared["announcement_date"].notna()
        & prepared["report_period"].notna()
        & (prepared["announcement_date"] <= as_of_timestamp)
    ].copy()
    if prepared.empty:
        return pd.DataFrame()
    prepared["as_of_date"] = as_of_date.isoformat()
    prepared["downloaded_at_utc"] = downloaded_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    prepared["announcement_date"] = prepared["announcement_date"].dt.strftime("%Y-%m-%d")
    prepared["report_period"] = prepared["report_period"].dt.strftime("%Y-%m-%d")

    numeric_columns = [
        column
        for column in prepared.columns
        if column
        not in {
            "code",
            "pubDate",
            "statDate",
            "ts_code",
            "source_code",
            "provider_ts_code",
            "announcement_date",
            "report_period",
            "as_of_date",
            "downloaded_at_utc",
        }
    ]
    for column in numeric_columns:
        prepared[column] = pd.to_numeric(prepared[column].replace("", pd.NA), errors="coerce")
    return prepared.drop(columns=["provider_ts_code"])


def fetch_latest_financial_for_security(
    source: BaoStockDataSource,
    ts_code: str,
    source_code: str,
    as_of_date: date,
    quarters: list[tuple[int, int]],
    downloaded_at: datetime,
) -> pd.DataFrame:
    """Fetch the latest available financial records for one security."""

    for year, quarter in quarters:
        frames = [
            prefix_financial_columns(
                source.fetch_financial_statement(source_code, year, quarter, group),
                group,
            )
            for group in FINANCIAL_GROUPS
        ]
        merged = merge_financial_groups(frames)
        prepared = prepare_financial_records(merged, ts_code, source_code, as_of_date, downloaded_at)
        if not prepared.empty:
            prepared["fiscal_year"] = year
            prepared["fiscal_quarter"] = quarter
            return prepared
    return pd.DataFrame()


def download_financial_data(
    source: BaoStockDataSource,
    stock_basic_path: Path,
    output_dir: Path,
    as_of_date: date,
    max_securities: int | None = None,
    batch_size: int = 100,
    lookback_quarters: int = 6,
    resume: bool = True,
) -> FinancialDownloadResult:
    """Download latest available quarterly financial indicators."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")
    output_dir.mkdir(parents=True, exist_ok=True)
    stock_basic = pd.read_parquet(stock_basic_path)
    securities = select_market_data_securities(stock_basic, as_of_date, max_securities)
    downloaded_at = datetime.now(UTC)
    quarters = recent_quarters(as_of_date, lookback_quarters)

    batch_dir = output_dir / f"financial_latest_{as_of_date.isoformat()}_batches"
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
                prepared = fetch_latest_financial_for_security(
                    source,
                    row.ts_code,
                    row.source_code,
                    as_of_date,
                    quarters,
                    downloaded_at,
                )
                if not prepared.empty:
                    frames.append(prepared)
            batch_data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            batch_data.to_parquet(batch_path, index=False)
            print(
                f"financial_batch={batch_number} securities={len(batch)} rows={len(batch_data)}",
                flush=True,
            )
    finally:
        source.logout()

    completed_batch_paths = [path for path in batch_paths if path.exists()]
    batch_frames = [pd.read_parquet(path) for path in completed_batch_paths]
    financial = pd.concat(batch_frames, ignore_index=True) if batch_frames else pd.DataFrame()
    financial_path = output_path_with_as_of_date(output_dir, "financial_latest", as_of_date, ".parquet")
    metadata_path = output_path_with_as_of_date(
        output_dir,
        "financial_latest_metadata",
        as_of_date,
        ".json",
    )
    financial.to_parquet(financial_path, index=False)
    metadata = {
        "provider": source.provider_name(),
        "downloaded_at_utc": downloaded_at.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "stock_basic_path": str(stock_basic_path),
        "securities_requested": int(len(securities)),
        "securities_with_rows": int(financial["ts_code"].nunique()) if "ts_code" in financial else 0,
        "financial_rows": int(len(financial)),
        "recent_quarters": [{"year": year, "quarter": quarter} for year, quarter in quarters],
        "completed_batches": len(completed_batch_paths),
        "expected_batches": len(batch_paths),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return FinancialDownloadResult(
        financial_path=financial_path,
        metadata_path=metadata_path,
        securities_requested=len(securities),
        securities_with_rows=int(financial["ts_code"].nunique()) if "ts_code" in financial else 0,
        financial_rows=len(financial),
    )
