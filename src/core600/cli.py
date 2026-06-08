"""Command-line interface for Core 600 research workflows."""

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from core600.basic_data import download_basic_data
from core600.data_sources.baostock_source import BaoStockDataSource
from core600.data_sources.base import DataSource
from core600.data_sources.tushare_source import TushareDataSource
from core600.market_features import save_market_features
from core600.industry_data import download_industry_data
from core600.financial_data import download_financial_data
from core600.market_data import download_market_data
from core600.market_selector import save_fundamental_proxy_pool, save_market_proxy_pool


def parse_date(value: str) -> date:
    """Parse an ISO date from the CLI."""

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected date format YYYY-MM-DD.") from error


def create_data_source(source_name: str) -> DataSource:
    """Create a configured data source from a CLI source name."""

    if source_name == "baostock":
        return BaoStockDataSource()
    if source_name == "tushare":
        return TushareDataSource()
    raise ValueError(f"Unsupported data source: {source_name}")


def read_skip_source_codes(path: Path | None) -> set[str]:
    """Read source codes to skip from a plain text file."""

    if path is None:
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(prog="core600")
    subparsers = parser.add_subparsers(dest="command")
    download_parser = subparsers.add_parser(
        "download-basic-data",
        help="Download stock basic information and trade calendars.",
    )
    download_parser.add_argument("--output-dir", default="data/raw", type=Path)
    download_parser.add_argument(
        "--source",
        choices=["baostock", "tushare"],
        default="baostock",
        help="Data source to use. BaoStock is free and does not require a token.",
    )
    download_parser.add_argument("--start-date", required=True, type=parse_date)
    download_parser.add_argument("--end-date", required=True, type=parse_date)
    download_parser.add_argument("--as-of-date", required=True, type=parse_date)

    market_parser = subparsers.add_parser(
        "download-market-data",
        help="Download daily market data, valuation fields, trading status, and ST flags.",
    )
    market_parser.add_argument(
        "--stock-basic-path",
        default=Path("data/raw/stock_basic_2026-06-06.parquet"),
        type=Path,
    )
    market_parser.add_argument("--output-dir", default="data/raw", type=Path)
    market_parser.add_argument("--start-date", required=True, type=parse_date)
    market_parser.add_argument("--end-date", required=True, type=parse_date)
    market_parser.add_argument("--as-of-date", required=True, type=parse_date)
    market_parser.add_argument("--max-securities", type=int, default=None)
    market_parser.add_argument("--batch-size", type=int, default=200)
    market_parser.add_argument("--no-resume", action="store_true")
    market_parser.add_argument("--skip-source-codes-file", type=Path, default=None)

    feature_parser = subparsers.add_parser(
        "calculate-market-features",
        help="Calculate market-derived features from downloaded daily market data.",
    )
    feature_parser.add_argument(
        "--market-data-path",
        default=Path("data/raw/market_daily_2026-06-06.parquet"),
        type=Path,
    )
    feature_parser.add_argument("--output-dir", default="data/processed", type=Path)
    feature_parser.add_argument("--as-of-date", required=True, type=parse_date)

    industry_parser = subparsers.add_parser(
        "download-industry-data",
        help="Download stock industry classifications.",
    )
    industry_parser.add_argument("--output-dir", default="data/raw", type=Path)
    industry_parser.add_argument("--as-of-date", required=True, type=parse_date)

    select_parser = subparsers.add_parser(
        "select-market-proxy",
        help="Build a preliminary market-data proxy Core 600 candidate pool.",
    )
    select_parser.add_argument("--stock-basic-path", type=Path, required=True)
    select_parser.add_argument("--market-features-path", type=Path, required=True)
    select_parser.add_argument("--industry-path", type=Path, required=True)
    select_parser.add_argument("--output-dir", default="outputs", type=Path)
    select_parser.add_argument("--as-of-date", required=True, type=parse_date)

    financial_parser = subparsers.add_parser(
        "download-financial-data",
        help="Download latest available quarterly financial indicators.",
    )
    financial_parser.add_argument("--stock-basic-path", type=Path, required=True)
    financial_parser.add_argument("--output-dir", default="data/raw", type=Path)
    financial_parser.add_argument("--as-of-date", required=True, type=parse_date)
    financial_parser.add_argument("--max-securities", type=int, default=None)
    financial_parser.add_argument("--batch-size", type=int, default=100)
    financial_parser.add_argument("--lookback-quarters", type=int, default=6)
    financial_parser.add_argument("--no-resume", action="store_true")

    fundamental_select_parser = subparsers.add_parser(
        "select-fundamental-proxy",
        help="Build a fundamental-enhanced Core 600 candidate pool.",
    )
    fundamental_select_parser.add_argument("--stock-basic-path", type=Path, required=True)
    fundamental_select_parser.add_argument("--market-features-path", type=Path, required=True)
    fundamental_select_parser.add_argument("--industry-path", type=Path, required=True)
    fundamental_select_parser.add_argument("--financial-path", type=Path, required=True)
    fundamental_select_parser.add_argument("--output-dir", default="outputs", type=Path)
    fundamental_select_parser.add_argument("--as-of-date", required=True, type=parse_date)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "download-basic-data":
        try:
            result = download_basic_data(
                source=create_data_source(args.source),
                output_dir=args.output_dir,
                start_date=args.start_date,
                end_date=args.end_date,
                as_of_date=args.as_of_date,
            )
        except RuntimeError as error:
            parser.exit(2, f"error: {error}\n")
        print(f"stock_basic_rows={result.stock_basic_rows}")
        print(f"trade_calendar_rows={result.trade_calendar_rows}")
        print(f"stock_basic_path={result.stock_basic_path}")
        print(f"trade_calendar_path={result.trade_calendar_path}")
        print(f"metadata_path={result.metadata_path}")
        return 0
    if args.command == "select-fundamental-proxy":
        result = save_fundamental_proxy_pool(
            stock_basic_path=args.stock_basic_path,
            market_features_path=args.market_features_path,
            industry_path=args.industry_path,
            financial_path=args.financial_path,
            output_dir=args.output_dir,
            as_of_date=args.as_of_date,
        )
        print(f"selected_rows={result.selected_rows}")
        print(f"excluded_rows={result.excluded_rows}")
        print(f"selected_path={result.selected_path}")
        print(f"excluded_path={result.excluded_path}")
        print(f"report_path={result.report_path}")
        return 0
    if args.command == "select-market-proxy":
        result = save_market_proxy_pool(
            stock_basic_path=args.stock_basic_path,
            market_features_path=args.market_features_path,
            industry_path=args.industry_path,
            output_dir=args.output_dir,
            as_of_date=args.as_of_date,
        )
        print(f"selected_rows={result.selected_rows}")
        print(f"excluded_rows={result.excluded_rows}")
        print(f"selected_path={result.selected_path}")
        print(f"excluded_path={result.excluded_path}")
        print(f"report_path={result.report_path}")
        return 0
    if args.command == "download-financial-data":
        try:
            result = download_financial_data(
                source=BaoStockDataSource(),
                stock_basic_path=args.stock_basic_path,
                output_dir=args.output_dir,
                as_of_date=args.as_of_date,
                max_securities=args.max_securities,
                batch_size=args.batch_size,
                lookback_quarters=args.lookback_quarters,
                resume=not args.no_resume,
            )
        except RuntimeError as error:
            parser.exit(2, f"error: {error}\n")
        print(f"securities_requested={result.securities_requested}")
        print(f"securities_with_rows={result.securities_with_rows}")
        print(f"financial_rows={result.financial_rows}")
        print(f"financial_path={result.financial_path}")
        print(f"metadata_path={result.metadata_path}")
        return 0
    if args.command == "download-industry-data":
        try:
            result = download_industry_data(
                source=BaoStockDataSource(),
                output_dir=args.output_dir,
                as_of_date=args.as_of_date,
            )
        except RuntimeError as error:
            parser.exit(2, f"error: {error}\n")
        print(f"industry_rows={result.industry_rows}")
        print(f"industry_path={result.industry_path}")
        print(f"metadata_path={result.metadata_path}")
        return 0
    if args.command == "calculate-market-features":
        result = save_market_features(
            market_data_path=args.market_data_path,
            output_dir=args.output_dir,
            as_of_date=args.as_of_date,
        )
        print(f"feature_rows={result.feature_rows}")
        print(f"feature_path={result.feature_path}")
        print(f"metadata_path={result.metadata_path}")
        return 0
    if args.command == "download-market-data":
        try:
            result = download_market_data(
                source=BaoStockDataSource(),
                stock_basic_path=args.stock_basic_path,
                output_dir=args.output_dir,
                start_date=args.start_date,
                end_date=args.end_date,
                as_of_date=args.as_of_date,
                max_securities=args.max_securities,
                batch_size=args.batch_size,
                resume=not args.no_resume,
                skip_source_codes=read_skip_source_codes(args.skip_source_codes_file),
            )
        except RuntimeError as error:
            parser.exit(2, f"error: {error}\n")
        print(f"securities_requested={result.securities_requested}")
        print(f"securities_with_rows={result.securities_with_rows}")
        print(f"market_data_rows={result.market_data_rows}")
        print(f"market_data_path={result.market_data_path}")
        print(f"metadata_path={result.metadata_path}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
