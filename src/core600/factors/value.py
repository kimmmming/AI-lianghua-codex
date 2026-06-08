"""Value factor placeholders."""

import pandas as pd


def calculate_value_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Return value-factor input unchanged until real formulas are defined."""

    return frame.copy()
