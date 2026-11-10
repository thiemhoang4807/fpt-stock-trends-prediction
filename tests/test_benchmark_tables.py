"""Report selection must never depend on the observed Test performance."""

from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from benchmark_tables import select_representatives


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_representatives_are_selected_by_cv_only(task):
    cv = pd.read_csv(ROOT / "reports/cv_summary.csv")
    metrics = pd.read_csv(ROOT / f"reports/{task}_test_metrics.csv")
    selected = select_representatives(cv, metrics, task)
    assert selected.groupby("feature_set").size().tolist() == [9, 9]
    changed = metrics.copy()
    for column in changed.select_dtypes(include="number"):
        changed[column] = -changed[column] + 1000
    repeated = select_representatives(cv, changed, task)
    pd.testing.assert_frame_equal(
        selected[["feature_set", "family", "model", "cv_mean", "cv_std"]],
        repeated[["feature_set", "family", "model", "cv_mean", "cv_std"]],
    )


def test_missing_test_row_is_not_silently_dropped():
    cv = pd.DataFrame(
        [
            dict(
                feature_set="branch",
                task="classification",
                model="LSTM L=10",
                balanced_accuracy_mean=0.6,
                balanced_accuracy_std=0.02,
            )
        ]
    )
    metrics = pd.DataFrame(columns=["feature_set", "model", "accuracy"])
    with pytest.raises(ValueError, match="no corresponding Test row"):
        select_representatives(cv, metrics, "classification")
