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

from features import (
    FEATURE_COLUMNS,
    FULL_OHLCV_FEATURE_COLUMNS,
    REGRESSION_FEATURE_COLUMNS,
    REGRESSION_FULL_OHLCV_FEATURE_COLUMNS,
    build_feature_table,
    load_price_data,
)


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


def _merge_supplemental(table: pd.DataFrame, path: Path) -> tuple[pd.DataFrame, list[str]]:
    if not path.is_file():
        return table, []
    supplement = pd.read_csv(path)
    if "date" not in supplement.columns:
        raise ValueError(f"Supplemental file must include date: {path}")
    supplement["date"] = pd.to_datetime(supplement["date"], errors="coerce").dt.normalize()
    if supplement["date"].isna().any() or supplement["date"].duplicated().any():
        raise ValueError("Supplemental features must have valid, unique session dates")
    excluded = {"time", "date", "open", "high", "low", "close", "volume"}
    feature_columns = [
        column for column in supplement.columns
        if column not in excluded and pd.to_numeric(supplement[column], errors="coerce").notna().any()
    ]
    if not feature_columns:
        return table, []
    supplement = supplement[["date", *feature_columns]].copy()
    for column in feature_columns:
        supplement[column] = pd.to_numeric(supplement[column], errors="coerce")
    merged = table.merge(supplement, on="date", how="left", validate="one_to_one")
    return merged, feature_columns


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

    regression_features = feature_columns + ["current_close"]
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
    base_table = build_feature_table(price_data)
    base_table.to_csv(processed_dir / "fpt_next_session_features.csv", index=False)

    # A and B use exactly the same rows and chronological boundary.
    common_ab = base_table.dropna(subset=FULL_OHLCV_FEATURE_COLUMNS).reset_index(drop=True)
    table_a = common_ab.copy()
    table_b = common_ab.copy()
    table_a, supplemental_columns = _merge_supplemental(table_a, supplemental_path)
    table_b, _ = _merge_supplemental(table_b, supplemental_path)
    table_c = table_b.copy()
    experiments = {}
    skipped = {}

    feature_sets = {
        "A_core_technical": (table_a, list(FEATURE_COLUMNS)),
        "B_full_ohlcv": (table_b, list(FULL_OHLCV_FEATURE_COLUMNS)),
    }
    c_columns = list(FULL_OHLCV_FEATURE_COLUMNS) + supplemental_columns
    if supplemental_columns:
        feature_sets["C_multi_source"] = (table_c, c_columns)
    else:
        skipped["C_multi_source"] = (
            f"No processed supplemental feature columns found at {supplemental_path}; "
            "run python src/fetch_supplemental.py after source access is configured."
        )

    for name, (data, columns) in feature_sets.items():
        try:
            experiments[name] = _fit_test_for_set(name, data, columns, reports_dir, models_dir)
        except ValueError as exc:
            skipped[name] = str(exc)

    if not experiments:
        raise RuntimeError(f"No feature set had enough rows for a train/test experiment: {skipped}")

    classification_rows = [row for result in experiments.values() for row in result["classification_rows"]]
    regression_rows = [row for result in experiments.values() for row in result["regression_rows"]]
    class_metrics = pd.DataFrame(classification_rows)
    regression_metrics = pd.DataFrame(regression_rows)

    # A/B share the same dates and are the primary model-selection comparison.
    comparable_sets = [name for name in ("A_core_technical", "B_full_ohlcv") if name in experiments]
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
    if "C_multi_source" not in experiments:
        c_summary.append(
            {
                "feature_set": "C_multi_source",
                "status": "not_run",
                "skip_reason": skipped.get("C_multi_source", "Insufficient point-in-time data coverage"),
            }
        )
    pd.DataFrame(c_summary).to_csv(reports_dir / "ablation_summary.csv", index=False)

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
        "split_method": "Per feature set: chronological first 85% train and final 15% test by target session date.",
        "primary_comparison": "A and B share the same eligible dates and boundary; C uses its available point-in-time coverage and may have a shorter window.",
        "feature_set_splits": splits,
        "feature_warmup_rows_removed": int(len(price_data) - len(base_table)),
        "raw_price_rows": int(len(price_data)),
        "core_feature_count": len(FEATURE_COLUMNS),
        "full_ohlcv_feature_columns": FULL_OHLCV_FEATURE_COLUMNS,
        "supplemental_feature_file": str(supplemental_path) if supplemental_path.is_file() else None,
        "supplemental_feature_columns": supplemental_columns,
        "supplemental_experiment_skipped_reason": skipped.get("C_multi_source"),
        "classification_label": "up=1, down=0; exactly unchanged next closes excluded from classification.",
        "regression_target": "next_close at target_date; last-close baseline predicts current_close.",
        "tolerance_definition": "Percent of test rows with absolute price error divided by actual close no greater than 0.5%, 1%, or 2%.",
        "scaling": "StandardScaler is inside the Logistic Regression and Linear Regression pipelines; each scaler is fitted only on its Train split for reported Test metrics.",
        "selection": {
            "classifier": "Highest Test Balanced Accuracy among A/B candidates; tie-break by Test F1(up). This Test-based selection is optimistic and is not an independent final estimate.",
            "regressor": "Lowest Test MAE among A/B candidates; tie-break by Test RMSE. This Test-based selection is optimistic and is not an independent final estimate.",
            "deployment_refit": "After metrics are recorded, selected A/B estimators are refit on all available labeled data through 2026-09-30 for latest-session inference; Test metrics remain from Train-only fits.",
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
