"""Calculate market-derived features for preliminary filtering and scoring."""

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

import numpy as np
import pandas as pd

from core600.data_quality import require_columns
from core600.reporting import output_path_with_as_of_date


REQUIRED_MARKET_FEATURE_COLUMNS = {
    "ts_code",
    "trade_date",
    "close",
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
class MarketFeatureResult:
    """Paths and row counts from a market-feature calculation run."""

    feature_path: Path
    metadata_path: Path
    feature_rows: int


def max_drawdown(close: pd.Series) -> float:
    """Calculate maximum drawdown from a close-price series."""

    values = close.dropna().astype(float)
    if values.empty:
        return float("nan")
    running_max = values.cummax()
    drawdowns = values / running_max - 1.0
    return float(drawdowns.min())


def return_between_positions(close: pd.Series, start_offset: int, end_offset: int) -> float:
    """Calculate return between two negative index offsets from the end."""

    values = close.dropna().astype(float)
    if len(values) < max(abs(start_offset), abs(end_offset)):
        return float("nan")
    start_value = values.iloc[start_offset]
    end_value = values.iloc[end_offset]
    if start_value <= 0:
        return float("nan")
    return float(end_value / start_value - 1.0)


def calculate_features_for_security(frame: pd.DataFrame, as_of_date: date) -> dict[str, object]:
    """Calculate market-derived features for one security."""

    sorted_frame = frame.sort_values("trade_date").reset_index(drop=True)
    latest = sorted_frame.iloc[-1]
    tail_60 = sorted_frame.tail(60)
    tail_120 = sorted_frame.tail(120)

    trading_60 = tail_60.loc[tail_60["tradestatus"] == 1]
    pct_change_60 = trading_60["pctChg"].dropna().astype(float) / 100.0
    annualized_volatility_60d = (
        float(pct_change_60.std(ddof=1) * np.sqrt(242)) if len(pct_change_60) >= 2 else float("nan")
    )

    return {
        "ts_code": latest["ts_code"],
        "as_of_date": as_of_date.isoformat(),
        "latest_trade_date": latest["trade_date"],
        "valid_trading_days_60d": int((tail_60["tradestatus"] == 1).sum()),
        "valid_trading_ratio_60d": float((tail_60["tradestatus"] == 1).mean()),
        "average_amount_60d": float(trading_60["amount"].dropna().mean())
        if not trading_60["amount"].dropna().empty
        else float("nan"),
        "annualized_volatility_60d": annualized_volatility_60d,
        "max_drawdown_120d": max_drawdown(tail_120["close"]),
        "return_6m": return_between_positions(sorted_frame["close"], -120, -1),
        "return_12m_skip_1m": return_between_positions(sorted_frame["close"], -242, -21),
        "latest_pe_ttm": latest["peTTM"],
        "latest_pb_mrq": latest["pbMRQ"],
        "latest_ps_ttm": latest["psTTM"],
        "latest_pcf_ncf_ttm": latest["pcfNcfTTM"],
        "has_st_60d": bool((tail_60["isST"] == 1).any()),
    }


def calculate_market_features(frame: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    """Calculate market-derived features for all securities in a market data table."""

    require_columns(frame, REQUIRED_MARKET_FEATURE_COLUMNS)
    prepared = frame.copy()
    prepared["trade_date"] = pd.to_datetime(prepared["trade_date"], errors="coerce")
    if prepared["trade_date"].isna().any():
        raise ValueError("Market data contains invalid trade_date values.")

    rows = [
        calculate_features_for_security(group, as_of_date)
        for _, group in prepared.groupby("ts_code", sort=True)
        if not group.empty
    ]
    return pd.DataFrame(rows)


def save_market_features(
    market_data_path: Path,
    output_dir: Path,
    as_of_date: date,
) -> MarketFeatureResult:
    """Read market data, calculate features, and save outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    market_data = pd.read_parquet(market_data_path)
    features = calculate_market_features(market_data, as_of_date)

    feature_path = output_path_with_as_of_date(output_dir, "market_features", as_of_date, ".parquet")
    metadata_path = output_path_with_as_of_date(
        output_dir,
        "market_features_metadata",
        as_of_date,
        ".json",
    )
    features.to_parquet(feature_path, index=False)
    metadata = {
        "as_of_date": as_of_date.isoformat(),
        "market_data_path": str(market_data_path),
        "feature_rows": int(len(features)),
        "feature_columns": list(features.columns),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return MarketFeatureResult(
        feature_path=feature_path,
        metadata_path=metadata_path,
        feature_rows=len(features),
    )
