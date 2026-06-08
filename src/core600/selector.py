"""Core 600 selector placeholder."""

from datetime import date

import pandas as pd


def select_core600(as_of_date: date, target_size: int = 600) -> pd.DataFrame:
    """Placeholder selector that refuses to fabricate a stock list."""

    if target_size <= 0:
        raise ValueError("target_size must be positive.")
    raise NotImplementedError(
        f"Core 600 selection for {as_of_date} is not implemented in stage 1."
    )
