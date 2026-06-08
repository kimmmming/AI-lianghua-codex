"""Scoring utilities."""

import pandas as pd


def require_as_of_date(frame: pd.DataFrame) -> None:
    """Validate that a DataFrame carries as_of_date for auditability."""

    if "as_of_date" not in frame.columns:
        raise ValueError("Outputs must include as_of_date.")
