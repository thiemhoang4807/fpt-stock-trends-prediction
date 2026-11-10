"""Select compact report rows using training CV, without rerunning models."""

import pandas as pd

FAMILY_ORDER = [
    "Baseline",
    "Linear family",
    "SVM",
    "Random Forest",
    "XGBoost",
    "HistGradientBoosting",
    "Statistical",
    "LSTM",
    "GRU",
]


def model_family(name):
    """Group linear variants and lookback settings for a nine-row benchmark."""
    if "baseline" in name.lower():
        return "Baseline"
    if name.startswith(("Logistic", "Linear", "Ridge")):
        return "Linear family"
    if name in ("SVC", "SVR"):
        return "SVM"
    if name in ("ARIMA", "SARIMAX"):
        return "Statistical"
    for family in FAMILY_ORDER:
        if name.startswith(family):
            return family
    raise ValueError(f"Unknown model family: {name}")


def select_representatives(cv_summary, test_metrics, task):
    """Choose one configuration per branch/family from Train CV, then join Test.

    Classification maximizes mean balanced accuracy; regression minimizes mean
    log-return RMSE. Equal CV scores retain their original experiment order.
    Test values are only attached after the selection has been completed.
    """
    if task not in ("classification", "regression"):
        raise ValueError(f"Unknown task: {task}")
    key = (
        "balanced_accuracy_mean" if task == "classification" else "log_return_rmse_mean"
    )
    candidates = cv_summary.loc[cv_summary.task.eq(task)].copy()
    candidates["family"] = candidates.model.map(model_family)
    if candidates[key].isna().any():
        raise ValueError("Missing CV score; a representative cannot be selected")
    chosen = candidates.sort_values(
        key, ascending=task == "regression", kind="stable"
    ).drop_duplicates(["feature_set", "family"])
    std_key = key.removesuffix("_mean") + "_std"
    chosen = chosen[["feature_set", "family", "model", key, std_key]].rename(
        columns={key: "cv_mean", std_key: "cv_std"}
    )
    result = chosen.merge(
        test_metrics,
        on=["feature_set", "model"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not result["_merge"].eq("both").all():
        raise ValueError("A CV-selected model has no corresponding Test row")
    result["family_order"] = result.family.map(FAMILY_ORDER.index)
    return (
        result.sort_values(["feature_set", "family_order"])
        .drop(columns=["_merge", "family_order"])
        .reset_index(drop=True)
    )
