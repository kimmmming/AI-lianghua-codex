"""Tests for hard exclusion safeguards."""

from datetime import date

import pandas as pd
import pytest

from core600.exclusions import apply_hard_exclusions


def test_apply_hard_exclusions_rejects_future_rows() -> None:
    """Universe rows dated after as_of_date should be rejected."""

    universe = pd.DataFrame([{"ts_code": "000001.SZ", "as_of_date": "2026-06-06"}])

    with pytest.raises(ValueError, match="after as_of_date"):
        apply_hard_exclusions(universe, date(2026, 6, 5))
