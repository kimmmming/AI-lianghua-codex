"""Tests for configuration loading."""

import pytest

from core600.config import FactorConfig, load_factor_config, load_portfolio_config


def test_factor_weights_sum_to_one() -> None:
    """Configured factor weights should sum to one."""

    config = load_factor_config()

    assert config.total_weight == 1.0


def test_factor_config_rejects_weights_that_do_not_sum_to_one() -> None:
    """Factor weights should fail fast when they are not auditable."""

    with pytest.raises(ValueError, match="sum to 1.0"):
        FactorConfig.model_validate(
            {
                "factor_groups": {
                    "quality": {"weight": 0.3, "factors": ["roe_ttm"]},
                    "growth": {"weight": 0.3, "factors": ["revenue_yoy"]},
                },
                "normalization": {},
                "special_rules": {},
            }
        )


def test_portfolio_config_derives_industry_cap() -> None:
    """Industry cap should be derived from target size and max weight."""

    config = load_portfolio_config()

    assert config.selection.target_size == 600
    assert config.selection.maximum_per_industry == 90
