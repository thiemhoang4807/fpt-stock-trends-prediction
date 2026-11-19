"""Three focused experiments with Train-only CV and one log-return target."""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from metrics import (
    evaluate_returns,
    restore_price,
    direction_from_return,
    price_metrics,
)
from prepare import (
    build_experiment_table,
    feature_groups,
    DEFAULT_INPUT,
    DEFAULT_SUPPLEMENTAL,
)
from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS
from sequence_models import fit_predict_sequence, fit_predict_statistical

ROOT = Path(__file__).resolve().parents[1]
_regression_metrics = price_metrics


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


def cv_splits(n):
    return list(TimeSeriesSplit(n_splits=5, gap=1).split(np.arange(n)))


def experiment_specs():
    """Predeclared small grids. The two ablation extensions are added after CV."""
    return {
        "last_close": ("Last-Close Baseline", "price_32", [dict(kind="baseline")]),
        "ridge": (
            "Ridge Regression",
            "price_32",
            [dict(kind="ridge", alpha=a) for a in (10.0, 100.0)],
        ),
        "xgboost_price": (
            "XGBoost",
            "price_32",
            [dict(kind="xgboost", max_depth=d) for d in (2, 3)],
        ),
        "arima": (
            "ARIMA",
            "price_32",
            [dict(kind="ARIMA", order=o) for o in [(0, 0, 0), (1, 0, 0)]],
        ),
        "gru_20": ("GRU L=20", "price_32", [dict(kind="GRU", lookback=20)]),
        "gru_60": ("GRU L=60", "price_32", [dict(kind="GRU", lookback=60)]),
        "sarimax": (
            "SARIMAX",
            "financial_42",
            [dict(kind="SARIMAX", order=o) for o in [(0, 0, 0), (1, 0, 0)]],
        ),
    }


def make_estimator(spec):
    kind = spec["kind"]
    if kind == "baseline":
        return DummyRegressor(strategy="constant", constant=0.0)
    if kind == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=spec["alpha"]))
    if kind == "xgboost":
        return XGBRegressor(
            n_estimators=120,
            max_depth=spec["max_depth"],
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=8,
            reg_lambda=3,
            random_state=42,
            n_jobs=1,
        )
    raise ValueError(f"Unknown tabular estimator: {kind}")


def fit_candidate(spec, data, columns, train_indices, evaluation_indices):
    """All adapters return log returns; no classifier is fitted here."""
    kind = spec["kind"]
    if kind == "GRU":
        return fit_predict_sequence(
            "GRU",
            "regression",
            data,
            columns,
            train_indices,
            evaluation_indices,
            lookback=spec["lookback"],
            epochs=12,
            hidden_size=16,
        )
    if kind in ("ARIMA", "SARIMAX"):
        return fit_predict_statistical(
            kind,
            data,
            MODEL_SUPPLEMENTAL_COLUMNS if kind == "SARIMAX" else [],
            train_indices,
            evaluation_indices,
            order=spec["order"],
        )
    model = clone(make_estimator(spec))
    model.fit(
        data.iloc[train_indices][columns], data.iloc[train_indices].next_log_return
    )
    prediction = (
        np.asarray(model.predict(data.iloc[evaluation_indices][columns]), dtype=float)
        if len(evaluation_indices)
        else np.array([], dtype=float)
    )
    return prediction, dict(
        model_kind="tabular",
        model=model,
        task="regression",
        feature_columns=columns,
    )


def select_main_ids(cv_summary):
    """Select a GRU lookback and the deployment winner without reading Test."""
    scores = cv_summary.set_index("config_id").cv_rmse_mean
    gru = min(["gru_20", "gru_60"], key=lambda name: scores[name])
    main = ["last_close", "ridge", "xgboost_price", "arima", gru]
    return main, min(main, key=lambda name: scores[name])


