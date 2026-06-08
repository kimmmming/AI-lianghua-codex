"""Tests for data-source placeholders."""

from datetime import date

import pytest

from core600.data_sources.akshare_source import AKShareDataSource
from core600.data_sources.tushare_source import TushareDataSource


def test_tushare_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tushare implementation should fail clearly without a token."""

    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="TUSHARE_TOKEN"):
        TushareDataSource()


def test_akshare_placeholder_does_not_download_data() -> None:
    """Stage 1 AKShare implementation should refuse data downloads."""

    source = AKShareDataSource()

    with pytest.raises(NotImplementedError):
        source.fetch_stock_basic(as_of_date=date(2026, 6, 5))
