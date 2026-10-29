"""Five-fold past-only model selection and frozen final holdout evaluation."""

import json, re
from pathlib import Path
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.svm import SVC, SVR
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    mean_squared_error,
    mean_absolute_error,
    mean_absolute_percentage_error,
)
from xgboost import XGBClassifier, XGBRegressor
from features import RESEARCH_END_DATE
from prepare import (
    build_experiment_table,
    feature_groups,
    DEFAULT_INPUT,
    DEFAULT_SUPPLEMENTAL,
)
from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS
from sequence_models import fit_predict_sequence, fit_predict_statistical

ROOT = Path(__file__).resolve().parents[1]
RANDOM_STATE = 42


def _chronological_splits(
    table: pd.DataFrame,
) -> tuple[dict[str, pd.Series], dict[str, str]]:
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
        "train_target_date_start": pd.Timestamp(
            labeled.iloc[0]["target_date"]
        ).strftime("%Y-%m-%d"),
        "train_target_date_end": train_end.strftime("%Y-%m-%d"),
        "test_target_date_start": test_start.strftime("%Y-%m-%d"),
        "test_target_date_end": pd.Timestamp(labeled.iloc[-1]["target_date"]).strftime(
            "%Y-%m-%d"
        ),
        "split_method": "chronological by target session date; first 85% train, last 15% test",
        "labeled_rows": int(len(labeled)),
        "train_rows": int(train_count),
        "test_rows": int(len(labeled) - train_count),
    }
    if not masks["train"].any() or not masks["test"].any():
        raise RuntimeError("Chronological split produced an empty partition")
    return masks, boundaries


def _classification_metrics(y_true, y_pred, y_probability) -> dict[str, float]:
    result = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision_up": float(
            precision_score(y_true, y_pred, pos_label=1, zero_division=0)
        ),
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
    relative_error = np.abs(y_pred - y_true) / np.maximum(
        np.abs(y_true), np.finfo(float).eps
    )
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape_percent": float(mean_absolute_percentage_error(y_true, y_pred) * 100.0),
        "directional_accuracy_nonflat_percent": directional_accuracy * 100.0,
        "tolerance_accuracy_0_5_percent": float(
            np.mean(relative_error <= 0.005) * 100.0
        ),
        "tolerance_accuracy_1_percent": float(np.mean(relative_error <= 0.01) * 100.0),
        "tolerance_accuracy_2_percent": float(np.mean(relative_error <= 0.02) * 100.0),
    }


def candidate_models(task):
    if task == "classification":
        return {
            "Majority baseline": [DummyClassifier(strategy="most_frequent")],
            "Logistic Regression": [
                make_pipeline(
                    StandardScaler(),
                    LogisticRegression(
                        C=c, class_weight="balanced", max_iter=3000, random_state=42
                    ),
                )
                for c in (0.1, 1.0)
            ],
            "SVC": [
                make_pipeline(StandardScaler(), SVC(C=c, class_weight="balanced"))
                for c in (0.1, 1.0)
            ],
            "Random Forest": [
                RandomForestClassifier(
                    n_estimators=120,
                    max_depth=d,
                    min_samples_leaf=15,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=1,
                )
                for d in (3, 6)
            ],
            "XGBoost": [
                XGBClassifier(
                    n_estimators=120,
                    max_depth=d,
                    learning_rate=0.04,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    min_child_weight=8,
                    reg_lambda=3,
                    random_state=42,
                    n_jobs=1,
                )
                for d in (2, 3)
            ],
            "HistGradientBoosting": [
                HistGradientBoostingClassifier(
                    max_iter=120,
                    max_leaf_nodes=l,
                    learning_rate=0.04,
                    l2_regularization=2,
                    early_stopping=False,
                    random_state=42,
                )
                for l in (7, 15)
            ],
        }
    return {
        "Last-Close Baseline": [DummyRegressor(strategy="constant", constant=0)],
        "Linear Regression": [make_pipeline(StandardScaler(), LinearRegression())],
        "Ridge Regression": [
            make_pipeline(StandardScaler(), Ridge(alpha=a)) for a in (10.0, 100.0)
        ],
        "SVR": [
            make_pipeline(StandardScaler(), SVR(C=c, epsilon=0.002))
            for c in (0.01, 0.1)
        ],
        "Random Forest Regressor": [
            RandomForestRegressor(
                n_estimators=120,
                max_depth=d,
                min_samples_leaf=15,
                random_state=42,
                n_jobs=1,
            )
            for d in (3, 6)
        ],
        "XGBoost Regressor": [
            XGBRegressor(
                n_estimators=120,
                max_depth=d,
                learning_rate=0.04,
                subsample=0.85,
                colsample_bytree=0.85,
                min_child_weight=8,
                reg_lambda=3,
                random_state=42,
                n_jobs=1,
            )
            for d in (2, 3)
        ],
        "HistGradientBoosting Regressor": [
            HistGradientBoostingRegressor(
                max_iter=120,
                max_leaf_nodes=l,
                learning_rate=0.04,
                l2_regularization=2,
                early_stopping=False,
                random_state=42,
            )
            for l in (7, 15)
        ],
    }


