"""Market-data proxy selector for a preliminary Core 600 candidate pool."""

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

import pandas as pd

from core600.reporting import output_path_with_as_of_date
from core600.html_report import write_market_proxy_html_report


@dataclass(frozen=True)
class MarketSelectionResult:
    """Paths and row counts from a market-proxy selection run."""

    selected_path: Path
    excluded_path: Path
    report_path: Path
    selected_rows: int
    excluded_rows: int


def percentile_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Calculate 0-100 percentile scores."""

    values = pd.to_numeric(series, errors="coerce")
    ranked = values.rank(pct=True, na_option="keep") * 100
    if not higher_is_better:
        ranked = 100 - ranked
    return ranked


def add_industry_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Add industry-relative market proxy scores."""

    scored = frame.copy()
    group = scored.groupby("industry", dropna=False)
    scored["liquidity_score"] = group["average_amount_60d"].transform(
        lambda item: percentile_score(item, True)
    )
    scored["momentum_score"] = group["return_6m"].transform(lambda item: percentile_score(item, True))
    scored["low_volatility_score"] = group["annualized_volatility_60d"].transform(
        lambda item: percentile_score(item, False)
    )
    scored["drawdown_score"] = group["max_drawdown_120d"].transform(
        lambda item: percentile_score(item, True)
    )
    scored["pb_score"] = group["latest_pb_mrq"].transform(lambda item: percentile_score(item, False))
    scored["ps_score"] = group["latest_ps_ttm"].transform(lambda item: percentile_score(item, False))
    scored["value_score"] = scored[["pb_score", "ps_score"]].mean(axis=1)
    scored["market_proxy_score"] = (
        scored["liquidity_score"] * 0.20
        + scored["momentum_score"] * 0.25
        + scored["low_volatility_score"] * 0.20
        + scored["drawdown_score"] * 0.20
        + scored["value_score"] * 0.15
    )
    return scored


