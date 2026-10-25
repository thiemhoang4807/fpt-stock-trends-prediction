"""Train next-session direction and price models with chronological 85/15 splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from features import (
    FULL_OHLCV_FEATURE_COLUMNS,
    PRICE_ONLY_FEATURE_COLUMNS,
    RESEARCH_END_DATE,
    load_price_data,
)
from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS
from prepare import build_experiment_table


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
DEFAULT_SUPPLEMENTAL = ROOT / "data" / "processed" / "fpt_multisource_features.csv"
RANDOM_STATE = 42
MIN_PARTITION_ROWS = 20


def _chronological_splits(table: pd.DataFrame) -> tuple[dict[str, pd.Series], dict[str, str]]:
    """Split labeled examples into the first 85% and last 15% by target date."""
    labeled = table.loc[table["target_date"].notna()].sort_values("target_date")
    if len(labeled) < 40:
        raise ValueError(f"At least 40 labeled rows are required; found {len(labeled)}")
    train_count = max(1, min(len(labeled) - 1, int(len(labeled) * 0.85)))
    train_end = pd.Timestamp(labeled.iloc[train_count - 1]["target_date"])
    test_start = pd.Timestamp(labeled.iloc[train_count]["target_date"])
    target_dates = pd.to_datetime(table["target_date"])
    masks = {
        "train": target_dates.notna() & target_dates.le(train_end),
        "test": target_dates.notna() & target_dates.gt(train_end),
    }
    boundaries = {
        "train_target_date_start": pd.Timestamp(labeled.iloc[0]["target_date"]).strftime("%Y-%m-%d"),
        "train_target_date_end": train_end.strftime("%Y-%m-%d"),
        "test_target_date_start": test_start.strftime("%Y-%m-%d"),
        "test_target_date_end": pd.Timestamp(labeled.iloc[-1]["target_date"]).strftime("%Y-%m-%d"),
        "split_method": "chronological by target session date; first 85% train, last 15% test",
        "labeled_rows": int(len(labeled)),
        "train_rows": int(train_count),
        "test_rows": int(len(labeled) - train_count),
    }
    if not masks["train"].any() or not masks["test"].any():
        raise RuntimeError("Chronological split produced an empty partition")
    return masks, boundaries


def _classifier_models() -> dict[str, object]:
    return {
        "Majority baseline": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=1.0,
                        class_weight="balanced",
                        max_iter=3000,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=350,
            max_depth=8,
            min_samples_leaf=20,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=220,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=8,
            reg_lambda=3.0,
            eval_metric="logloss",
            n_jobs=1,
            random_state=RANDOM_STATE,
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=160,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=RANDOM_STATE,
        ),
    }


def _regressor_models() -> dict[str, object]:
    return {
        "Linear Regression": Pipeline(
            [("scaler", StandardScaler()), ("model", LinearRegression())]
        ),
        "Random Forest Regressor": RandomForestRegressor(
            n_estimators=350,
            max_depth=8,
            min_samples_leaf=20,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "XGBoost Regressor": XGBRegressor(
            n_estimators=240,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=8,
            reg_lambda=3.0,
            objective="reg:squarederror",
            n_jobs=1,
            random_state=RANDOM_STATE,
        ),
        "HistGradientBoosting Regressor": HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=160,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=RANDOM_STATE,
        ),
    }


def _classification_metrics(y_true, y_pred, y_probability) -> dict[str, float]:
    result = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision_up": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_up": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_up": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
    }
    result["roc_auc"] = (
        float(roc_auc_score(y_true, y_probability))
        if len(np.unique(y_true)) == 2
        else float("nan")
    )
    return result


def _regression_metrics(y_true, y_pred, current_close) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    current_close = np.asarray(current_close, dtype=float)
    actual_direction = np.sign(y_true - current_close)
    predicted_direction = np.sign(y_pred - current_close)
    nonflat = actual_direction != 0
    directional_accuracy = (
        float(np.mean(actual_direction[nonflat] == predicted_direction[nonflat]))
        if nonflat.any()
        else float("nan")
    )
    relative_error = np.abs(y_pred - y_true) / np.maximum(np.abs(y_true), np.finfo(float).eps)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape_percent": float(mean_absolute_percentage_error(y_true, y_pred) * 100.0),
        "directional_accuracy_nonflat_percent": directional_accuracy * 100.0,
        "tolerance_accuracy_0_5_percent": float(np.mean(relative_error <= 0.005) * 100.0),
        "tolerance_accuracy_1_percent": float(np.mean(relative_error <= 0.01) * 100.0),
        "tolerance_accuracy_2_percent": float(np.mean(relative_error <= 0.02) * 100.0),
    }


def _fit_test_for_set(
    feature_set: str,
    table: pd.DataFrame,
    feature_columns: list[str],
    reports_dir: Path,
    models_dir: Path,
) -> dict:
    data = table.loc[
        table["target_date"].notna() & table[feature_columns].notna().all(axis=1)
    ].copy().reset_index(drop=True)
    masks, bounds = _chronological_splits(data)
    for part in ("train", "test"):
        if int(masks[part].sum()) < MIN_PARTITION_ROWS:
            raise ValueError(f"{feature_set} {part} has fewer than {MIN_PARTITION_ROWS} usable rows")

    class_data = data.loc[data["direction"].notna()].copy().reset_index(drop=True)
    train_end = pd.Timestamp(bounds["train_target_date_end"])
    class_masks = {
        "train": class_data["target_date"].le(train_end),
        "test": class_data["target_date"].gt(train_end),
    }
    bounds["classification_train_rows"] = int(class_masks["train"].sum())
    bounds["classification_test_rows"] = int(class_masks["test"].sum())
    if min(int(class_masks["train"].sum()), int(class_masks["test"].sum())) < MIN_PARTITION_ROWS:
        raise ValueError(f"{feature_set} has too few non-flat classification examples")
    y_class = class_data["direction"].astype(int)
    if y_class.loc[class_masks["train"]].nunique() < 2:
        raise ValueError(f"{feature_set} training classification set contains only one class")

    classification_rows = []
    class_models = {}
    class_predictions = {}
    for model_name, model in _classifier_models().items():
        model.fit(class_data.loc[class_masks["train"], feature_columns], y_class.loc[class_masks["train"]])
        prediction = model.predict(class_data.loc[class_masks["test"], feature_columns]).astype(int)
        probability = model.predict_proba(class_data.loc[class_masks["test"], feature_columns])[:, 1]
        metrics = _classification_metrics(y_class.loc[class_masks["test"]], prediction, probability)
        classification_rows.append(
            {
                "feature_set": feature_set,
                "model": model_name,
                "test_rows": int(class_masks["test"].sum()),
                "test_start": pd.Timestamp(class_data.loc[class_masks["test"], "target_date"].min()).strftime("%Y-%m-%d"),
                "test_end": pd.Timestamp(class_data.loc[class_masks["test"], "target_date"].max()).strftime("%Y-%m-%d"),
                **metrics,
            }
        )
        class_models[model_name] = model
        class_predictions[model_name] = (prediction, probability)

    regression_features = list(dict.fromkeys([*feature_columns, "current_close"]))
    y_regression = data["next_close"]
    regression_rows = []
    regression_models = {}
    regression_predictions = {}

    persistence = data.loc[masks["test"], "current_close"].to_numpy(dtype=float)
    persistence_metrics = _regression_metrics(
        y_regression.loc[masks["test"]], persistence, data.loc[masks["test"], "current_close"]
    )
    regression_rows.append(
        {
            "feature_set": feature_set,
            "model": "Last-Close Baseline",
            "test_rows": int(masks["test"].sum()),
            "test_start": bounds["test_target_date_start"],
            "test_end": bounds["test_target_date_end"],
            **persistence_metrics,
        }
    )
    regression_predictions["Last-Close Baseline"] = persistence
    for model_name, model in _regressor_models().items():
        model.fit(data.loc[masks["train"], regression_features], y_regression.loc[masks["train"]])
        prediction = model.predict(data.loc[masks["test"], regression_features])
        metrics = _regression_metrics(
            y_regression.loc[masks["test"]], prediction, data.loc[masks["test"], "current_close"]
        )
        regression_rows.append(
            {
                "feature_set": feature_set,
                "model": model_name,
                "test_rows": int(masks["test"].sum()),
                "test_start": bounds["test_target_date_start"],
                "test_end": bounds["test_target_date_end"],
                **metrics,
            }
        )
        regression_models[model_name] = model
        regression_predictions[model_name] = prediction

    return {
        "feature_set": feature_set,
        "feature_columns": feature_columns,
        "regression_feature_columns": regression_features,
        "data": data,
        "class_data": class_data,
        "masks": masks,
        "class_masks": class_masks,
        "boundaries": bounds,
        "classification_rows": classification_rows,
        "regression_rows": regression_rows,
        "class_models": class_models,
        "class_predictions": class_predictions,
        "regression_models": regression_models,
        "regression_predictions": regression_predictions,
    }


def _refit_selected_model(
    experiment: dict,
    task: str,
    selected_name: str,
    models_dir: Path,
) -> dict:
    feature_set = experiment["feature_set"]
    data = experiment["data"]
    if task == "classification":
        feature_columns = experiment["feature_columns"]
        class_data = experiment["class_data"]
        y = class_data["direction"].astype(int)
        if selected_name == "Majority baseline":
            model = DummyClassifier(strategy="most_frequent")
        else:
            model = _classifier_models()[selected_name]
        model.fit(class_data[feature_columns], y)
        artifact = {
            "model": model,
            "model_name": selected_name,
            "feature_set": feature_set,
            "feature_columns": feature_columns,
            "positive_class": "up",
            "trained_through_target_date": pd.Timestamp(class_data["target_date"].max()).strftime("%Y-%m-%d"),
            "fit_scope": "all available labeled examples, after train/test metrics were recorded",
        }
        path = models_dir / "best_classifier.joblib"
    else:
        feature_columns = experiment["regression_feature_columns"]
        if selected_name == "Last-Close Baseline":
            artifact = {
                "strategy": "last_close",
                "model_name": selected_name,
                "feature_set": feature_set,
                "feature_columns": feature_columns,
                "fit_scope": "persistence baseline; no fitted parameters",
            }
        else:
            model = _regressor_models()[selected_name]
            model.fit(data[feature_columns], data["next_close"])
            artifact = {
                "strategy": "estimator",
                "model": model,
                "model_name": selected_name,
                "feature_set": feature_set,
                "feature_columns": feature_columns,
                "trained_through_target_date": pd.Timestamp(data["target_date"].max()).strftime("%Y-%m-%d"),
                "fit_scope": "all available labeled examples, after train/test metrics were recorded",
            }
        path = models_dir / "best_regressor.joblib"
    joblib.dump(artifact, path)
    return artifact


def run_training(
    input_path: Path,
    figures_dir: Path,
    reports_dir: Path,
    models_dir: Path,
    processed_dir: Path,
    supplemental_path: Path = DEFAULT_SUPPLEMENTAL,
) -> dict:
    for directory in (figures_dir, reports_dir, models_dir, processed_dir):
        directory.mkdir(parents=True, exist_ok=True)
    price_data = load_price_data(input_path)
    base_table, common_rows, branch_columns = build_experiment_table(input_path, supplemental_path)
    base_table.to_csv(processed_dir / "fpt_next_session_features.csv", index=False)
    common_rows.to_csv(processed_dir / "fpt_two_branch_features.csv", index=False)

    # Both branches use the exact same eligible session dates and the exact
    # same 85/15 boundary. This makes the difference attributable to inputs,
    # rather than to an easier or later test window.
    supplemental_columns = list(MODEL_SUPPLEMENTAL_COLUMNS)
    experiments = {}
    skipped = {}

    feature_sets = {name: (common_rows.copy(), columns) for name, columns in branch_columns.items()}

    for name, (data, columns) in feature_sets.items():
        try:
            experiments[name] = _fit_test_for_set(name, data, columns, reports_dir, models_dir)
        except ValueError as exc:
            skipped[name] = str(exc)

    if not experiments:
        raise RuntimeError(f"No feature set had enough rows for a train/test experiment: {skipped}")
    if len(experiments) != 2:
        raise RuntimeError(f"Both data branches must complete for a fair comparison: {skipped}")
    splits = [result["boundaries"] for result in experiments.values()]
    if splits[0] != splits[1]:
        raise RuntimeError("Branch Train/Test dates or sample counts do not match")

    classification_rows = [row for result in experiments.values() for row in result["classification_rows"]]
    regression_rows = [row for result in experiments.values() for row in result["regression_rows"]]
    class_metrics = pd.DataFrame(classification_rows)
    regression_metrics = pd.DataFrame(regression_rows)

    # The two branches share one chronological cohort and therefore can be
    # compared model-for-model on an identical test period.
    comparable_sets = [name for name in ("Branch_1_Price_Only", "Branch_2_Macro_Fundamental") if name in experiments]
    class_primary = class_metrics[class_metrics["feature_set"].isin(comparable_sets)]
    reg_primary = regression_metrics[regression_metrics["feature_set"].isin(comparable_sets)]
    best_class_row = class_primary.sort_values(
        ["balanced_accuracy", "f1_up"], ascending=[False, False]
    ).iloc[0]
    best_reg_row = reg_primary.sort_values(["mae", "rmse"], ascending=[True, True]).iloc[0]
    classifier_set = str(best_class_row["feature_set"])
    classifier_name = str(best_class_row["model"])
    regressor_set = str(best_reg_row["feature_set"])
    regressor_name = str(best_reg_row["model"])

    class_metrics["selected_for_deployment"] = (
        class_metrics["feature_set"].eq(classifier_set) & class_metrics["model"].eq(classifier_name)
    )
    regression_metrics["selected_for_deployment"] = (
        regression_metrics["feature_set"].eq(regressor_set) & regression_metrics["model"].eq(regressor_name)
    )
    class_metrics.sort_values(["feature_set", "balanced_accuracy"], ascending=[True, False]).to_csv(
        reports_dir / "classification_test_metrics.csv", index=False
    )
    regression_metrics.sort_values(["feature_set", "mae"], ascending=[True, True]).to_csv(
        reports_dir / "regression_test_metrics.csv", index=False
    )

    classifier_experiment = experiments[classifier_set]
    _refit_selected_model(classifier_experiment, "classification", classifier_name, models_dir)
    regressor_experiment = experiments[regressor_set]
    _refit_selected_model(regressor_experiment, "regression", regressor_name, models_dir)

    c_summary = []
    for name, result in experiments.items():
        best_cls = max(result["classification_rows"], key=lambda row: (row["balanced_accuracy"], row["f1_up"]))
        best_reg = min(result["regression_rows"], key=lambda row: (row["mae"], row["rmse"]))
        c_summary.append(
            {
                "feature_set": name,
                "status": "completed",
                "feature_count": len(result["feature_columns"]),
                "train_start": result["boundaries"]["train_target_date_start"],
                "train_end": result["boundaries"]["train_target_date_end"],
                "test_start": result["boundaries"]["test_target_date_start"],
                "test_end": result["boundaries"]["test_target_date_end"],
                "train_rows": result["boundaries"]["train_rows"],
                "test_rows": result["boundaries"]["test_rows"],
                "classification_test_rows": best_cls["test_rows"],
                "best_classifier": best_cls["model"],
                "balanced_accuracy": best_cls["balanced_accuracy"],
                "accuracy": best_cls["accuracy"],
                "f1_up": best_cls["f1_up"],
                "roc_auc": best_cls["roc_auc"],
                "best_regressor": best_reg["model"],
                "regression_mae": best_reg["mae"],
                "regression_rmse": best_reg["rmse"],
                "regression_mape_percent": best_reg["mape_percent"],
                "tolerance_accuracy_0_5_percent": best_reg["tolerance_accuracy_0_5_percent"],
                "tolerance_accuracy_1_percent": best_reg["tolerance_accuracy_1_percent"],
                "tolerance_accuracy_2_percent": best_reg["tolerance_accuracy_2_percent"],
            }
        )
    pd.DataFrame(c_summary).to_csv(reports_dir / "ablation_summary.csv", index=False)

    confusion_rows = []
    direction_rows = []
    importance_rows = []
    fig, axes = plt.subplots(2, 5, figsize=(16, 6.5))
    for branch_index, (branch_name, result) in enumerate(experiments.items()):
        test_class = result["class_data"].loc[result["class_masks"]["test"]].reset_index(drop=True)
        for model_index, (model_name, (predicted, probability)) in enumerate(result["class_predictions"].items()):
            cm = confusion_matrix(test_class["direction"].astype(int), predicted, labels=[0, 1])
            tn, fp, fn, tp = (int(value) for value in cm.ravel())
            confusion_rows.append({"feature_set": branch_name, "model": model_name, "tn": tn, "fp": fp, "fn": fn, "tp": tp, "test_rows": int(cm.sum())})
            axis = axes[branch_index, model_index]
            axis.imshow(cm, cmap="Blues", vmin=0, vmax=len(test_class))
            axis.set_title(f"Nhánh {branch_index + 1}\n{model_name}", fontsize=10)
            axis.set_xticks([0, 1], labels=["Giảm", "Tăng"])
            axis.set_yticks([0, 1], labels=["Giảm", "Tăng"])
            axis.set_xlabel("Dự đoán")
            axis.set_ylabel("Thực tế")
            for row in range(2):
                for col in range(2):
                    axis.text(col, row, str(cm[row, col]), ha="center", va="center", fontsize=12)
            output = test_class[["date", "target_date", "current_close", "next_close", "direction"]].copy()
            output["feature_set"] = branch_name
            output["model"] = model_name
            output["predicted_direction"] = predicted
            output["probability_up"] = probability
            direction_rows.append(output)
            estimator = result["class_models"][model_name]
            if hasattr(estimator, "feature_importances_"):
                importance_rows.extend({"feature_set": branch_name, "model": model_name, "feature": feature, "importance": float(value)} for feature, value in zip(result["feature_columns"], estimator.feature_importances_))
    fig.suptitle("Ma trận nhầm lẫn của toàn bộ mô hình phân loại trên cùng Test", fontsize=14)
    fig.tight_layout()
    fig.savefig(figures_dir / "05_all_confusion_matrices.png", dpi=220)
    plt.close(fig)
    pd.DataFrame(confusion_rows).to_csv(reports_dir / "confusion_matrices.csv", index=False)
    pd.concat(direction_rows, ignore_index=True).to_csv(reports_dir / "test_direction_predictions_by_model.csv", index=False)
    pd.DataFrame(importance_rows).to_csv(reports_dir / "feature_importance_train.csv", index=False)

    hyperparameters = {
        "random_state": RANDOM_STATE,
        "tuning": "Fixed parameters; no early stopping on Test, no parameter search on Test",
        "classification": {name: model.get_params(deep=True) for name, model in _classifier_models().items()},
        "regression": {name: model.get_params(deep=True) for name, model in _regressor_models().items()},
    }
    (reports_dir / "model_hyperparameters.json").write_text(json.dumps(hyperparameters, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    class_test = classifier_experiment["class_data"].loc[classifier_experiment["class_masks"]["test"]].reset_index(drop=True)
    class_pred, class_prob = classifier_experiment["class_predictions"][classifier_name]
    matrix = confusion_matrix(class_test["direction"].astype(int), class_pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    image = ax.imshow(matrix, cmap="Blues")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks([0, 1], labels=["Dự đoán giảm", "Dự đoán tăng"])
    ax.set_yticks([0, 1], labels=["Thực tế giảm", "Thực tế tăng"])
    ax.set_title(f"Confusion matrix — {classifier_set} / {classifier_name}")
    for row in range(2):
        for column in range(2):
            ax.text(column, row, str(matrix[row, column]), ha="center", va="center", color="black")
    fig.tight_layout()
    fig.savefig(figures_dir / "05_test_confusion_matrix.png", dpi=160)
    plt.close(fig)

    regression_test = regressor_experiment["data"].loc[regressor_experiment["masks"]["test"]].reset_index(drop=True)
    regression_pred = regressor_experiment["regression_predictions"][regressor_name]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(regression_test["target_date"], regression_test["next_close"], label="Giá thực tế phiên kế tiếp", linewidth=1.0, color="#202020")
    ax.plot(regression_test["target_date"], regression_pred, label=f"Dự đoán — {regressor_set} / {regressor_name}", linewidth=1.0, color="#D14A40", alpha=0.85)
    ax.set_title("Giá đóng cửa thực tế và dự đoán trên tập test")
    ax.set_xlabel("Ngày mục tiêu")
    ax.set_ylabel("Close (nghìn VND/cổ phiếu)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "06_actual_vs_predicted_close.png", dpi=160)
    plt.close(fig)

    # One panel per branch lets a reader inspect every requested regression
    # model against exactly the same observed close path.
    plotted_regressors = [
        "Linear Regression",
        "Random Forest Regressor",
        "XGBoost Regressor",
        "HistGradientBoosting Regressor",
    ]
    colors = {"Linear Regression": "#376E9F", "Random Forest Regressor": "#D17A22", "XGBoost Regressor": "#6A9F58", "HistGradientBoosting Regressor": "#A45C8A"}
    fig, axes = plt.subplots(len(experiments), 1, figsize=(13, 5.4 * len(experiments)), sharex=True)
    axes = np.atleast_1d(axes)
    long_price_rows = []
    for axis, (branch_name, result) in zip(axes, experiments.items()):
        branch_test = result["data"].loc[result["masks"]["test"]].reset_index(drop=True)
        axis.plot(branch_test["target_date"], branch_test["next_close"], color="#202020", linewidth=1.45, label="Actual close")
        for model_name in plotted_regressors:
            prediction = result["regression_predictions"][model_name]
            axis.plot(branch_test["target_date"], prediction, color=colors[model_name], linewidth=0.95, alpha=0.9, label=model_name)
            long_price_rows.extend(
                {
                    "feature_set": branch_name,
                    "model": model_name,
                    "date": row.date.strftime("%Y-%m-%d"),
                    "target_date": row.target_date.strftime("%Y-%m-%d"),
                    "actual_close": float(row.next_close),
                    "predicted_close": float(prediction[index]),
                }
                for index, row in branch_test.iterrows()
            )
        axis.set_title(branch_name.replace("_", " "))
        axis.set_ylabel("Close (nghìn VND)")
        axis.grid(alpha=0.25)
        axis.legend(ncol=2, fontsize=8)
    axes[-1].set_xlabel("Ngày mục tiêu")
    fig.suptitle("Giá thực tế và giá dự đoán của từng mô hình trên tập Test", y=0.995)
    fig.tight_layout()
    fig.savefig(figures_dir / "07_regression_lines_by_branch.png", dpi=220)
    plt.close(fig)
    pd.DataFrame(long_price_rows).to_csv(reports_dir / "test_price_predictions_by_model.csv", index=False)

    # XGBoost is the common nonlinear comparator in the two branches. The
    # second panel magnifies the latest 80 sessions without hiding the full path.
    price_branch = experiments["Branch_1_Price_Only"]
    macro_branch = experiments["Branch_2_Macro_Fundamental"]
    comparison_test = price_branch["data"].loc[price_branch["masks"]["test"]].reset_index(drop=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=False)
    for axis, start_index, title in (
        (axes[0], 0, "Toàn bộ tập Test"),
        (axes[1], max(0, len(comparison_test) - 80), "Phóng to 80 phiên cuối của tập Test"),
    ):
        subset = comparison_test.iloc[start_index:]
        axis.plot(subset["target_date"], subset["next_close"], color="#202020", linewidth=1.55, label="Actual close")
        axis.plot(subset["target_date"], price_branch["regression_predictions"]["XGBoost Regressor"][start_index:], color="#376E9F", linewidth=1.05, label="Nhánh 1: XGBoost")
        axis.plot(subset["target_date"], macro_branch["regression_predictions"]["XGBoost Regressor"][start_index:], color="#C45A3D", linewidth=1.05, label="Nhánh 2: XGBoost")
        axis.set_title(title)
        axis.set_ylabel("Close (nghìn VND)")
        axis.grid(alpha=0.25)
        axis.legend()
    axes[-1].set_xlabel("Ngày mục tiêu")
    fig.tight_layout()
    fig.savefig(figures_dir / "08_branch_xgboost_comparison_zoom.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(4, 2, figsize=(15, 14))
    for row_index, model_name in enumerate(plotted_regressors):
        for col_index, start_index in ((0, 0), (1, max(0, len(comparison_test) - 80))):
            axis = axes[row_index, col_index]
            subset = comparison_test.iloc[start_index:]
            axis.plot(subset["target_date"], subset["next_close"], color="#202020", linewidth=1.4, label="Actual close")
            axis.plot(subset["target_date"], price_branch["regression_predictions"][model_name][start_index:], color="#376E9F", linewidth=0.95, label="Nhánh 1")
            axis.plot(subset["target_date"], macro_branch["regression_predictions"][model_name][start_index:], color="#C45A3D", linewidth=0.95, label="Nhánh 2")
            axis.set_title(f"{model_name} / {'Toàn bộ Test' if col_index == 0 else '80 phiên cuối'}", fontsize=11)
            axis.set_ylabel("Close (nghìn VND)")
            axis.grid(alpha=0.25)
            axis.legend(fontsize=8)
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    fig.savefig(figures_dir / "11_all_regressors_branch_comparison_zoom.png", dpi=220)
    plt.close(fig)

    def _metric_bars(frame: pd.DataFrame, model_names: list[str], metrics: list[str], title: str, filename: str) -> None:
        labels = [name.replace(" Regressor", "").replace(" Regression", "") for name in model_names]
        positions = np.arange(len(labels))
        width = 0.36
        fig, axes = plt.subplots(1, len(metrics), figsize=(5.2 * len(metrics), 4.8))
        for axis, metric in zip(np.atleast_1d(axes), metrics):
            for offset, branch_name in ((-width / 2, "Branch_1_Price_Only"), (width / 2, "Branch_2_Macro_Fundamental")):
                values = [
                    float(frame.loc[(frame["feature_set"] == branch_name) & (frame["model"] == model), metric].iloc[0])
                    for model in model_names
                ]
                axis.bar(positions + offset, values, width, label=branch_name.replace("Branch_", "Nhánh ").replace("_", " "))
            axis.set_title(metric.replace("_", " ").title())
            axis.set_xticks(positions, labels, rotation=25, ha="right")
            axis.grid(axis="y", alpha=0.25)
        axes[0].set_ylabel("Tỷ lệ" if metrics[0] in {"accuracy", "balanced_accuracy", "f1_up"} else "Sai số")
        axes[0].legend(fontsize=8)
        fig.suptitle(title, y=1.02)
        fig.tight_layout()
        fig.savefig(figures_dir / filename, dpi=220, bbox_inches="tight")
        plt.close(fig)

    _metric_bars(
        class_metrics,
        ["Majority baseline", "Logistic Regression", "Random Forest", "XGBoost", "HistGradientBoosting"],
        ["accuracy", "balanced_accuracy", "f1_up"],
        "So sánh chỉ số phân loại giữa hai nhánh", "09_classification_metric_bars.png",
    )
    _metric_bars(
        regression_metrics,
        ["Last-Close Baseline", "Linear Regression", "Random Forest Regressor", "XGBoost Regressor", "HistGradientBoosting Regressor"],
        ["mae", "rmse", "mape_percent"],
        "So sánh sai số hồi quy giữa hai nhánh", "10_regression_metric_bars.png",
    )

    price_output = regression_test[["date", "target_date", "current_close", "next_close", "next_return"]].copy()
    price_output["regression_prediction"] = regression_pred
    price_output["regression_model"] = regressor_name
    price_output["feature_set"] = regressor_set
    price_output.to_csv(reports_dir / "test_price_predictions.csv", index=False)

    class_output = class_test[["date", "target_date", "current_close", "next_close", "next_return", "direction"]].copy()
    class_output["actual_direction"] = np.where(class_output["direction"] > 0, "up", "down")
    class_output["predicted_direction"] = np.where(class_pred == 1, "up", "down")
    class_output["probability_up"] = class_prob
    class_output["classifier_model"] = classifier_name
    class_output["feature_set"] = classifier_set
    class_output.to_csv(reports_dir / "test_direction_predictions.csv", index=False)

    splits = {name: result["boundaries"] for name, result in experiments.items()}
    metadata = {
        "split_method": "Shared chronological cohort: first 85% train and final 15% test by target session date.",
        "primary_comparison": "Both branches use the same availability-aligned eligible dates and the same boundary; financial/GDP release dates include stated assumptions.",
        "feature_set_splits": splits,
        "feature_warmup_rows_removed": int(len(price_data) - len(base_table)),
        "raw_price_rows": int(len(price_data)),
        "cutoff_date": RESEARCH_END_DATE,
        "price_only_feature_count": len(PRICE_ONLY_FEATURE_COLUMNS),
        "full_ohlcv_feature_columns": FULL_OHLCV_FEATURE_COLUMNS,
        "supplemental_feature_file": supplemental_path.relative_to(ROOT).as_posix() if supplemental_path.is_relative_to(ROOT) else supplemental_path.name,
        "supplemental_feature_columns": supplemental_columns,
        "classification_label": "up=1, down=0; exactly unchanged next closes excluded from classification.",
        "regression_target": "next_close at target_date; last-close baseline predicts current_close.",
        "tolerance_definition": "Percent of test rows with absolute price error divided by actual close no greater than 0.5%, 1%, or 2%.",
        "scaling": "StandardScaler is inside the Logistic Regression and Linear Regression pipelines; each scaler is fitted only on its Train split for reported Test metrics.",
        "selection": {
            "classifier": "Highest Test Balanced Accuracy among both branch candidates; tie-break by Test F1(up). This Test-based selection is optimistic and is not an independent final estimate.",
            "regressor": "Lowest Test MAE among both branch candidates; tie-break by Test RMSE. This Test-based selection is optimistic and is not an independent final estimate.",
            "deployment_refit": "After metrics are recorded, selected estimators are refit on all labeled rows of the shared cohort through 2025-09-30 for latest-session inference; Test metrics remain from Train-only fits.",
        },
        "selected_models": {
            "classifier": {"model": classifier_name, "feature_set": classifier_set},
            "regressor": {"model": regressor_name, "feature_set": regressor_set},
        },
    }
    (reports_dir / "split_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "classifier_selected": {"model": classifier_name, "feature_set": classifier_set},
        "regressor_selected": {"model": regressor_name, "feature_set": regressor_set},
        "classification_test_metrics": class_metrics.to_dict("records"),
        "regression_test_metrics": regression_metrics.to_dict("records"),
        "ablation_summary": c_summary,
        "split": metadata,
    }
    (reports_dir / "training_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train chronological FPT direction and price experiments.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--supplemental", type=Path, default=DEFAULT_SUPPLEMENTAL)
    parser.add_argument("--figures", type=Path, default=ROOT / "figures")
    parser.add_argument("--reports", type=Path, default=ROOT / "reports")
    parser.add_argument("--models", type=Path, default=ROOT / "models")
    parser.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()
    run_training(args.input, args.figures, args.reports, args.models, args.processed, args.supplemental)


if __name__ == "__main__":
    main()
