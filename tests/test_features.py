from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from features import FEATURE_COLUMNS, FULL_OHLCV_FEATURE_COLUMNS, PRICE_ONLY_FEATURE_COLUMNS, build_feature_table, load_price_data
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
    original_row = original_features.loc[original_features["date"].eq(date_to_check), PRICE_ONLY_FEATURE_COLUMNS].iloc[0]
    changed_row = changed_features.loc[changed_features["date"].eq(date_to_check), PRICE_ONLY_FEATURE_COLUMNS].iloc[0]
    pd.testing.assert_series_equal(original_row, changed_row)


def test_splits_are_chronological_by_target_date():
    table = build_feature_table(_synthetic_ohlcv())
    masks, _ = _chronological_splits(table)
    train_end = table.loc[masks["train"], "target_date"].max()
    test_start = table.loc[masks["test"], "target_date"].min()
    assert train_end < test_start
    assert "validation" not in masks
    labeled_rows = int(table["target_date"].notna().sum())
    assert int(masks["train"].sum()) == int(labeled_rows * 0.85)
    assert int(masks["test"].sum()) == labeled_rows - int(labeled_rows * 0.85)


def test_full_ohlcv_features_are_known_at_close_of_current_session():
    data = _synthetic_ohlcv()
    features = build_feature_table(data)
    row = features.loc[features["date"].eq(data.loc[60, "time"])].iloc[0]
    current = data.loc[60]
    previous = data.loc[59, "close"]
    assert np.isclose(row["candle_range_pct"], (current["high"] - current["low"]) / current["close"])
    assert np.isclose(row["candle_body_pct"], (current["close"] - current["open"]) / current["open"])
    assert np.isclose(row["overnight_gap_pct"], current["open"] / previous - 1.0)
    assert np.isclose(row["close_location_in_range"], (current["close"] - current["low"]) / (current["high"] - current["low"]))
    assert set(FULL_OHLCV_FEATURE_COLUMNS).issubset(features.columns)


def test_flat_range_candle_uses_neutral_close_position_without_dropping_row():
    data = _synthetic_ohlcv()
    data.loc[80, ["open", "high", "low", "close"]] = 100.0
    features = build_feature_table(data)
    row = features.loc[features["date"].eq(data.loc[80, "time"])].iloc[0]
    assert row["close_location_in_range"] == 0.5


def test_cutoff_is_applied_before_next_session_label_is_constructed(tmp_path):
    data = _synthetic_ohlcv(180)
    data["time"] = pd.bdate_range(end="2025-10-02", periods=len(data))
    path = tmp_path / "prices.csv"
    data.to_csv(path, index=False)
    clipped = load_price_data(path)
    features = build_feature_table(clipped)
    assert clipped["time"].max() == pd.Timestamp("2025-09-30")
    assert features.iloc[-1]["target_date"] is pd.NaT or pd.isna(features.iloc[-1]["target_date"])
    assert pd.isna(features.iloc[-1]["next_close"])
    assert features["target_date"].dropna().max() == pd.Timestamp("2025-09-30")


def test_price_branch_includes_current_ohlcv_and_excludes_future_outcomes():
    data = _synthetic_ohlcv()
    features = build_feature_table(data)
    row = features.loc[features["date"].eq(data.loc[60, "time"])].iloc[0]
    assert len(PRICE_ONLY_FEATURE_COLUMNS) == 32
    for raw_name in ("open", "high", "low", "close", "volume"):
        assert row[f"current_{raw_name}"] == data.loc[60, raw_name]
    assert not {"direction", "next_close", "next_return", "target_date"}.intersection(PRICE_ONLY_FEATURE_COLUMNS)
