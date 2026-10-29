"""Post-hoc held-out explanations of trees selected using training CV only."""

import json
from pathlib import Path
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.inspection import permutation_importance
from prepare import build_experiment_table, DEFAULT_INPUT, DEFAULT_SUPPLEMENTAL

ROOT = Path(__file__).resolve().parents[1]


def explain(reports_dir=ROOT / "reports", figures_dir=ROOT / "figures"):
    _, table, _ = build_experiment_table(DEFAULT_INPUT, DEFAULT_SUPPLEMENTAL)
    table.attrs = {}
    table = table.dropna(subset=["next_log_return"]).reset_index(drop=True)
    cut = int(len(table) * 0.85)
    manifest = json.loads(
        (reports_dir / "evaluation_manifest.json").read_text(encoding="utf-8")
    )
    if isinstance(manifest, dict):
        manifest = manifest["models"]
    records = []
    for task in ("classification", "regression"):
        candidates = [
            m
            for m in manifest
            if m["task"] == task
            and ("XGBoost" in m["model"] or "Random Forest" in m["model"])
        ]
        selected = sorted(
            candidates, key=lambda m: m["cv_score"], reverse=task == "classification"
        )[0]
        artifact_path = Path(selected["path"])
        if not artifact_path.is_absolute():
            artifact_path = ROOT / artifact_path
        artifact = joblib.load(artifact_path)
        estimator = artifact["model"] if isinstance(artifact, dict) else artifact
        cols = selected["feature_columns"]
        test = table.iloc[cut:].copy()
        if task == "classification":
            test = test.dropna(subset=["direction"])
        X = test[cols]
        y = (
            test.direction.astype(int)
            if task == "classification"
            else test.next_log_return
        )
        scoring = (
            "balanced_accuracy"
            if task == "classification"
            else "neg_root_mean_squared_error"
        )
        perm = permutation_importance(
            estimator, X, y, scoring=scoring, n_repeats=10, random_state=42, n_jobs=1
        )
        permutation = pd.DataFrame(
            {
                "feature": cols,
                "importance_mean": perm.importances_mean,
                "importance_std": perm.importances_std,
            }
        ).sort_values("importance_mean", ascending=False)
        permutation.to_csv(
            reports_dir / f"permutation_importance_{task}.csv", index=False
        )
        fig, ax = plt.subplots(figsize=(10, 7))
        top = permutation.head(20).iloc[::-1]
        ax.barh(
            top.feature, top.importance_mean, xerr=top.importance_std, color="#4178a5"
        )
        ax.set_title(
            f"Permutation on Test: {selected['feature_set']} / {selected['model']}"
        )
        ax.set_xlabel(
            "Drop in balanced accuracy"
            if task == "classification"
            else "Increase in log-return RMSE"
        )
        fig.tight_layout()
        fig.savefig(figures_dir / f"permutation_{task}.png", dpi=180)
        plt.close(fig)
        # Background contains training inputs only; explanation sample is fixed, not chosen by errors.
        background = table.iloc[:cut][cols].sample(min(100, cut), random_state=42)
        sample = X.iloc[np.linspace(0, len(X) - 1, min(150, len(X))).astype(int)]
        explainer = shap.TreeExplainer(
            estimator, data=background, feature_perturbation="interventional"
        )
        values = explainer(sample, check_additivity=False)
        if values.values.ndim == 3:
            values = values[:, :, 1]
        # Check the explanation against the actual output scale, including XGB margins.
        if "XGBoost" in selected["model"]:
            raw_output = estimator.predict(sample, output_margin=True)
        elif task == "classification":
            raw_output = estimator.predict_proba(sample)[:, 1]
        else:
            raw_output = estimator.predict(sample)
        reconstructed = np.asarray(values.base_values) + values.values.sum(axis=1)
        if not np.isfinite(values.values).all() or not np.allclose(
            reconstructed, raw_output, rtol=1e-4, atol=1e-6
        ):
            raise RuntimeError("SHAP contributions do not reconstruct the model output")
        max_additivity_error = float(np.max(np.abs(reconstructed - raw_output)))
        shap.summary_plot(values.values, sample, show=False, max_display=20)
        plt.title(f"SHAP: {task} / {selected['model']}")
        plt.tight_layout()
        plt.savefig(
            figures_dir / f"shap_summary_{task}.png", dpi=180, bbox_inches="tight"
        )
        plt.close()
        importance = pd.DataFrame(
            {"feature": cols, "mean_abs_shap": np.abs(values.values).mean(axis=0)}
        ).sort_values("mean_abs_shap", ascending=False)
        importance.to_csv(reports_dir / f"shap_importance_{task}.csv", index=False)
        fig, ax = plt.subplots(figsize=(10, 7))
        top = importance.head(20).iloc[::-1]
        ax.barh(top.feature, top.mean_abs_shap, color="#559878")
        ax.set_title(f"Mean absolute SHAP: {task}")
        fig.tight_layout()
        fig.savefig(figures_dir / f"shap_bar_{task}.png", dpi=180)
        plt.close(fig)
        records.append(
            {
                "task": task,
                "model": selected["model"],
                "feature_set": selected["feature_set"],
                "selection": "training CV only",
                "permutation_scoring": scoring,
                "test_rows": len(test),
                "shap_rows": len(sample),
                "background": "100 training rows at most, random seed42",
                "shap_output": "raw model output; class1 for multiclass-shaped classifier output",
                "max_additivity_error": max_additivity_error,
            }
        )
    report = {
        "models": records,
        "limitations": "Post-hoc Test analysis only; no feature removal or retuning afterward. Correlated inputs share credit; permutation breaks temporal dependence and is descriptive, not causal. SHAP background only from Train.",
    }
    (reports_dir / "explainability_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    print(json.dumps(explain(), ensure_ascii=False, indent=2))
