"""HTML report helpers."""

from html import escape
from pathlib import Path

import pandas as pd


def write_market_proxy_html_report(
    selected: pd.DataFrame,
    excluded: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write a compact HTML report for the market proxy candidate pool."""

    industry_html = selected["industry"].value_counts().head(20).to_frame("count").to_html()
    excluded_html = excluded["exclusion_reason"].value_counts().to_frame("count").to_html()
    top_columns = [
        "ts_code",
        "name",
        "industry",
        "market_proxy_score",
        "average_amount_60d",
        "return_6m",
        "annualized_volatility_60d",
        "max_drawdown_120d",
    ]
    top_html = selected[top_columns].head(50).to_html(index=False)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Core 600 Market Proxy Report</title>
  <style>
    body {{ font-family: Arial, 'Microsoft YaHei', sans-serif; line-height: 1.6; margin: 32px; color: #1f2a30; }}
    h1, h2 {{ line-height: 1.25; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 32px; font-size: 14px; }}
    th, td {{ border: 1px solid #d6dde0; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef4f1; }}
    .note {{ padding: 16px; background: #fff8e5; border-left: 6px solid #b7791f; }}
  </style>
</head>
<body>
  <h1>Core 600 Market Proxy Report</h1>
  <p class="note"><strong>重要限制：</strong>{escape('这是市场数据代理版，不是最终基本面完整版。财报公告日期、审计意见和治理风险仍待接入。')}</p>
  <h2>Summary</h2>
  <ul>
    <li>Selected rows: {len(selected)}</li>
    <li>Excluded rows: {len(excluded)}</li>
    <li>Unique selected securities: {selected['ts_code'].nunique()}</li>
    <li>Max industry count: {selected['industry'].value_counts().max()}</li>
  </ul>
  <h2>Top Industries</h2>
  {industry_html}
  <h2>Exclusion Reasons</h2>
  {excluded_html}
  <h2>Top 50 Selected</h2>
  {top_html}
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")
