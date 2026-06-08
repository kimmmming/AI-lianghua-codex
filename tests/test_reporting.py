"""Tests for reporting path helpers."""

from datetime import date
from pathlib import Path

import pytest

from core600.reporting import output_path_with_as_of_date


def test_output_path_includes_as_of_date() -> None:
    """Generated output paths must carry as_of_date."""

    path = output_path_with_as_of_date(
        Path("outputs"),
        "core600",
        date(2026, 6, 5),
        ".csv",
    )

    assert path == Path("outputs") / "core600_2026-06-05.csv"


def test_output_path_rejects_suffix_without_dot() -> None:
    """Suffix validation prevents ambiguous output filenames."""

    with pytest.raises(ValueError, match="suffix"):
        output_path_with_as_of_date(Path("outputs"), "core600", date(2026, 6, 5), "csv")
