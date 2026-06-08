"""Reporting placeholders."""

from datetime import date
from pathlib import Path


def output_path_with_as_of_date(output_dir: Path, stem: str, as_of_date: date, suffix: str) -> Path:
    """Build an output path that includes as_of_date."""

    if not stem:
        raise ValueError("Output stem must not be empty.")
    if not suffix.startswith("."):
        raise ValueError("Output suffix must start with '.'.")
    return output_dir / f"{stem}_{as_of_date.isoformat()}{suffix}"
