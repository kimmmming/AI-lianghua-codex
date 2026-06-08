"""Hard exclusion rule placeholders."""

from datetime import date

import pandas as pd


def apply_hard_exclusions(universe: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    """Apply implemented hard exclusions.

    Stage 1 does not implement real exclusion logic because the required input
    fields are not connected yet.
    """

    if "as_of_date" in universe.columns:
        frame_dates = pd.to_datetime(universe["as_of_date"]).dt.date
        if (frame_dates > as_of_date).any():
            raise ValueError("Universe contains rows dated after as_of_date.")
    return universe.copy()