def _classifier_models():
    return {k: v[0] for k, v in candidate_models("classification").items()}


def _regressor_models():
    return {k: v[0] for k, v in candidate_models("regression").items()}


def cv_splits(n):
    return list(TimeSeriesSplit(n_splits=5, gap=1).split(np.arange(n)))


def evaluate(task, frame, prediction, score=None):
    if task == "classification":
        valid = frame.direction.notna().to_numpy()
        return _classification_metrics(
            frame.direction.to_numpy()[valid].astype(int),
            np.asarray(prediction)[valid].astype(int),
            np.asarray(score)[valid],
        )
    prediction = np.asarray(prediction)
    metrics = _regression_metrics(
        frame.next_close,
        frame.current_close.to_numpy() * np.exp(prediction),
        frame.current_close,
    )
    metrics.update(
        log_return_mae=float(mean_absolute_error(frame.next_log_return, prediction)),
        log_return_rmse=float(
            np.sqrt(mean_squared_error(frame.next_log_return, prediction))
        ),
    )
    return metrics


def fit_candidate(spec, task, data, cols, a, b):
    family, candidate = spec
    if family == "sequence":
        score, artifact = fit_predict_sequence(
            candidate["kind"],
            task,
            data,
            cols,
            a,
            b,
            lookback=candidate["lookback"],
            epochs=12,
            hidden_size=16,
        )
        return (
            (score >= 0.5).astype(int) if task == "classification" else score,
            score,
            artifact,
        )
    if family == "statistical":
        score, artifact = fit_predict_statistical(
            candidate["kind"],
            data,
            MODEL_SUPPLEMENTAL_COLUMNS if candidate["kind"] == "SARIMAX" else [],
            a,
            b,
            order=candidate["order"],
        )
        return (
            (score > 0).astype(int) if task == "classification" else score,
            score,
            artifact,
        )
    train = data.iloc[a]
    if task == "classification":
        train = train.dropna(subset=["direction"])
    estimator = clone(candidate)
    estimator.fit(
        train[cols],
        (
            train.direction.astype(int)
            if task == "classification"
            else train.next_log_return
        ),
    )
    prediction = estimator.predict(data.iloc[b][cols]) if len(b) else np.array([])
    score = prediction
    if task == "classification" and len(b):
        score = (
            estimator.predict_proba(data.iloc[b][cols])[:, 1]
            if hasattr(estimator, "predict_proba")
            else estimator.decision_function(data.iloc[b][cols])
        )
    return (
        prediction,
        score,
        {
            "model_kind": "tabular",
            "model": estimator,
            "task": task,
            "feature_columns": cols,
        },
    )


