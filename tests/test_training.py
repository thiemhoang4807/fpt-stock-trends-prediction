from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import train
from features import build_feature_table
from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS
from predict import predict_latest


def test_scaler_parameters_are_fitted_on_train_only(monkeypatch, tmp_path):
    count = 200
    dates = pd.bdate_range("2020-01-01", periods=count)
    table = pd.DataFrame({
        "date": dates,
        "target_date": dates + pd.offsets.BDay(1),
        "current_close": np.full(count, 100.0),
        "next_close": 100.0 + np.where(np.arange(count) % 2, 1.0, -1.0),
        "direction": np.arange(count) % 2,
        "x": np.r_[np.arange(170, dtype=float), np.arange(30, dtype=float) + 10000.0],
    })
    monkeypatch.setattr(train, "_classifier_models", lambda: {"Logistic Regression": Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression())])})
    monkeypatch.setattr(train, "_regressor_models", lambda: {"Linear Regression": Pipeline([("scaler", StandardScaler()), ("model", LinearRegression())])})
    result = train._fit_test_for_set("test", table, ["x"], tmp_path, tmp_path)
    for model in [result["class_models"]["Logistic Regression"], result["regression_models"]["Linear Regression"]]:
        scaler = model.named_steps["scaler"]
        assert scaler.n_samples_seen_ == 170
        assert scaler.mean_[0] == pytest.approx(84.5)
        assert scaler.mean_[0] != pytest.approx(table["x"].mean())


def test_predict_rejects_missing_latest_source_instead_of_reusing_old_session(tmp_path):
    dates = pd.bdate_range("2024-01-01", periods=100)
    close = 50.0 + np.sin(np.arange(100) / 3.0)
    prices = pd.DataFrame({"time": dates, "open": close - 0.1, "high": close + 0.4, "low": close - 0.5, "close": close, "volume": np.arange(100) + 1000})
    input_path = tmp_path / "prices.csv"
    prices.to_csv(input_path, index=False)
    features = build_feature_table(prices)
    supplement = pd.DataFrame({"date": features["date"]})
    for column in MODEL_SUPPLEMENTAL_COLUMNS:
        supplement[column] = 1.0
    supplement.loc[supplement.index[-1], "usd_vnd_rate"] = np.nan
    supplement_path = tmp_path / "supplement.csv"
    supplement.to_csv(supplement_path, index=False)
    model = DummyClassifier(strategy="most_frequent").fit(pd.DataFrame({"usd_vnd_rate": [1.0, 2.0]}), [0, 1])
    joblib.dump({"model": model, "model_name": "dummy", "feature_columns": ["usd_vnd_rate"]}, tmp_path / "best_classifier.joblib")
    joblib.dump({"strategy": "last_close", "model_name": "baseline", "feature_columns": ["current_close"]}, tmp_path / "best_regressor.joblib")
    with pytest.raises(ValueError, match="Latest session is missing"):
        predict_latest(input_path, tmp_path, tmp_path / "prediction.json", supplement_path)


def test_all_required_model_families_are_available():
    assert set(train._classifier_models()) == {"Majority baseline", "Logistic Regression", "Random Forest", "XGBoost", "HistGradientBoosting"}
    assert set(train._regressor_models()) == {"Linear Regression", "Random Forest Regressor", "XGBoost Regressor", "HistGradientBoosting Regressor"}


def test_exported_results_cover_both_branches_and_all_classifiers():
    root = Path(__file__).resolve().parents[1]
    metrics = pd.read_csv(root / "reports/classification_test_metrics.csv")
    matrices = pd.read_csv(root / "reports/confusion_matrices.csv")
    predictions = pd.read_csv(root / "reports/test_direction_predictions_by_model.csv")
    assert len(metrics) == len(matrices) == 10
    assert metrics.groupby("feature_set")["model"].nunique().tolist() == [5, 5]
    assert metrics["test_start"].nunique() == metrics["test_end"].nunique() == 1
    assert metrics["test_end"].iloc[0] == "2025-09-30"
    for row in metrics.itertuples():
        matrix = matrices.loc[(matrices["feature_set"] == row.feature_set) & (matrices["model"] == row.model)].iloc[0]
        assert int(matrix[["tn", "fp", "fn", "tp"]].sum()) == row.test_rows
        assert (matrix["tn"] + matrix["tp"]) / row.test_rows == pytest.approx(row.accuracy)
        per_session = predictions.loc[(predictions["feature_set"] == row.feature_set) & (predictions["model"] == row.model)]
        assert len(per_session) == row.test_rows
        assert float((per_session["direction"] == per_session["predicted_direction"]).mean()) == pytest.approx(row.accuracy)


def test_regression_table_reports_five_models_per_branch_and_ordered_tolerances():
    root = Path(__file__).resolve().parents[1]
    metrics = pd.read_csv(root / "reports/regression_test_metrics.csv")
    assert len(metrics) == 10
    assert metrics.groupby("feature_set")["model"].nunique().tolist() == [5, 5]
    assert (metrics["tolerance_accuracy_0_5_percent"] <= metrics["tolerance_accuracy_1_percent"]).all()
    assert (metrics["tolerance_accuracy_1_percent"] <= metrics["tolerance_accuracy_2_percent"]).all()
    baselines = metrics.loc[metrics["model"].eq("Last-Close Baseline")]
    assert baselines["mae"].nunique() == 1
    assert baselines["directional_accuracy_nonflat_percent"].eq(0).all()
