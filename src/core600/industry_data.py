"""Download and persist industry classifications."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
from pathlib import Path

import pandas as pd

from core600.data_sources.baostock_source import BaoStockDataSource
from core600.reporting import output_path_with_as_of_date


@dataclass(frozen=True)
class IndustryDownloadResult:
    """Paths and row counts from an industry download run."""

    industry_path: Path
    metadata_path: Path
    industry_rows: int


def download_industry_data(
    source: BaoStockDataSource,
    output_dir: Path,
    as_of_date: date,
) -> IndustryDownloadResult:
    """Download industry classification data and save it."""

    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded_at = datetime.now(UTC)
    industry = source.fetch_stock_industry()
    industry["as_of_date"] = as_of_date.isoformat()
    industry["downloaded_at_utc"] = downloaded_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    industry_path = output_path_with_as_of_date(output_dir, "stock_industry", as_of_date, ".parquet")
    metadata_path = output_path_with_as_of_date(
        output_dir,
        "stock_industry_metadata",
        as_of_date,
        ".json",
    )
    industry.to_parquet(industry_path, index=False)
    metadata = {
        "provider": source.provider_name(),
        "downloaded_at_utc": downloaded_at.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "industry_rows": int(len(industry)),
        "missing_industry_rows": int(industry["industry"].isna().sum()) if "industry" in industry else 0,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return IndustryDownloadResult(industry_path, metadata_path, len(industry))
