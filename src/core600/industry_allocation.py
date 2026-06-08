"""Industry allocation placeholders."""

import pandas as pd


def allocate_by_industry(scored: pd.DataFrame, target_size: int) -> pd.DataFrame:
    """Placeholder for industry-constrained allocation."""

    if target_size <= 0:
        raise ValueError("target_size must be positive.")
    return scored.copy()