def _search(config_id, name, level, candidates, data, columns, folds):
    fold_rows, candidate_rows = [], []
    for candidate_id, spec in enumerate(candidates):
        values = []
        for fold, (a, b) in enumerate(folds, 1):
            prediction, artifact = fit_candidate(spec, data, columns, a, b)
            metrics = evaluate_returns(data.iloc[b], prediction)
            values.append(metrics["log_return_rmse"])
            fold_rows.append(
                dict(
                    config_id=config_id,
                    model=name,
                    feature_level=level,
                    candidate_id=candidate_id,
                    fold=fold,
                    **metrics,
                    converged=artifact.get("converged", True),
                    warnings=json.dumps(artifact.get("warnings", [])),
                )
            )
        candidate_rows.append(
            dict(
                config_id=config_id,
                model=name,
                feature_level=level,
                candidate_id=candidate_id,
                cv_rmse_mean=float(np.mean(values)),
                cv_rmse_std=float(np.std(values, ddof=1)),
                configuration=json.dumps(spec, sort_keys=True),
            )
        )
    best = min(candidate_rows, key=lambda row: row["cv_rmse_mean"])
    return candidates[best["candidate_id"]], best, candidate_rows, fold_rows


def run_training(
    input_path=DEFAULT_INPUT,
    figures_dir=ROOT / "figures",
    reports_dir=ROOT / "reports",
    models_dir=ROOT / "models",
    processed_dir=ROOT / "data/processed",
    supplemental_path=DEFAULT_SUPPLEMENTAL,
):
    for path in [figures_dir, reports_dir, models_dir / "evaluation", processed_dir]:
        path.mkdir(parents=True, exist_ok=True)
    base, common, _ = build_experiment_table(input_path, supplemental_path)
    context = common.attrs["sequence_context"]
    common.attrs = {}
    base.to_csv(processed_dir / "fpt_next_session_features.csv", index=False)
    common.to_csv(processed_dir / "fpt_experiment_features.csv", index=False)
    data = common.dropna(subset=["next_log_return"]).reset_index(drop=True)
    data.attrs["sequence_context"] = context
    masks, boundaries = _chronological_splits(data)
    a = np.flatnonzero(masks["train"])
    b = np.flatnonzero(masks["test"])
    folds = cv_splits(len(a))
    groups = feature_groups()
    catalog = experiment_specs()
    selected_specs, summaries, all_candidates, cv_rows = {}, [], [], []
    for config_id, (name, level, candidates) in catalog.items():
        print("CV", config_id, flush=True)
        spec, best, candidate_rows, fold_rows = _search(
            config_id,
            name,
            level,
            candidates,
            data,
            groups[level],
            folds,
        )
        selected_specs[config_id] = spec
        summaries.append(best)
        all_candidates.extend(candidate_rows)
        cv_rows.extend(fold_rows)
    # Keep the XGBoost hyperparameters fixed: only the input columns change.
    for config_id, level in [
        ("xgboost_macro", "macro_38"),
        ("xgboost_financial", "financial_42"),
    ]:
        spec = selected_specs["xgboost_price"].copy()
        catalog[config_id] = ("XGBoost", level, [spec])
        _, best, candidate_rows, fold_rows = _search(
            config_id,
            "XGBoost",
            level,
            [spec],
            data,
            groups[level],
            folds,
        )
        selected_specs[config_id] = spec
        summaries.append(best)
        all_candidates.extend(candidate_rows)
        cv_rows.extend(fold_rows)
    cv = pd.DataFrame(summaries)
    main_ids, selected_id = select_main_ids(cv)
    # All choices are now locked, before the first final Test prediction.
    plan = dict(
        main_ids=main_ids,
        selected_id=selected_id,
        selection="minimum five-fold Train CV RMSE of log return",
        selected_configurations=selected_specs,
        boundaries=boundaries,
        ablation="XGBoost settings chosen on price_32 then fixed for all three levels",
        statistical_comparison="same order grid and constant trend; orders selected within Train CV",
        historical_test_note="Dates were observed in earlier designs; this is a retrospective redesign, not a new untouched holdout.",
    )
    (reports_dir / "experiment_plan.json").write_text(
        json.dumps(plan, indent=2), encoding="utf-8"
    )
    cv.to_csv(reports_dir / "cv_summary.csv", index=False)
    pd.DataFrame(all_candidates).to_csv(
        reports_dir / "cv_candidate_summary.csv", index=False
    )
    pd.DataFrame(cv_rows).to_csv(reports_dir / "cv_fold_metrics.csv", index=False)

    test_rows, prediction_rows, manifest = [], [], []
    for config_id, (name, level, _) in catalog.items():
        print("TEST", config_id, flush=True)
        spec = selected_specs[config_id]
        prediction, artifact = fit_candidate(spec, data, groups[level], a, b)
        artifact.update(
            config_id=config_id,
            model_name=name,
            feature_level=level,
            fit_scope="Train only; frozen parameters during Test",
            trained_through_target_date=boundaries["train_target_date_end"],
        )
        path = models_dir / "evaluation" / f"{config_id}.joblib"
        joblib.dump(artifact, path)
        cv_row = cv.loc[cv.config_id.eq(config_id)].iloc[0]
        test_rows.append(
            dict(
                config_id=config_id,
                model=name,
                feature_level=level,
                feature_count=len(artifact["feature_columns"]),
                cv_rmse_mean=cv_row.cv_rmse_mean,
                cv_rmse_std=cv_row.cv_rmse_std,
                **evaluate_returns(data.iloc[b], prediction),
            )
        )
        frame = data.iloc[b]
        records = pd.DataFrame(
            dict(
                config_id=config_id,
                model=name,
                feature_level=level,
                date=frame.date.to_numpy(),
                target_date=frame.target_date.to_numpy(),
                current_close=frame.current_close.to_numpy(),
                actual_close=frame.next_close.to_numpy(),
                actual_log_return=frame.next_log_return.to_numpy(),
                predicted_log_return=prediction,
                actual_direction=np.sign(frame.next_log_return.to_numpy()).astype(int),
                predicted_direction=direction_from_return(prediction),
                predicted_close=restore_price(frame.current_close, prediction),
            )
        )
        prediction_rows.append(records)
        manifest.append(
            dict(
                config_id=config_id,
                model=name,
                feature_level=level,
                configuration=spec,
                path=(
                    path.relative_to(ROOT).as_posix()
                    if path.is_relative_to(ROOT)
                    else str(path)
                ),
                feature_columns=artifact["feature_columns"],
                fit_scope=artifact["fit_scope"],
                converged=artifact.get("converged", True),
                training_context_rows=artifact.get("training_context_rows", len(a)),
                warnings=artifact.get("warnings", []),
            )
        )
    metrics = pd.DataFrame(test_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    metrics.to_csv(reports_dir / "all_test_metrics.csv", index=False)
    predictions.to_csv(reports_dir / "test_predictions.csv", index=False)
    experiments = {
        "main_benchmark": main_ids,
        "ablation": ["xgboost_price", "xgboost_macro", "xgboost_financial"],
        "statistical_extension": ["arima", "sarimax"],
        "lookback": ["gru_20", "gru_60"],
    }
    for name, identifiers in experiments.items():
        metrics.set_index("config_id").loc[identifiers].reset_index().to_csv(
            reports_dir / f"{name}.csv",
            index=False,
        )
    (reports_dir / "evaluation_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    name, level, _ = catalog[selected_id]
    _, artifact = fit_candidate(
        selected_specs[selected_id],
        data,
        groups[level],
        np.arange(len(data)),
        np.array([], dtype=int),
    )
    artifact.update(
        config_id=selected_id,
        model_name=name,
        feature_level=level,
        fit_scope="All labeled rows; refit after frozen evaluation",
        trained_through_target_date=boundaries["test_target_date_end"],
    )
    joblib.dump(artifact, models_dir / "best_regressor.joblib")
    summary = dict(
        selected_model=dict(config_id=selected_id, model=name, feature_level=level),
        main_model_ids=main_ids,
        split=boundaries,
        target="next_log_return",
        artifact_count=10,
        test_configurations=9,
        cv_folds=[
            dict(
                fold=i,
                train_rows=len(x),
                validation_rows=len(y),
                train_target_end=str(data.iloc[x[-1]].target_date.date()),
                validation_input_start=str(data.iloc[y[0]].date.date()),
                validation_target_end=str(data.iloc[y[-1]].target_date.date()),
            )
            for i, (x, y) in enumerate(folds, 1)
        ],
    )
    (reports_dir / "training_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    from plots import draw_experiments

    draw_experiments(metrics, predictions, experiments, figures_dir)
    return summary


if __name__ == "__main__":
    print(json.dumps(run_training(), indent=2))
