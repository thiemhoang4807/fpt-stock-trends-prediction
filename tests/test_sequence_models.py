from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sequence_models import (
    _windows,
    fit_predict_sequence,
    fit_predict_statistical,
    predict_sequence_artifact,
)


def sample_table(count=130):
    dates = pd.bdate_range("2020-01-01", periods=count + 1)
    returns = np.sin(np.arange(count) / 3) * 0.01
    return pd.DataFrame(
        {
            "session_index": np.arange(count),
            "date": dates[:-1],
            "target_date": dates[1:],
            "current_close": np.full(count, 100.0),
            "next_close": 100 * np.exp(returns),
            "next_log_return": returns,
            "direction": (returns > 0).astype(float),
            "x": np.sin(np.arange(count) / 5),
        }
    )


def test_window_keeps_every_observed_session_and_rejects_gaps():
    data = sample_table()
    data.loc[5, "session_index"] = 1000
    with pytest.raises(ValueError, match="skip trading sessions"):
        _windows(data, ["x"], np.array([10]), 10)


def test_sequence_scaler_and_weights_do_not_depend_on_future_values():
    data = sample_table()
    changed = data.copy()
    changed.loc[90:, "x"] += 1000
    changed.loc[90:, "next_log_return"] += 1000
    args = dict(
        kind="GRU",
        task="regression",
        feature_columns=["x"],
        train_indices=np.arange(10, 80),
        eval_indices=np.arange(81, 90),
        lookback=10,
        epochs=1,
        hidden_size=4,
    )
    prediction, artifact = fit_predict_sequence(table=data, **args)
    other_prediction, other = fit_predict_sequence(table=changed, **args)
    np.testing.assert_allclose(prediction, other_prediction)
    np.testing.assert_allclose(artifact["scaler"].mean_, other["scaler"].mean_)
    assert artifact["scaler_last_session_index"] == 79
    assert artifact["scaler"].n_samples_seen_ == 79


def test_common_table_windows_use_full_context_not_compressed_rows():
    context = sample_table()
    common = context.iloc[60:].copy().reset_index(drop=True)
    common.attrs["sequence_context"] = context
    prediction, artifact = fit_predict_sequence(
        "LSTM",
        "classification",
        common,
        ["x"],
        np.arange(20),
        np.arange(21, 25),
        lookback=60,
        epochs=1,
        hidden_size=4,
    )
    assert len(prediction) == 4
    assert ((prediction >= 0) & (prediction <= 1)).all()
    latest = predict_sequence_artifact(artifact, common)
    assert latest.shape == (1,)
    assert artifact["scaler_last_session_index"] == 79


def test_arima_forecast_never_uses_current_or_future_outcome():
    data = sample_table()
    modified = data.copy()
    modified.loc[85:, "next_log_return"] += 0.2
    args = dict(
        kind="ARIMA",
        exog_columns=[],
        train_indices=np.arange(60),
        eval_indices=np.arange(61, 95),
        order=(1, 0, 0),
    )
    first, artifact = fit_predict_statistical(table=data, **args)
    second, _ = fit_predict_statistical(table=modified, **args)
    # Prediction for position 85 precedes observing its altered target.
    np.testing.assert_allclose(first[:25], second[:25])
    assert not np.allclose(first[25:], second[25:])
    assert artifact["training_context_rows"] == 60


def test_sarimax_scaler_and_imputer_fit_train_only():
    data = sample_table()
    data.loc[10, "x"] = np.nan
    data.loc[61:, "x"] += 10000
    _, artifact = fit_predict_statistical(
        "SARIMAX", data, ["x"], np.arange(60), np.arange(61, 65), (1, 0, 0)
    )
    expected = data.loc[:59, "x"].fillna(data.loc[:59, "x"].median())
    assert artifact["scaler"].mean_[0] == pytest.approx(expected.mean())
    assert artifact["training_exog_missing_cells_imputed"] == 1
