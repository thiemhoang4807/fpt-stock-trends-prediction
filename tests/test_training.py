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


def test_fold_scaler_does_not_learn_from_validation():
    frame = pd.DataFrame({"x": np.r_[np.arange(80), np.arange(20)+10000.], "next_log_return": np.sin(np.arange(100))*.01, "direction": np.arange(100)%2})
    for task,name in [("classification","Logistic Regression"),("regression","Linear Regression")]:
        spec=("tabular",train.candidate_models(task)[name][0])
        _,_,artifact=train.fit_candidate(spec,task,frame,["x"],np.arange(80),np.arange(81,100))
        scaler=artifact["model"].named_steps["standardscaler"]
        assert scaler.n_samples_seen_ == 80
        assert scaler.mean_[0] == pytest.approx(39.5)


def test_five_folds_have_purge_and_never_use_holdout():
    for a,b in train.cv_splits(850):
        assert a.max()+1 < b.min()
        assert b.max() < 850
    assert len(train.cv_splits(850)) == 5


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
    assert set(train._classifier_models()) == {"SVC", "Majority baseline", "Logistic Regression", "Random Forest", "XGBoost", "HistGradientBoosting"}
    assert set(train._regressor_models()) == {"Last-Close Baseline", "Ridge Regression", "SVR", "Linear Regression", "Random Forest Regressor", "XGBoost Regressor", "HistGradientBoosting Regressor"}


def test_exported_results_cover_both_branches_and_all_classifiers():
    root = Path(__file__).resolve().parents[1]
    metrics = pd.read_csv(root / "reports/classification_test_metrics.csv")
    matrices = pd.read_csv(root / "reports/confusion_matrices.csv")
    predictions = pd.read_csv(root / "reports/test_direction_predictions_by_model.csv")
    assert len(metrics) == len(matrices) == 30
    assert metrics.groupby("feature_set")["model"].nunique().tolist() == [15, 15]
    assert metrics["test_start"].nunique() == metrics["test_end"].nunique() == 1
    assert metrics["test_end"].iloc[0] == "2025-09-30"
    for row in metrics.itertuples():
        matrix = matrices.loc[(matrices["feature_set"] == row.feature_set) & (matrices["model"] == row.model)].iloc[0]
        assert int(matrix[["tn", "fp", "fn", "tp"]].sum()) == row.test_rows
        assert (matrix["tn"] + matrix["tp"]) / row.test_rows == pytest.approx(row.accuracy)
        per_session = predictions.loc[(predictions["feature_set"] == row.feature_set) & (predictions["model"] == row.model)]
        assert len(per_session) == row.test_rows
        assert float((per_session["direction"] == per_session["prediction"]).mean()) == pytest.approx(row.accuracy)


def test_regression_table_reports_five_models_per_branch_and_ordered_tolerances():
    root = Path(__file__).resolve().parents[1]
    metrics = pd.read_csv(root / "reports/regression_test_metrics.csv")
    assert len(metrics) == 32
    assert metrics.groupby("feature_set")["model"].nunique().tolist() == [16, 16]
    assert (metrics["tolerance_accuracy_0_5_percent"] <= metrics["tolerance_accuracy_1_percent"]).all()
    assert (metrics["tolerance_accuracy_1_percent"] <= metrics["tolerance_accuracy_2_percent"]).all()
    baselines = metrics.loc[metrics["model"].eq("Last-Close Baseline")]
    assert baselines["mae"].nunique() == 1
    assert baselines["directional_accuracy_nonflat_percent"].eq(0).all()


def test_published_selection_matches_cv_not_test():
    root=Path(__file__).resolve().parents[1]
    for task in ["classification","regression"]:
        metrics=pd.read_csv(root/f"reports/{task}_test_metrics.csv")
        selected=metrics.loc[metrics.selected_for_deployment].iloc[0]
        expected=metrics.cv_score.max() if task=="classification" else metrics.cv_score.min()
        assert selected.cv_score == pytest.approx(expected)


def test_price_predictions_are_reconstructed_from_log_return():
    root=Path(__file__).resolve().parents[1]
    p=pd.read_csv(root/"reports/test_price_predictions_by_model.csv")
    # XGBoost emits float32; exp(float32) differs from CSV float64 reconstruction by <0.02 VND.
    np.testing.assert_allclose(p.predicted_close,p.current_close*np.exp(p.prediction),rtol=2e-7,atol=1e-10)
