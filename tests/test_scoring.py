"""Tests for scoring safeguards."""

import pandas as pd
import pytest

from core600.scoring import require_as_of_date


def test_require_as_of_date_rejects_missing_column() -> None:
    """Auditable outputs must carry as_of_date."""

    with pytest.raises(ValueError, match="as_of_date"):
        require_as_of_date(pd.DataFrame([{"ts_code": "000001.SZ"}]))
