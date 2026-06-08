"""Tests for selector placeholder safeguards."""

from datetime import date

import pytest

from core600.selector import select_core600


def test_selector_refuses_to_fabricate_stage_one_result() -> None:
    """Stage 1 selector should not return a fake Core 600 list."""

    with pytest.raises(NotImplementedError, match="not implemented"):
        select_core600(date(2026, 6, 5))


def test_selector_rejects_invalid_target_size() -> None:
    """Selection size must be valid before any implementation runs."""

    with pytest.raises(ValueError, match="target_size"):
        select_core600(date(2026, 6, 5), target_size=0)
