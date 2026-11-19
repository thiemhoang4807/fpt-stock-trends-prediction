"""Leakage, selection, signed outputs, and saved-result consistency."""

from pathlib import Path
import sys
import json
import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import train
from features import build_feature_table
from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS
from predict import predict_latest
from metrics import evaluate_returns, restore_price, direction_from_return
from prepare import feature_groups


def test_fold_scaler_does_not_learn_from_validation():
    frame = pd.DataFrame(
        {
            "x": np.r_[np.arange(80), np.arange(20) + 10000.0],
            "next_log_return": np.sin(np.arange(100)) * 0.01,
        }
    )
    _, artifact = train.fit_candidate(
        dict(kind="ridge", alpha=10), frame, ["x"], np.arange(80), np.arange(81, 100)
    )
    scaler = artifact["model"].named_steps["standardscaler"]
    assert scaler.n_samples_seen_ == 80
    assert scaler.mean_[0] == pytest.approx(39.5)


def test_five_folds_have_purge_and_never_use_holdout():
    for a, b in train.cv_splits(850):
        assert a.max() + 1 < b.min()
        assert b.max() < 850
    assert len(train.cv_splits(850)) == 5


def test_zero_forecast_is_flat_and_wrong_on_nonflat_sessions():
    frame = pd.DataFrame(
        dict(
            current_close=[100, 100, 100],
            next_close=[110, 90, 100],
            next_log_return=np.log([1.1, 0.9, 1]),
        )
    )
    result = evaluate_returns(frame, np.zeros(3))
    assert result["directional_accuracy_nonflat_percent"] == 0
    assert result["nonflat_rows"] == 2
    np.testing.assert_array_equal(direction_from_return([-0.01, 0, 0.01]), [-1, 0, 1])
    np.testing.assert_allclose(restore_price([100, 100], np.log([1.1, 0.9])), [110, 90])


@pytest.mark.parametrize("values", [[float("nan")], [float("inf")]])
def test_invalid_forecasts_are_rejected(values):
    with pytest.raises(ValueError):
        direction_from_return(values)


def test_predict_rejects_missing_latest_source(tmp_path):
    dates = pd.bdate_range("2024-01-01", periods=100)
    close = 50 + np.sin(np.arange(100) / 3)
    prices = pd.DataFrame(
        dict(
            time=dates,
            open=close - 0.1,
            high=close + 0.4,
            low=close - 0.5,
            close=close,
            volume=np.arange(100) + 1000,
        )
    )
    input_path = tmp_path / "prices.csv"
    prices.to_csv(input_path, index=False)
    features = build_feature_table(prices)
    supplement = pd.DataFrame({"date": features.date})
    for column in MODEL_SUPPLEMENTAL_COLUMNS:
        supplement[column] = 1.0
    supplement.loc[supplement.index[-1], "usd_vnd_rate"] = np.nan
    supplement_path = tmp_path / "supplement.csv"
    supplement.to_csv(supplement_path, index=False)
    model = DummyRegressor(strategy="constant", constant=0).fit(
        pd.DataFrame({"usd_vnd_rate": [1.0, 2.0]}), [0.0, 0.0]
    )
    joblib.dump(
        dict(model=model, model_name="baseline", feature_columns=["usd_vnd_rate"]),
        tmp_path / "best_regressor.joblib",
    )
    with pytest.raises(ValueError, match="Latest session is missing"):
        predict_latest(
            input_path, tmp_path, tmp_path / "prediction.json", supplement_path
        )
    supplement.loc[supplement.index[-1], "usd_vnd_rate"] = 1
    supplement.to_csv(supplement_path, index=False)
    result = predict_latest(
        input_path, tmp_path, tmp_path / "prediction.json", supplement_path
    )
    assert result["predicted_direction"] == "unchanged"
    assert result["predicted_next_close"] == result["current_close"]
    assert not any("probability" in k or "confidence" in k for k in result)


def test_main_choice_depends_only_on_cv():
    cv = pd.DataFrame(
        dict(
            config_id=[
                "last_close",
                "ridge",
                "xgboost_price",
                "arima",
                "gru_20",
                "gru_60",
            ],
            cv_rmse_mean=[0.03, 0.02, 0.04, 0.01, 0.06, 0.05],
            test_rmse=[0, 1, 2, 3, 4, 5],
        )
    )
    main, selected = train.select_main_ids(cv)
    assert len(main) == 5 and main[-1] == "gru_60" and selected == "arima"
    cv["test_rmse"] = -cv.test_rmse
    assert train.select_main_ids(cv) == (main, selected)


def test_published_metrics_reconstruct_from_each_prediction():
    metrics = pd.read_csv(ROOT / "reports/all_test_metrics.csv")
    predictions = pd.read_csv(ROOT / "reports/test_predictions.csv")
    split = json.loads((ROOT / "reports/training_summary.json").read_text())["split"]
    expected_dates = predictions.loc[predictions.config_id.eq("last_close"), "target_date"].tolist()
    assert len(expected_dates) == split["test_rows"] == 455
    assert expected_dates == sorted(set(expected_dates))
    assert expected_dates[0] == split["test_target_date_start"]
    assert expected_dates[-1] == split["test_target_date_end"]
    assert len(metrics) == 9
    for row in metrics.itertuples():
        p = predictions.loc[predictions.config_id.eq(row.config_id)].copy()
        assert p.target_date.tolist() == expected_dates
        assert p.target_date.iloc[-1] == "2025-09-30"
        np.testing.assert_allclose(
            p.predicted_close,
            restore_price(p.current_close, p.predicted_log_return),
            rtol=1e-12,
        )
        frame = p.rename(
            columns={
                "actual_close": "next_close",
                "actual_log_return": "next_log_return",
            }
        )
        computed = evaluate_returns(frame, p.predicted_log_return.to_numpy())
        for name, value in computed.items():
            assert getattr(row, name) == pytest.approx(value, abs=1e-10)
        assert (
            row.tolerance_accuracy_0_5_percent
            <= row.tolerance_accuracy_1_percent
            <= row.tolerance_accuracy_2_percent
        )


def test_tables_artifacts_and_fixed_ablation_design():
    groups = feature_groups()
    assert list(map(len, groups.values())) == [32, 38, 42]
    for name, count in [
        ("main_benchmark", 5),
        ("ablation", 3),
        ("lookback", 2),
        ("statistical_extension", 2),
    ]:
        assert len(pd.read_csv(ROOT / f"reports/{name}.csv")) == count
    plan = json.loads((ROOT / "reports/experiment_plan.json").read_text())
    cv = pd.read_csv(ROOT / "reports/cv_summary.csv")
    assert train.select_main_ids(cv) == (plan["main_ids"], plan["selected_id"])
    configurations = plan["selected_configurations"]
    assert (
        configurations["xgboost_price"]
        == configurations["xgboost_macro"]
        == configurations["xgboost_financial"]
    )
    assert len(list((ROOT / "models/evaluation").glob("*.joblib"))) == 9
    assert not (ROOT / "models/best_classifier.joblib").exists()
    assert set(pd.read_csv(ROOT / "reports/cv_fold_metrics.csv").fold) == set(
        range(1, 6)
    )
