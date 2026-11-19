"""Permutation explanations, supplemental SHAP, and observed error contexts."""

import json
from pathlib import Path
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FormatStrFormatter
import numpy as np
import pandas as pd
import shap
from sklearn.inspection import permutation_importance
from prepare import build_experiment_table, DEFAULT_INPUT, DEFAULT_SUPPLEMENTAL
from fetch_supplemental import load_market_closes

ROOT = Path(__file__).resolve().parents[1]


def error_cases(reports_dir, table):
    """Select three largest absolute price errors without inventing causes."""
    summary = json.loads((reports_dir / "training_summary.json").read_text())
    selected = summary["selected_model"]["config_id"]
    predictions = pd.read_csv(
        reports_dir / "test_predictions.csv", parse_dates=["date", "target_date"]
    )
    cases = predictions.loc[predictions.config_id.eq(selected)].copy()
    cases["absolute_price_error"] = abs(cases.actual_close - cases.predicted_close)
    cases = cases.nlargest(3, "absolute_price_error").copy()
    for key in ["volatility_20d", "rsi_14"]:
        if key in table:
            cases[key] = cases.date.map(table.set_index("date")[key])
    cases["actual_change_percent"] = np.expm1(cases.actual_log_return) * 100
    cases["predicted_change_percent"] = np.expm1(cases.predicted_log_return) * 100
    # Same-session market returns describe errors AFTER evaluation; they are not inputs.
    index = load_market_closes()
    returns = index.set_index("time").close.pct_change() * 100
    cases["vnindex_same_session_change_percent"] = cases.target_date.map(returns)
    cases["interpretation"] = (
        "Observed next-session move is much larger than the model forecast. "
        "Market co-movement is descriptive; the data alone do not identify a news cause."
    )
    cases.to_csv(reports_dir / "error_cases.csv", index=False)
    return cases


def explain(
    reports_dir=ROOT / "reports",
    figures_dir=ROOT / "figures",
    models_dir=ROOT / "models",
):
    _, table, _ = build_experiment_table(DEFAULT_INPUT, DEFAULT_SUPPLEMENTAL)
    table.attrs = {}
    table = table.dropna(subset=["next_log_return"]).reset_index(drop=True)
    cut = int(len(table) * 0.85)
    artifact = joblib.load(models_dir / "evaluation/xgboost_price.joblib")
    estimator, columns = artifact["model"], artifact["feature_columns"]
    X, y = table.iloc[cut:][columns], table.iloc[cut:].next_log_return
    perm = permutation_importance(
        estimator,
        X,
        y,
        scoring="neg_root_mean_squared_error",
        n_repeats=10,
        random_state=42,
        n_jobs=1,
    )
    permutation = pd.DataFrame(
        dict(
            feature=columns,
            importance_mean=perm.importances_mean,
            importance_std=perm.importances_std,
        )
    ).sort_values("importance_mean", ascending=False)
    permutation.to_csv(reports_dir / "permutation_importance.csv", index=False)
    fig, ax = plt.subplots(figsize=(10, 6))
    top = permutation.head(15).iloc[::-1]
    ax.barh(top.feature, top.importance_mean, xerr=top.importance_std, color="#4178a5")
    ax.axvline(0, color="black", lw=0.8)
    ax.set(
        title="XGBoost / price_32: permutation importance on Test",
        xlabel="Increase in log-return RMSE (mean +/- std, 10 repeats)",
    )
    fig.tight_layout()
    fig.savefig(figures_dir / "permutation_importance.png", dpi=180)
    plt.close(fig)
    background = table.iloc[:cut][columns].sample(min(100, cut), random_state=42)
    sample = X.iloc[np.linspace(0, len(X) - 1, min(150, len(X))).astype(int)]
    explainer = shap.TreeExplainer(
        estimator, data=background, feature_perturbation="interventional"
    )
    values = explainer(sample, check_additivity=True)
    pd.DataFrame(
        dict(feature=columns, mean_absolute_shap=np.abs(values.values).mean(axis=0))
    ).sort_values("mean_absolute_shap", ascending=False).to_csv(
        reports_dir / "shap_importance.csv", index=False
    )
    shap.summary_plot(values.values, sample, show=False, max_display=15)
    figure = plt.gcf()
    figure.set_size_inches(11, 7.5)
    axis = figure.axes[0]
    axis.xaxis.set_major_locator(MaxNLocator(nbins=5))
    axis.xaxis.set_major_formatter(FormatStrFormatter("%.3f"))
    axis.set_xlabel("SHAP contribution to predicted log return")
    plt.tight_layout()
    plt.savefig(figures_dir / "appendix_shap.png", dpi=180, bbox_inches="tight")
    plt.close()
    cases = error_cases(reports_dir, table)
    result = dict(
        explained_model="xgboost_price",
        fit_scope=artifact["fit_scope"],
        permutation_metric="increase in Test log-return RMSE",
        repeats=10,
        shap_background="100 Train rows",
        shap_sample_rows=len(sample),
        error_model=json.loads((reports_dir / "training_summary.json").read_text())[
            "selected_model"
        ]["config_id"],
        error_selection="three largest absolute price errors on final Test",
        error_dates=cases.target_date.dt.strftime("%Y-%m-%d").tolist(),
        interpretation="Post-hoc explanation only; do not use these Test importances to tune the current model.",
    )
    (reports_dir / "explainability_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(explain(), indent=2))