def build_market_proxy_pool(
    stock_basic: pd.DataFrame,
    market_features: pd.DataFrame,
    industry: pd.DataFrame,
    as_of_date: date,
    target_size: int = 600,
    maximum_industry_weight: float = 0.15,
    minimum_valid_trading_days_60d: int = 50,
    minimum_average_amount_60d: float = 20_000_000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a preliminary market-data proxy candidate pool."""

    active = stock_basic.loc[stock_basic["list_status"] == "L"].copy()
    merged = active.merge(market_features, on="ts_code", how="left", suffixes=("", "_feature"))
    industry_columns = industry[["ts_code", "industry", "industry_classification"]].drop_duplicates(
        "ts_code"
    )
    merged = merged.merge(industry_columns, on="ts_code", how="left", suffixes=("", "_industry"))
    if "industry_industry" in merged.columns:
        merged["industry"] = merged["industry_industry"].combine_first(merged.get("industry"))
    merged["industry"] = merged["industry"].fillna("UNKNOWN")
    merged["exclusion_reason"] = ""

    missing_features = merged["average_amount_60d"].isna()
    recent_st = merged["has_st_60d"].fillna(True)
    insufficient_trading = merged["valid_trading_days_60d"].fillna(0) < minimum_valid_trading_days_60d
    insufficient_liquidity = merged["average_amount_60d"].fillna(0) < minimum_average_amount_60d
    negative_or_missing_pb = merged["latest_pb_mrq"].fillna(-1) <= 0

    rules = [
        (missing_features, "missing_market_features"),
        (recent_st, "recent_st"),
        (insufficient_trading, "insufficient_trading_days"),
        (insufficient_liquidity, "insufficient_liquidity"),
        (negative_or_missing_pb, "invalid_pb"),
    ]
    for mask, reason in rules:
        merged.loc[mask & (merged["exclusion_reason"] == ""), "exclusion_reason"] = reason

    excluded = merged.loc[merged["exclusion_reason"] != ""].copy()
    eligible = merged.loc[merged["exclusion_reason"] == ""].copy()
    scored = add_industry_scores(eligible)
    scored = scored.sort_values(
        ["market_proxy_score", "average_amount_60d", "ts_code"],
        ascending=[False, False, True],
    )

    max_per_industry = max(1, int(target_size * maximum_industry_weight))
    selected_parts = []
    industry_counts: dict[str, int] = {}
    for row in scored.itertuples(index=False):
        count = industry_counts.get(row.industry, 0)
        if count >= max_per_industry:
            continue
        selected_parts.append(row)
        industry_counts[row.industry] = count + 1
        if len(selected_parts) >= target_size:
            break
    selected = pd.DataFrame(selected_parts)
    if not selected.empty:
        selected["as_of_date"] = as_of_date.isoformat()
        selected["selection_version"] = "market_proxy_v1"
        selected["selection_note"] = "Market-data proxy only; financial announcement-date factors pending."
    return selected, excluded


def build_fundamental_proxy_pool(
    stock_basic: pd.DataFrame,
    market_features: pd.DataFrame,
    industry: pd.DataFrame,
    financial: pd.DataFrame,
    as_of_date: date,
    target_size: int = 600,
    maximum_industry_weight: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a fundamental-enhanced candidate pool using announcement-filtered data."""

    selected_base, excluded = build_market_proxy_pool(
        stock_basic=stock_basic,
        market_features=market_features,
        industry=industry,
        as_of_date=as_of_date,
        target_size=5000,
        maximum_industry_weight=1.0,
    )
    financial_cols = [
        "ts_code",
        "announcement_date",
        "report_period",
        "profit_roeAvg",
        "profit_npMargin",
        "profit_gpMargin",
        "cashflow_CFOToNP",
        "growth_YOYNI",
        "growth_YOYAsset",
        "balance_liabilityToAsset",
    ]
    available_cols = [column for column in financial_cols if column in financial.columns]
    merged = selected_base.merge(financial[available_cols], on="ts_code", how="left")
    merged["financial_missing"] = merged["announcement_date"].isna()
    merged["financial_missing_fields"] = merged[
        [
            column
            for column in [
                "profit_roeAvg",
                "profit_npMargin",
                "cashflow_CFOToNP",
                "growth_YOYNI",
                "balance_liabilityToAsset",
            ]
            if column in merged.columns
        ]
    ].isna().sum(axis=1)

    eligible = merged.loc[~merged["financial_missing"]].copy()
    group = eligible.groupby("industry", dropna=False)
    eligible["quality_score"] = (
        group["profit_roeAvg"].transform(lambda item: percentile_score(item, True)) * 0.45
        + group["profit_npMargin"].transform(lambda item: percentile_score(item, True)) * 0.25
        + group["cashflow_CFOToNP"].transform(lambda item: percentile_score(item, True)).fillna(50)
        * 0.15
        + group["balance_liabilityToAsset"].transform(lambda item: percentile_score(item, False)) * 0.15
    )
    eligible["growth_score"] = (
        group["growth_YOYNI"].transform(lambda item: percentile_score(item, True)).fillna(50) * 0.70
        + group["growth_YOYAsset"].transform(lambda item: percentile_score(item, True)).fillna(50) * 0.30
    )
    eligible["fundamental_proxy_score"] = (
        eligible["quality_score"] * 0.35
        + eligible["growth_score"] * 0.20
        + eligible["market_proxy_score"] * 0.45
    )
    eligible = eligible.sort_values(
        ["fundamental_proxy_score", "market_proxy_score", "average_amount_60d", "ts_code"],
        ascending=[False, False, False, True],
    )

    max_per_industry = max(1, int(target_size * maximum_industry_weight))
    selected_parts = []
    industry_counts: dict[str, int] = {}
    for row in eligible.itertuples(index=False):
        count = industry_counts.get(row.industry, 0)
        if count >= max_per_industry:
            continue
        selected_parts.append(row)
        industry_counts[row.industry] = count + 1
        if len(selected_parts) >= target_size:
            break
    selected = pd.DataFrame(selected_parts)
    if not selected.empty:
        selected["as_of_date"] = as_of_date.isoformat()
        selected["selection_version"] = "fundamental_proxy_v1"
        selected["selection_note"] = (
            "Fundamental-enhanced proxy using BaoStock pubDate-filtered quarterly indicators; "
            "audit opinion and governance checks pending."
        )

    financial_excluded = merged.loc[merged["financial_missing"]].copy()
    financial_excluded["exclusion_reason"] = "missing_financial_records"
    combined_excluded = pd.concat([excluded, financial_excluded], ignore_index=True, sort=False)
    return selected, combined_excluded


def save_fundamental_proxy_pool(
    stock_basic_path: Path,
    market_features_path: Path,
    industry_path: Path,
    financial_path: Path,
    output_dir: Path,
    as_of_date: date,
) -> MarketSelectionResult:
    """Build and save the fundamental-enhanced candidate pool."""

    output_dir.mkdir(parents=True, exist_ok=True)
    stock_basic = pd.read_parquet(stock_basic_path)
    market_features = pd.read_parquet(market_features_path)
    industry = pd.read_parquet(industry_path)
    financial = pd.read_parquet(financial_path)
    selected, excluded = build_fundamental_proxy_pool(
        stock_basic,
        market_features,
        industry,
        financial,
        as_of_date,
    )

    selected_path = output_path_with_as_of_date(output_dir, "core600_fundamental_proxy", as_of_date, ".csv")
    excluded_path = output_path_with_as_of_date(
        output_dir,
        "excluded_fundamental_proxy",
        as_of_date,
        ".csv",
    )
    report_path = output_path_with_as_of_date(
        output_dir,
        "core600_fundamental_proxy_report",
        as_of_date,
        ".json",
    )
    html_report_path = output_path_with_as_of_date(
        output_dir,
        "core600_fundamental_proxy_report",
        as_of_date,
        ".html",
    )
    selected.to_csv(selected_path, index=False, encoding="utf-8-sig")
    excluded.to_csv(excluded_path, index=False, encoding="utf-8-sig")
    report = {
        "as_of_date": as_of_date.isoformat(),
        "selection_version": "fundamental_proxy_v1",
        "selected_rows": int(len(selected)),
        "excluded_rows": int(len(excluded)),
        "industry_distribution": selected["industry"].value_counts().to_dict()
        if "industry" in selected
        else {},
        "max_announcement_date": str(financial["announcement_date"].max())
        if "announcement_date" in financial
        else None,
        "limitations": [
            "Audit opinion and governance risk checks are pending.",
            "BaoStock free financial indicators may have coverage and field limitations.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_market_proxy_html_report(selected, excluded, html_report_path)
    return MarketSelectionResult(selected_path, excluded_path, report_path, len(selected), len(excluded))


def save_market_proxy_pool(
    stock_basic_path: Path,
    market_features_path: Path,
    industry_path: Path,
    output_dir: Path,
    as_of_date: date,
) -> MarketSelectionResult:
    """Build and save the market-proxy candidate pool."""

    output_dir.mkdir(parents=True, exist_ok=True)
    stock_basic = pd.read_parquet(stock_basic_path)
    market_features = pd.read_parquet(market_features_path)
    industry = pd.read_parquet(industry_path)
    selected, excluded = build_market_proxy_pool(stock_basic, market_features, industry, as_of_date)

    selected_path = output_path_with_as_of_date(output_dir, "core600_market_proxy", as_of_date, ".csv")
    excluded_path = output_path_with_as_of_date(output_dir, "excluded_market_proxy", as_of_date, ".csv")
    report_path = output_path_with_as_of_date(output_dir, "core600_market_proxy_report", as_of_date, ".json")
    html_report_path = output_path_with_as_of_date(
        output_dir,
        "core600_market_proxy_report",
        as_of_date,
        ".html",
    )
    selected.to_csv(selected_path, index=False, encoding="utf-8-sig")
    excluded.to_csv(excluded_path, index=False, encoding="utf-8-sig")
    report = {
        "as_of_date": as_of_date.isoformat(),
        "selection_version": "market_proxy_v1",
        "selected_rows": int(len(selected)),
        "excluded_rows": int(len(excluded)),
        "industry_distribution": selected["industry"].value_counts().to_dict()
        if "industry" in selected
        else {},
        "limitations": [
            "This is not the final fundamental Core 600.",
            "Financial statement announcement dates are not yet included.",
            "Audit opinion and governance risk checks are pending.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_market_proxy_html_report(selected, excluded, html_report_path)
    return MarketSelectionResult(selected_path, excluded_path, report_path, len(selected), len(excluded))