def run_training(
    input_path=DEFAULT_INPUT,
    figures_dir=ROOT / "figures",
    reports_dir=ROOT / "reports",
    models_dir=ROOT / "models",
    processed_dir=ROOT / "data/processed",
    supplemental_path=DEFAULT_SUPPLEMENTAL,
):
    for p in (figures_dir, reports_dir, models_dir / "evaluation", processed_dir):
        p.mkdir(parents=True, exist_ok=True)
    base, common, branches = build_experiment_table(input_path, supplemental_path)
    context = common.attrs["sequence_context"]
    common.attrs = {}
    base.to_csv(processed_dir / "fpt_next_session_features.csv", index=False)
    common.to_csv(processed_dir / "fpt_two_branch_features.csv", index=False)
    data = common.loc[common.target_date.notna()].reset_index(drop=True)
    data.attrs["sequence_context"] = context
    cut = int(len(data) * 0.85)
    train_idx = np.arange(cut)
    test_idx = np.arange(cut, len(data))
    folds = cv_splits(cut)
    bounds = {
        "train_rows": cut,
        "test_rows": len(test_idx),
        "train_target_date_start": str(data.iloc[0].target_date.date()),
        "train_target_date_end": str(data.iloc[cut - 1].target_date.date()),
        "test_target_date_start": str(data.iloc[cut].target_date.date()),
        "test_target_date_end": str(data.iloc[-1].target_date.date()),
    }
    cv_rows = []
    selected_specs = []
    metric_rows = []
    predictions = []
    manifest = []
    diagnostics = []
    for branch, cols in branches.items():
        for task in ("classification", "regression"):
            families = {
                name: [("tabular", m) for m in models]
                for name, models in candidate_models(task).items()
            }
            for kind in ("LSTM", "GRU"):
                for L in (10, 20, 30, 60):
                    families[f"{kind} L={L}"] = [
                        ("sequence", {"kind": kind, "lookback": L})
                    ]
            stat = "ARIMA" if "Price_Only" in branch else "SARIMAX"
            families[stat] = [
                ("statistical", {"kind": stat, "order": o})
                for o in [(0, 0, 0), (1, 0, 0)]
            ]
            for name, specs in families.items():
                print("CV", branch, task, name, flush=True)
                means = []
                for candidate_id, spec in enumerate(specs):
                    scores = []
                    for fold, (a, b) in enumerate(folds, 1):
                        pred, score, artifact = fit_candidate(
                            spec, task, data, cols, a, b
                        )
                        m = evaluate(task, data.iloc[b], pred, score)
                        cv_rows.append(
                            dict(
                                feature_set=branch,
                                task=task,
                                model=name,
                                candidate_id=candidate_id,
                                fold=fold,
                                **m,
                            )
                        )
                        scores.append(
                            m[
                                (
                                    "balanced_accuracy"
                                    if task == "classification"
                                    else "log_return_rmse"
                                )
                            ]
                        )
                        if artifact["model_kind"] == "statistical":
                            diagnostics.append(
                                dict(
                                    feature_set=branch,
                                    task=task,
                                    model=name,
                                    fold=fold,
                                    candidate_id=candidate_id,
                                    converged=artifact["converged"],
                                    warnings=artifact["warnings"],
                                )
                            )
                    means.append(float(np.mean(scores)))
                best = int(
                    np.argmax(means) if task == "classification" else np.argmin(means)
                )
                spec = specs[best]
                pred, score, artifact = fit_candidate(
                    spec, task, data, cols, train_idx, test_idx
                )
                artifact.update(
                    model_name=name,
                    feature_set=branch,
                    fit_scope="Train only",
                    trained_through_target_date=bounds["train_target_date_end"],
                )
                m = evaluate(task, data.iloc[test_idx], pred, score)
                metric_rows.append(
                    dict(
                        feature_set=branch,
                        task=task,
                        model=name,
                        test_rows=(
                            int(data.iloc[test_idx].direction.notna().sum())
                            if task == "classification"
                            else len(test_idx)
                        ),
                        test_start=bounds["test_target_date_start"],
                        test_end=bounds["test_target_date_end"],
                        cv_score=means[best],
                        **m,
                    )
                )
                identity = (branch, task, name)
                selected_specs.append((identity, spec, means[best], best))
                path = (
                    models_dir
                    / "evaluation"
                    / (
                        re.sub("[^a-zA-Z0-9]+", "_", f"{branch}_{task}_{name}")
                        + ".joblib"
                    )
                )
                joblib.dump(artifact, path)
                manifest.append(
                    dict(
                        feature_set=branch,
                        task=task,
                        model=name,
                        cv_score=means[best],
                        path=(
                            path.relative_to(ROOT).as_posix()
                            if path.is_relative_to(ROOT)
                            else str(path)
                        ),
                        feature_columns=cols,
                        candidate_id=best,
                        configuration=str(spec[1]),
                    )
                )
                for j, index in enumerate(test_idx):
                    row = data.iloc[index]
                    if task == "classification" and pd.isna(row.direction):
                        continue
                    predictions.append(
                        dict(
                            feature_set=branch,
                            task=task,
                            model=name,
                            date=str(row.date.date()),
                            target_date=str(row.target_date.date()),
                            current_close=row.current_close,
                            actual_close=row.next_close,
                            actual_log_return=row.next_log_return,
                            direction=row.direction,
                            prediction=float(pred[j]),
                            score=float(score[j]),
                            predicted_close=(
                                float(row.current_close * np.exp(pred[j]))
                                if task == "regression"
                                else np.nan
                            ),
                        )
                    )
    cv = pd.DataFrame(cv_rows)
    cv.to_csv(reports_dir / "cv_fold_metrics.csv", index=False)
    metrics = pd.DataFrame(metric_rows)
    summaries = []
    for identity, spec, value, candidate_id in selected_specs:
        branch, task, name = identity
        part = cv[
            (cv.feature_set == branch)
            & (cv.task == task)
            & (cv.model == name)
            & (cv.candidate_id == candidate_id)
        ]
        r = dict(
            feature_set=branch,
            task=task,
            model=name,
            candidate_id=candidate_id,
            configuration=str(spec[1]),
        )
        for c in part.select_dtypes(include="number").columns.difference(
            ["candidate_id", "fold"]
        ):
            if part[c].notna().any():
                r[c + "_mean"] = float(part[c].mean())
                r[c + "_std"] = float(part[c].std(ddof=1))
        summaries.append(r)
    pd.DataFrame(summaries).to_csv(reports_dir / "cv_summary.csv", index=False)
    selected = {}
    for task in ("classification", "regression"):
        choices = [s for s in selected_specs if s[0][1] == task]
        identity, spec, score, candidate_id = sorted(
            choices, key=lambda s: s[2], reverse=task == "classification"
        )[0]
        branch, _, name = identity
        selected[task] = dict(model=name, feature_set=branch, cv_score=score)
        _, _, artifact = fit_candidate(
            spec,
            task,
            data,
            branches[branch],
            np.arange(len(data)),
            np.array([], dtype=int),
        )
        artifact.update(
            model_name=name,
            feature_set=branch,
            fit_scope="All labeled rows after frozen evaluation",
            trained_through_target_date=bounds["test_target_date_end"],
        )
        joblib.dump(
            artifact,
            models_dir
            / (
                "best_classifier.joblib"
                if task == "classification"
                else "best_regressor.joblib"
            ),
        )
        out = (
            metrics[metrics.task == task]
            .drop(columns="task")
            .dropna(axis=1, how="all")
            .copy()
        )
        out["selected_for_deployment"] = out.model.eq(name) & out.feature_set.eq(branch)
        out.to_csv(reports_dir / f"{task}_test_metrics.csv", index=False)
    predicted = pd.DataFrame(predictions)
    for task, label in [("classification", "direction"), ("regression", "price")]:
        predicted[predicted.task == task].to_csv(
            reports_dir / f"test_{label}_predictions_by_model.csv", index=False
        )
    matrices = []
    for (branch, name), g in predicted[predicted.task == "classification"].groupby(
        ["feature_set", "model"]
    ):
        tn, fp, fn, tp = confusion_matrix(
            g.direction, g.prediction, labels=[0, 1]
        ).ravel()
        matrices.append(
            dict(
                feature_set=branch,
                model=name,
                tn=int(tn),
                fp=int(fp),
                fn=int(fn),
                tp=int(tp),
            )
        )
    pd.DataFrame(matrices).to_csv(reports_dir / "confusion_matrices.csv", index=False)
    (reports_dir / "evaluation_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (reports_dir / "model_hyperparameters.json").write_text(
        json.dumps(
            {"selection": "five-fold Train CV only", "models": manifest}, indent=2
        ),
        encoding="utf-8",
    )
    for task, label in [("classification", "direction"), ("regression", "price")]:
        choice = selected[task]
        chosen = predicted[
            (predicted.task == task)
            & (predicted.model == choice["model"])
            & (predicted.feature_set == choice["feature_set"])
        ]
        chosen.to_csv(reports_dir / f"test_{label}_predictions.csv", index=False)
    ablation = []
    for group, cols in feature_groups().items():
        if group == "G5" and cols == feature_groups()["G4"]:
            ablation.append(
                dict(
                    group=group,
                    status="excluded: no reliable ICT history",
                    feature_count=len(cols),
                )
            )
            continue
        for task in ("classification", "regression"):
            print("ABLATION", group, task, flush=True)
            name = "XGBoost" if task == "classification" else "XGBoost Regressor"
            scores = []
            for candidate in candidate_models(task)[name]:
                values = []
                for a, b in folds:
                    pred, score, _ = fit_candidate(
                        ("tabular", candidate), task, data, cols, a, b
                    )
                    values.append(
                        evaluate(task, data.iloc[b], pred, score)[
                            (
                                "balanced_accuracy"
                                if task == "classification"
                                else "log_return_rmse"
                            )
                        ]
                    )
                scores.append(
                    (float(np.mean(values)), float(np.std(values, ddof=1)), candidate)
                )
            mean, std, candidate = sorted(
                scores, key=lambda s: s[0], reverse=task == "classification"
            )[0]
            pred, score, _ = fit_candidate(
                ("tabular", candidate), task, data, cols, train_idx, test_idx
            )
            ablation.append(
                dict(
                    group=group,
                    task=task,
                    status="evaluated",
                    feature_count=len(cols),
                    cv_mean=mean,
                    cv_std=std,
                    **evaluate(task, data.iloc[test_idx], pred, score),
                )
            )
    abl = pd.DataFrame(ablation)
    abl.to_csv(reports_dir / "ablation_summary.csv", index=False)
    metrics[metrics.model.str.contains("LSTM|GRU")].to_csv(
        reports_dir / "lookback_comparison.csv", index=False
    )
    fold_metadata = [
        dict(
            fold=i + 1,
            train_rows=len(a),
            validation_rows=len(b),
            train_target_end=str(data.iloc[a[-1]].target_date.date()),
            validation_input_start=str(data.iloc[b[0]].date.date()),
            validation_target_end=str(data.iloc[b[-1]].target_date.date()),
        )
        for i, (a, b) in enumerate(folds)
    ]
    metadata = dict(
        split_method="85/15 chronological; five TimeSeriesSplit folds on Train with gap=1",
        cutoff_date=RESEARCH_END_DATE,
        feature_set_splits={b: bounds for b in branches},
        cv_folds=fold_metadata,
        feature_columns=branches,
        selected_models=selected,
        historical_test_caveat="Test dates were examined in previous versions; excluded from selection in this run but not a never-before-seen external holdout.",
        regression_target="next_log_return; price=current_close*exp(prediction)",
        log_return_mape="Not defined: zeros/near-zero/negative returns make percentage errors inappropriate; MAE/RMSE on returns, MAPE/tolerance on positive reconstructed prices.",
        sequence_policy="Same eligible dates for all L; windows use true consecutive context sessions.",
        statistical_diagnostics=diagnostics,
    )
    (reports_dir / "split_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    summary = dict(
        classifier_selected=selected["classification"],
        regressor_selected=selected["regression"],
        split=metadata,
    )
    (reports_dir / "training_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    draw_results(predicted, metrics, abl, figures_dir)
    print(json.dumps(selected, indent=2), flush=True)
    return summary


def draw_results(predictions, metrics, ablation, figures_dir):
    for branch in predictions.feature_set.unique():
        frame = predictions[
            (predictions.feature_set == branch) & (predictions.task == "regression")
        ]
        names = [
            "Last-Close Baseline",
            "Ridge Regression",
            "XGBoost Regressor",
            "ARIMA" if "Price" in branch else "SARIMAX",
            "LSTM L=20",
            "GRU L=20",
        ]
        fig, axes = plt.subplots(2, 1, figsize=(14, 9))
        for ax, zoom in zip(axes, [False, True]):
            for name in names:
                s = frame[frame.model == name].sort_values("target_date")
                if zoom:
                    s = s.tail(80)
                if name == names[0]:
                    ax.plot(
                        pd.to_datetime(s.target_date),
                        s.actual_close,
                        color="black",
                        label="Actual Close",
                        lw=1.5,
                    )
                ax.plot(
                    pd.to_datetime(s.target_date),
                    s.predicted_close,
                    label=name,
                    lw=0.8,
                    alpha=0.8,
                )
            ax.set_title(branch + (" / final80 sessions" if zoom else " / full Test"))
            ax.set_ylabel("Thousand VND")
            ax.legend(ncol=3, fontsize=8)
            ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(figures_dir / f"14_forecasts_{branch}.png", dpi=180)
        plt.close(fig)
    for task, key in [("classification", "balanced_accuracy"), ("regression", "rmse")]:
        frame = metrics[metrics.task == task]
        keys = (
            ["accuracy", "balanced_accuracy", "f1_up"]
            if task == "classification"
            else ["mae", "rmse", "mape_percent"]
        )
        fig, axes = plt.subplots(3, 1, figsize=(15, 15))
        for ax, metric in zip(axes, keys):
            frame.pivot(index="model", columns="feature_set", values=metric).plot.bar(
                ax=ax
            )
            ax.set_title(f"Test {metric} (selection on Train CV)")
            ax.tick_params(axis="x", rotation=40)
            ax.set_xlabel("")
        fig.tight_layout()
        fig.savefig(figures_dir / f"15_metrics_{task}.png", dpi=180)
        plt.close(fig)
        sub = ablation[(ablation.status == "evaluated") & (ablation.task == task)]
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        axes[0].bar(sub.group, sub.cv_mean, yerr=sub.cv_std)
        axes[0].set_title("Train CV Mean +/- Std")
        axes[1].bar(sub.group, sub[key])
        axes[1].set_title(f"Test {key}")
        fig.suptitle(f"XGBoost ablation / {task}; G5 excluded (no reliable ICT data)")
        fig.tight_layout()
        fig.savefig(figures_dir / f"16_ablation_{task}.png", dpi=180)
        plt.close(fig)

    # Confusion matrices use the same order: rows=true, columns=predicted, [Down, Up].
    for branch in predictions.feature_set.unique():
        subset = predictions[
            (predictions.task == "classification") & (predictions.feature_set == branch)
        ]
        names = list(subset.model.unique())
        fig, axes = plt.subplots(3, 5, figsize=(16, 10))
        for ax, name in zip(axes.flat, names):
            rows = subset[subset.model == name]
            matrix = confusion_matrix(rows.direction, rows.prediction, labels=[0, 1])
            ax.imshow(matrix, cmap="Blues", vmin=0, vmax=len(rows))
            for (i, j), value in np.ndenumerate(matrix):
                ax.text(j, i, str(value), ha="center", va="center")
            ax.set_xticks([0, 1], ["Down", "Up"])
            ax.set_yticks([0, 1], ["Down", "Up"])
            ax.set_title(name, fontsize=9)
            ax.set_xlabel("Predicted")
            ax.set_ylabel("Actual")
        fig.suptitle(branch + " / final Test confusion matrices")
        fig.tight_layout()
        fig.savefig(figures_dir / f"17_confusion_{branch}.png", dpi=180)
        plt.close(fig)


if __name__ == "__main__":
    run_training()
