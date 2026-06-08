# Data Dictionary

## Required Date Fields

- `as_of_date`: requested construction date for a run.
- `report_period`: financial statement period.
- `announcement_date`: date when the financial record became public.

Financial records are usable only when `announcement_date <= as_of_date`.

## Security Identity Fields

- `ts_code`: stable security identifier from the data source.
- `name`: security name.
- `exchange`: exchange code.
- `board`: market board.
- `list_date`: listing date.
- `delist_date`: delisting date, if any.
- `list_status`: current or historical listing status.
- `downloaded_at_utc`: UTC time when the data was downloaded.
- `source_code`: original security code from the data source.
- `security_type`: raw security type from the data source when available.

TODO: Extend this dictionary when real data-source schemas are implemented.

## Trade Calendar Fields

- `exchange`: exchange code.
- `cal_date`: calendar date.
- `is_open`: 1 for trading day, 0 for market close.
- `pretrade_date`: previous trading day where provided by the data source.

## Daily Market Fields

- `trade_date`: trading date.
- `close`: closing price.
- `amount`: trading amount.
- `tradestatus`: 1 for normal trading, 0 for suspended or not traded where provided.
- `pctChg`: daily percentage change.
- `peTTM`: trailing PE from the data source.
- `pbMRQ`: PB from the data source.
- `psTTM`: trailing PS from the data source.
- `pcfNcfTTM`: trailing price-to-cash-flow field from the data source.
- `isST`: 1 when the security is marked ST, 0 otherwise.

## Market Feature Fields

- `valid_trading_days_60d`: number of valid trading days in the latest 60 rows.
- `valid_trading_ratio_60d`: valid trading days divided by latest 60 rows.
- `average_amount_60d`: average trading amount over valid trading days in the latest 60 rows.
- `annualized_volatility_60d`: annualized standard deviation of daily returns.
- `max_drawdown_120d`: maximum drawdown over the latest 120 rows.
- `return_6m`: approximate 6-month price return.
- `return_12m_skip_1m`: approximate 12-month return skipping the latest month.
- `has_st_60d`: whether the security had an ST flag in the latest 60 rows.

## Financial Fields

- `announcement_date`: BaoStock `pubDate`; financial records after `as_of_date` are filtered out.
- `report_period`: BaoStock `statDate`.
- `profit_roeAvg`: average ROE from BaoStock profit indicators.
- `profit_npMargin`: net profit margin.
- `profit_gpMargin`: gross profit margin.
- `cashflow_CFOToNP`: operating cash flow to net profit.
- `growth_YOYNI`: net profit year-over-year growth.
- `growth_YOYAsset`: total asset year-over-year growth.
- `balance_liabilityToAsset`: liability-to-asset ratio.
