from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from features import FEATURE_COLUMNS, build_feature_table
from train import _chronological_splits


def _synthetic_ohlcv(rows: int = 180) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=rows)
    close = 100.0 + np.arange(rows) * 0.2 + np.sin(np.arange(rows) / 4.0)
    return pd.DataFrame(
        {
            "time": dates,
            "open": close - 0.1,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
            "volume": 1000 + np.arange(rows) * 10,
        }
    )


def test_next_session_target_is_aligned_to_following_close():
    data = _synthetic_ohlcv()
    features = build_feature_table(data)
    row = features.loc[features["date"].eq(data.loc[60, "time"])].iloc[0]
    assert row["next_close"] == data.loc[61, "close"]
    assert row["target_date"] == data.loc[61, "time"]
    expected_direction = 1.0 if data.loc[61, "close"] > data.loc[60, "close"] else 0.0
    assert row["direction"] == expected_direction


def test_past_features_do_not_change_when_future_prices_change():
    data = _synthetic_ohlcv()
    changed = data.copy()
    future_mask = changed.index >= 70
    changed.loc[future_mask, ["open", "high", "low", "close"]] *= 1.5

    original_features = build_feature_table(data)
    changed_features = build_feature_table(changed)
    date_to_check = data.loc[60, "time"]
    original_row = original_features.loc[original_features["date"].eq(date_to_check), FEATURE_COLUMNS].iloc[0]
    changed_row = changed_features.loc[changed_features["date"].eq(date_to_check), FEATURE_COLUMNS].iloc[0]
    pd.testing.assert_series_equal(original_row, changed_row)


def test_splits_are_chronological_by_target_date():
    table = build_feature_table(_synthetic_ohlcv())
    masks, _ = _chronological_splits(table)
    train_end = table.loc[masks["train"], "target_date"].max()
    validation_start = table.loc[masks["validation"], "target_date"].min()
    validation_end = table.loc[masks["validation"], "target_date"].max()
    test_start = table.loc[masks["test"], "target_date"].min()
    assert train_end < validation_start
    assert validation_end < test_start
