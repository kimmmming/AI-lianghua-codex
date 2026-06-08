"""Tests for factor placeholders."""

import pandas as pd

from core600.factors.quality import calculate_quality_factors


def test_factor_placeholder_does_not_mutate_input() -> None:
    """Placeholder factor functions should not mutate raw inputs."""

    raw = pd.DataFrame([{"ts_code": "000001.SZ", "roe_ttm": 0.1}])

    result = calculate_quality_factors(raw)
    result.loc[0, "roe_ttm"] = 0.2

    assert raw.loc[0, "roe_ttm"] == 0.1
