import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from time_series_analysis import stationarity


def test_stationarity_reports_opposite_nulls_and_nonrejection_correctly():
    x = np.random.default_rng(42).normal(size=1000)
    rows = stationarity(x, "noise", "train")
    assert rows[0]["test"] == "ADF" and rows[0]["reject_null_at_5pct"]
    assert rows[1]["test"] == "KPSS" and not rows[1]["reject_null_at_5pct"]
    assert rows[0]["null_hypothesis"] != rows[1]["null_hypothesis"]
    assert "not rejected" in rows[1]["conclusion"]
    assert "5%" in rows[0]["critical_values"]
