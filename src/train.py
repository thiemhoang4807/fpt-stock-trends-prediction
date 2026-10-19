"""Train chronological next-session direction and close-price experiments."""

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

from features import FEATURE_COLUMNS, REGRESSION_FEATURE_COLUMNS, build_feature_table, load_price_data


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
RANDOM_STATE = 42


def _chronological_splits(table: pd.DataFrame) -> tuple[dict[str, pd.Series], dict[str, str]]:
    labeled = table.loc[table["target_date"].notna()].sort_values("target_date").reset_index(drop=True)
    if len(labeled) < 100:
        raise ValueError(f"At least 100 labeled rows are required; found {len(labeled)}")
    train_end_index = max(1, int(len(labeled) * 0.70) - 1)
    validation_end_index = max(train_end_index + 1, int(len(labeled) * 0.85) - 1)
    train_end = labeled.loc[train_end_index, "target_date"]
    validation_start = labeled.loc[train_end_index + 1, "target_date"]
    validation_end = labeled.loc[validation_end_index, "target_date"]
    test_start = labeled.loc[validation_end_index + 1, "target_date"]
    target_dates = table["target_date"]
    masks = {
        "train": target_dates.le(train_end),
        "validation": target_dates.gt(train_end) & target_dates.le(validation_end),
        "test": target_dates.gt(validation_end),
    }
    boundaries = {
        "train_target_date_end": train_end.strftime("%Y-%m-%d"),
        "validation_target_date_start": validation_start.strftime("%Y-%m-%d"),
        "validation_target_date_end": validation_end.strftime("%Y-%m-%d"),
        "test_target_date_start": test_start.strftime("%Y-%m-%d"),
        "split_method": "chronological by target session date; train 70%, validation 15%, test 15%",
    }
    if not masks["train"].any() or not masks["validation"].any() or not masks["test"].any():
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
        "Random Forest": RandomForestRegressor(
            n_estimators=350,
            max_depth=8,
            min_samples_leaf=20,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "HistGradientBoosting": HistGradientBoostingRegressor(
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
    result["roc_auc"] = float(roc_auc_score(y_true, y_probability)) if len(np.unique(y_true)) == 2 else float("nan")
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
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape_percent": float(mean_absolute_percentage_error(y_true, y_pred) * 100.0),
        "directional_accuracy_nonflat_percent": directional_accuracy * 100.0,
    }


def _evaluate_classifiers(class_table, masks, reports_dir, figures_dir, models_dir):
    X = class_table[FEATURE_COLUMNS]
    y = class_table["direction"].astype(int)
    train_mask = masks["train"] & class_table["target_date"].notna()
    validation_mask = masks["validation"] & class_table["target_date"].notna()
    test_mask = masks["test"] & class_table["target_date"].notna()
    train_rows = train_mask.to_numpy()
    validation_rows = validation_mask.to_numpy()
    test_rows = test_mask.to_numpy()
    if min(int(train_rows.sum()), int(validation_rows.sum()), int(test_rows.sum())) < 20:
        raise ValueError("Classification train, validation, and test partitions must each have at least 20 rows")

    selection = []
    final_models = {}
    validation_predictions = {}
    for name, model in _classifier_models().items():
        model.fit(X.loc[train_mask], y.loc[train_mask])
        validation_pred = model.predict(X.loc[validation_mask]).astype(int)
        validation_prob = model.predict_proba(X.loc[validation_mask])[:, 1]
        metrics = _classification_metrics(y.loc[validation_mask], validation_pred, validation_prob)
        selection.append({"model": name, **{f"validation_{key}": value for key, value in metrics.items()}})
        validation_predictions[name] = (validation_pred, validation_prob)

        # Refit on train + validation only after model selection metrics are recorded.
        train_validation_mask = train_mask | validation_mask
        model.fit(X.loc[train_validation_mask], y.loc[train_validation_mask])
        final_models[name] = model

    selected_name = max(
        selection,
        key=lambda row: (row["validation_balanced_accuracy"], row["validation_f1_up"]),
    )["model"]
    test_rows_out = []
    best_predictions = None
    for name, model in final_models.items():
        prediction = model.predict(X.loc[test_mask]).astype(int)
        probability = model.predict_proba(X.loc[test_mask])[:, 1]
        metrics = _classification_metrics(y.loc[test_mask], prediction, probability)
        test_rows_out.append({"model": name, **metrics, "selected_by_validation": name == selected_name})
        if name == selected_name:
            best_predictions = (prediction, probability)

    pd.DataFrame(selection).to_csv(reports_dir / "classification_validation_metrics.csv", index=False)
    pd.DataFrame(test_rows_out).sort_values("balanced_accuracy", ascending=False).to_csv(
        reports_dir / "classification_test_metrics.csv", index=False
    )
    best_model = final_models[selected_name]
    joblib.dump(
        {"model": best_model, "model_name": selected_name, "feature_columns": FEATURE_COLUMNS, "positive_class": "up"},
        models_dir / "best_classifier.joblib",
    )

    test_table = class_table.loc[test_mask].reset_index(drop=True)
    pred, probability = best_predictions
    matrix = confusion_matrix(y.loc[test_mask], pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    image = ax.imshow(matrix, cmap="Blues")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks([0, 1], labels=["Dự đoán giảm", "Dự đoán tăng"])
    ax.set_yticks([0, 1], labels=["Thực tế giảm", "Thực tế tăng"])
    ax.set_title(f"Confusion matrix — {selected_name}")
    for row in range(2):
        for column in range(2):
            ax.text(column, row, str(matrix[row, column]), ha="center", va="center", color="black")
    fig.tight_layout()
    fig.savefig(figures_dir / "05_test_confusion_matrix.png", dpi=160)
    plt.close(fig)

    return selected_name, test_table, pred, probability, test_rows_out


def _evaluate_regressors(table, masks, reports_dir, figures_dir, models_dir):
    X = table[REGRESSION_FEATURE_COLUMNS]
    train_mask = masks["train"] & table["next_close"].notna()
    validation_mask = masks["validation"] & table["next_close"].notna()
    test_mask = masks["test"] & table["next_close"].notna()
    if min(int(train_mask.sum()), int(validation_mask.sum()), int(test_mask.sum())) < 20:
        raise ValueError("Regression train, validation, and test partitions must each have at least 20 rows")

    y = table["next_close"]
    validation_records = []
    test_predictions = {}
    validation_predictions = {}
    final_models = {}

    validation_persistence = table.loc[validation_mask, "current_close"].to_numpy()
    validation_metrics = _regression_metrics(y.loc[validation_mask], validation_persistence, table.loc[validation_mask, "current_close"])
    validation_records.append({"model": "Last close baseline", **{f"validation_{k}": v for k, v in validation_metrics.items()}})
    validation_predictions["Last close baseline"] = validation_persistence
    test_predictions["Last close baseline"] = table.loc[test_mask, "current_close"].to_numpy()

    for name, model in _regressor_models().items():
        model.fit(X.loc[train_mask], y.loc[train_mask])
        validation_pred = model.predict(X.loc[validation_mask])
        metrics = _regression_metrics(y.loc[validation_mask], validation_pred, table.loc[validation_mask, "current_close"])
        validation_records.append({"model": name, **{f"validation_{k}": v for k, v in metrics.items()}})
        validation_predictions[name] = validation_pred

        train_validation_mask = train_mask | validation_mask
        model.fit(X.loc[train_validation_mask], y.loc[train_validation_mask])
        final_models[name] = model
        test_predictions[name] = model.predict(X.loc[test_mask])

    selected_name = min(validation_records, key=lambda row: row["validation_mae"])["model"]
    test_rows_out = []
    for name, prediction in test_predictions.items():
        metrics = _regression_metrics(y.loc[test_mask], prediction, table.loc[test_mask, "current_close"])
        test_rows_out.append({"model": name, **metrics, "selected_by_validation": name == selected_name})

    pd.DataFrame(validation_records).to_csv(reports_dir / "regression_validation_metrics.csv", index=False)
    pd.DataFrame(test_rows_out).sort_values("mae").to_csv(reports_dir / "regression_test_metrics.csv", index=False)
    if selected_name == "Last close baseline":
        joblib.dump(
            {"strategy": "last_close", "model_name": selected_name, "feature_columns": REGRESSION_FEATURE_COLUMNS},
            models_dir / "best_regressor.joblib",
        )
    else:
        joblib.dump(
            {"strategy": "estimator", "model": final_models[selected_name], "model_name": selected_name, "feature_columns": REGRESSION_FEATURE_COLUMNS},
            models_dir / "best_regressor.joblib",
        )

    test_table = table.loc[test_mask].reset_index(drop=True)
    best_prediction = test_predictions[selected_name]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(test_table["target_date"], test_table["next_close"], label="Giá thực tế phiên kế tiếp", linewidth=1.0, color="#202020")
    ax.plot(test_table["target_date"], best_prediction, label=f"Dự đoán — {selected_name}", linewidth=1.0, color="#D14A40", alpha=0.85)
    ax.set_title("Giá đóng cửa thực tế và dự đoán trên tập test")
    ax.set_xlabel("Ngày mục tiêu")
    ax.set_ylabel("Close (đơn vị theo dữ liệu nguồn)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "06_actual_vs_predicted_close.png", dpi=160)
    plt.close(fig)

    return selected_name, test_table, best_prediction, test_predictions, test_rows_out


def run_training(input_path: Path, figures_dir: Path, reports_dir: Path, models_dir: Path, processed_dir: Path) -> dict:
    for directory in (figures_dir, reports_dir, models_dir, processed_dir):
        directory.mkdir(parents=True, exist_ok=True)
    price_data = load_price_data(input_path)
    table = build_feature_table(price_data)
    table.to_csv(processed_dir / "fpt_next_session_features.csv", index=False)
    masks, boundaries = _chronological_splits(table)

    class_table = table.loc[table["direction"].notna()].reset_index(drop=True)
    # Keep identical cut dates for both tasks, with split membership based on outcome date.
    train_end = pd.Timestamp(boundaries["train_target_date_end"])
    validation_end = pd.Timestamp(boundaries["validation_target_date_end"])
    class_masks = {
        "train": class_table["target_date"].le(train_end),
        "validation": class_table["target_date"].gt(train_end) & class_table["target_date"].le(validation_end),
        "test": class_table["target_date"].gt(validation_end),
    }

    classifier_name, classifier_test, classifier_pred, classifier_prob, _ = _evaluate_classifiers(
        class_table, class_masks, reports_dir, figures_dir, models_dir
    )
    regressor_name, regression_test, regression_pred, all_reg_predictions, _ = _evaluate_regressors(
        table, masks, reports_dir, figures_dir, models_dir
    )

    prediction_output = regression_test[["date", "target_date", "current_close", "next_close", "next_return"]].copy()
    prediction_output["regression_prediction"] = regression_pred
    prediction_output["regression_model"] = regressor_name
    prediction_output.to_csv(reports_dir / "test_price_predictions.csv", index=False)

    class_output = classifier_test[["date", "target_date", "current_close", "next_close", "next_return"]].copy()
    class_output["actual_direction"] = np.where(class_output["next_return"] > 0, "up", "down")
    class_output["predicted_direction"] = np.where(classifier_pred == 1, "up", "down")
    class_output["probability_up"] = classifier_prob
    class_output.to_csv(reports_dir / "test_direction_predictions.csv", index=False)

    split_metadata = {
        **boundaries,
        "feature_warmup_rows_removed": int(len(price_data) - len(table)),
        "final_feature_rows_without_next_session_target": int(table["target_date"].isna().sum()),
        "regression_rows": {
            "train": int(masks["train"].sum()),
            "validation": int(masks["validation"].sum()),
            "test": int(masks["test"].sum()),
        },
        "classification_rows_excluding_unchanged": {
            "train": int(class_masks["train"].sum()),
            "validation": int(class_masks["validation"].sum()),
            "test": int(class_masks["test"].sum()),
        },
        "feature_count": len(FEATURE_COLUMNS),
        "feature_names": FEATURE_COLUMNS,
        "regression_feature_count": len(REGRESSION_FEATURE_COLUMNS),
        "regression_feature_names": REGRESSION_FEATURE_COLUMNS,
        "prediction_definition": "At close of session t, predict close(t+1) and its direction relative to close(t).",
        "classification_label": "up=1, down=0; exactly unchanged next closes are excluded from classification.",
        "regression_directional_accuracy": "Computed only for non-zero actual next-session returns.",
        "scaling": "StandardScaler is inside Logistic/Linear Regression pipelines; fit occurs only on training data, then on train+validation for final test evaluation.",
        "model_selection": {
            "classifier": "highest validation balanced accuracy; tie-break by validation F1 for up class",
            "regressor": "lowest validation MAE, including last-close persistence baseline",
        },
        "selected_models": {"classifier": classifier_name, "regressor": regressor_name},
    }
    (reports_dir / "split_metadata.json").write_text(json.dumps(split_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "classifier_selected": classifier_name,
        "regressor_selected": regressor_name,
        "classification_test_metrics": pd.read_csv(reports_dir / "classification_test_metrics.csv").to_dict("records"),
        "regression_test_metrics": pd.read_csv(reports_dir / "regression_test_metrics.csv").to_dict("records"),
        "split": split_metadata,
    }
    (reports_dir / "training_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train FPT next-session ML models with chronological splits.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--figures", type=Path, default=ROOT / "figures")
    parser.add_argument("--reports", type=Path, default=ROOT / "reports")
    parser.add_argument("--models", type=Path, default=ROOT / "models")
    parser.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()
    run_training(args.input, args.figures, args.reports, args.models, args.processed)


if __name__ == "__main__":
    main()
