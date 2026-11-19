"""Checks for the distinction between missing metadata and invalid numbers."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_data_quality import review


def test_missing_release_dates_are_not_counted_as_infinite_values():
    sources = review()["source_files"]
    for name in ("cpi", "gdp"):
        source = sources[name]
        assert source["nulls_by_column"]["publication_date"] == source["rows"]
        assert source["nonfinite_numeric_values"] == 0
