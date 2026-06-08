# A-share Core 600 Research Project

This repository builds the engineering foundation for a reproducible and auditable A-share Core 600 candidate universe.

The first stage only creates the project skeleton. It does not download market data, does not generate stock lists, does not implement full factor scoring, and does not claim any backtest result.

## Goals

- Build a replaceable data-source layer for free public data and optional paid data.
- Keep thresholds and factor weights in YAML configuration.
- Preserve `as_of_date` for every generated output.
- Prevent look-ahead bias by requiring financial records to preserve both `report_period` and `announcement_date`.
- Support historical universe construction that can include delisted securities when data exists.

## Current Stage

Stage 1: engineering scaffold.

Implemented:

- Python `src` layout.
- Configuration files under `config/`.
- Replaceable data-source interface.
- Free BaoStock basic-data source.
- Optional Tushare source.
- Module and test skeletons.

Not implemented yet:

- Market, financial, industry, audit, and risk data download.
- Stock selection.
- Full factor calculations.
- Backtesting.

## Test

```powershell
python -m pytest
```

## Basic Data Download

The first data step downloads only stock basic information and trade calendars.
It does not download prices, financial statements, industry classifications, or generate a stock list.

Default free source:

```powershell
$env:PYTHONPATH="src"
python -m core600.cli download-basic-data --start-date 1990-01-01 --end-date 2026-06-06 --as-of-date 2026-06-06
```

Optional Tushare source:

```powershell
$env:TUSHARE_TOKEN="your-token"
$env:PYTHONPATH="src"
python -m core600.cli download-basic-data --source tushare --start-date 1990-01-01 --end-date 2026-06-06 --as-of-date 2026-06-06
```

Outputs are written to `data/raw/` as Parquet files plus JSON metadata.

Free public data is suitable for a learning and research version. Paid or commercial data can be added later for stronger coverage of announcements, audit opinions, historical delisting details, and industry classifications.

## Market Data Download

Download daily market data, valuation fields, trading status, and ST flags:

```powershell
$env:PYTHONPATH="src"
python -m core600.cli download-market-data --stock-basic-path data/raw/stock_basic_2026-06-06.parquet --start-date 2025-06-06 --end-date 2026-06-06 --as-of-date 2026-06-06 --max-securities 200
```

Remove `--max-securities` only when you are ready for a longer full-universe run.

Calculate market-derived features:

```powershell
$env:PYTHONPATH="src"
python -m core600.cli calculate-market-features --market-data-path data/raw/market_daily_2026-06-06.parquet --output-dir data/processed --as-of-date 2026-06-06
```

## Market Proxy Candidate Pool

Build a preliminary market-data proxy candidate pool:

```powershell
$env:PYTHONPATH="src"
python -m core600.cli select-market-proxy --stock-basic-path data/raw/stock_basic_2026-06-06.parquet --market-features-path data/processed/market_features_2026-06-06.parquet --industry-path data/raw/stock_industry_2026-06-06.parquet --output-dir outputs --as-of-date 2026-06-06
```

This produces a 600-stock candidate pool based on market data, valuation proxies, ST flags, trading status, liquidity, volatility, drawdown, and industry caps. It is explicitly not the final fundamental Core 600 until financial statement announcement dates, audit opinions, and governance checks are added.

## Fundamental Proxy Candidate Pool

Download latest available quarterly financial indicators. BaoStock provides `pubDate`, which is preserved as `announcement_date` and filtered by `as_of_date`.

```powershell
$env:PYTHONPATH="src"
python -m core600.cli download-financial-data --stock-basic-path data/raw/stock_basic_2026-06-06.parquet --output-dir data/raw --as-of-date 2026-06-06 --batch-size 100 --lookback-quarters 6
```

Build the fundamental-enhanced proxy pool:

```powershell
$env:PYTHONPATH="src"
python -m core600.cli select-fundamental-proxy --stock-basic-path data/raw/stock_basic_2026-06-06.parquet --market-features-path data/processed/market_features_2026-06-06.parquet --industry-path data/raw/stock_industry_2026-06-06.parquet --financial-path data/raw/financial_latest_2026-06-06.parquet --output-dir outputs --as-of-date 2026-06-06
```

This version uses announcement-date-filtered financial indicators plus market data. Audit opinion and governance risk checks remain pending.

## Web Learning Site

A static learning site for ordinary investment learners is available at:

```text
web/index.html
```

Open it directly in a browser. No development server is required.

The visualization dashboard is available at:

```text
web/dashboard.html
```

For Vercel deployment:

```powershell
npm run build
```

Vercel uses `vercel.json` to build the static site into `dist/`.

Recommended GitHub + Vercel flow:

1. Push this repository to GitHub.
2. In Vercel, import the GitHub repository.
3. Keep the project root as the repository root.
4. Vercel will read `vercel.json`, run `npm run build`, and serve `dist/`.

## Important Boundary

This project is for quantitative research engineering only. It does not provide investment advice and must not fabricate financial data.
