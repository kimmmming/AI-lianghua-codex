"""Configuration loading helpers."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class FactorGroupConfig(BaseModel):
    """Configuration for a factor group."""

    weight: float = Field(ge=0.0, le=1.0)
    factors: list[str]


class FactorConfig(BaseModel):
    """Top-level factor configuration."""

    factor_groups: dict[str, FactorGroupConfig]
    normalization: dict[str, Any]
    special_rules: dict[str, Any]

    @property
    def total_weight(self) -> float:
        """Return the sum of configured factor-group weights."""

        return sum(group.weight for group in self.factor_groups.values())

    @model_validator(mode="after")
    def validate_total_weight(self) -> "FactorConfig":
        """Validate that factor-group weights sum to one."""

        if abs(self.total_weight - 1.0) > 1e-9:
            raise ValueError("Factor-group weights must sum to 1.0.")
        return self


class SelectionConfig(BaseModel):
    """Configuration for final universe selection."""

    target_size: int = Field(gt=0)
    minimum_per_industry: int = Field(ge=0)
    maximum_industry_weight: float = Field(gt=0.0, le=1.0)
    ranking_key: str
    deterministic_tie_breakers: list[str]

    @property
    def maximum_per_industry(self) -> int:
        """Return the implied maximum number of selections per industry."""

        return int(self.target_size * self.maximum_industry_weight)


class PortfolioConfig(BaseModel):
    """Top-level portfolio selection configuration."""

    selection: SelectionConfig
    industry_allocation: dict[str, Any]


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return a dictionary."""

    resolved_path = Path(path)
    with resolved_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {resolved_path}")
    return data


def load_factor_config(path: str | Path = CONFIG_DIR / "factors.yaml") -> FactorConfig:
    """Load and validate factor configuration."""

    return FactorConfig.model_validate(load_yaml(path))


def load_portfolio_config(path: str | Path = CONFIG_DIR / "portfolio.yaml") -> PortfolioConfig:
    """Load and validate portfolio configuration."""

    return PortfolioConfig.model_validate(load_yaml(path))
