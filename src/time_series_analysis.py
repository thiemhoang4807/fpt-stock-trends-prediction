"""Descriptive stationarity and dependence diagnostics, separate from model inputs."""

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import STL
from features import load_price_data
from prepare import build_experiment_table, DEFAULT_INPUT, DEFAULT_SUPPLEMENTAL

ROOT = Path(__file__).resolve().parents[1]


def stationarity(series, name, scope):
    """ADF H0=unit root; KPSS H0=level stationarity. Non-rejection is not proof."""
    x = pd.Series(series).dropna().to_numpy(dtype=float)
    rows = []
    for test in ("ADF", "KPSS"):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = (
                adfuller(x, regression="c", autolag="AIC")
                if test == "ADF"
                else kpss(x, regression="c", nlags="auto")
            )
        statistic, pvalue, lag = result[:3]
        critical = result[4] if test == "ADF" else result[3]
        reject = bool(pvalue < 0.05)
        rows.append(
            {
                "series": name,
                "scope": scope,
                "test": test,
                "n": len(x),
                "statistic": float(statistic),
                "p_value": float(pvalue),
                "lags": int(lag),
                "critical_values": {str(k): float(v) for k, v in critical.items()},
                "null_hypothesis": "unit root" if test == "ADF" else "level stationary",
                "reject_null_at_5pct": reject,
                "conclusion": (
                    (
                        "evidence against unit root"
                        if reject
                        else "unit root not rejected"
                    )
                    if test == "ADF"
                    else (
                        "level stationarity rejected"
                        if reject
                        else "level stationarity not rejected"
                    )
                ),
                "warnings": [str(w.message) for w in caught],
            }
        )
    return rows


def run_analysis(
    input_path=DEFAULT_INPUT,
    supplemental_path=DEFAULT_SUPPLEMENTAL,
    reports_dir=ROOT / "reports",
    figures_dir=ROOT / "figures",
):
    prices = load_price_data(input_path)
    _, common, _ = build_experiment_table(input_path, supplemental_path)
    labeled = common.dropna(subset=["target_date"])
    train_end = labeled.iloc[int(len(labeled) * 0.85) - 1].target_date
    prices["log_return"] = np.log(prices.close / prices.close.shift(1))
    rows = []
    for scope, frame in [
        ("train_history", prices.loc[prices.time.le(train_end)]),
        ("full_snapshot_descriptive_only", prices),
    ]:
        for name in ["close", "log_return"]:
            rows.extend(stationarity(frame[name], name, scope))
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "train_history_end": str(train_end.date()),
        "alpha": 0.05,
        "regression": "constant (level stationarity)",
        "note": "Full-snapshot diagnostics are descriptive only, not used to choose parameters. KPSS endpoint p-values may be bounds; see warnings.",
        "tests": rows,
    }
    (reports_dir / "stationarity_tests.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    csv = pd.DataFrame(rows)
    csv["critical_values"] = csv.critical_values.map(json.dumps)
    csv["warnings"] = csv.warnings.map(json.dumps)
    csv.to_csv(reports_dir / "stationarity_tests.csv", index=False)
    train = prices.loc[prices.time.le(train_end)]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for i, name in enumerate(["close", "log_return"]):
        x = train[name].dropna()
        plot_acf(
            x, lags=40, alpha=0.05, ax=axes[i, 0], title=f"{name}: ACF (Train history)"
        )
        plot_pacf(
            x,
            lags=40,
            alpha=0.05,
            method="ywm",
            ax=axes[i, 1],
            title=f"{name}: PACF (Train history)",
        )
    fig.tight_layout()
    fig.savefig(figures_dir / "12_acf_pacf.png", dpi=180)
    plt.close(fig)
    # Five trading observations are a descriptive cycle, not evidence of seasonality.
    x = np.log(train.set_index("time").close)
    decomposition = STL(x, period=5, robust=True).fit()
    fig = decomposition.plot()
    fig.set_size_inches(13, 9)
    fig.suptitle(
        "STL: log(close), period=5 trading sessions; Train history only", y=1.0
    )
    fig.tight_layout()
    fig.savefig(figures_dir / "13_time_series_decomposition.png", dpi=180)
    plt.close(fig)
    return report


if __name__ == "__main__":
    print(json.dumps(run_analysis(), indent=2, ensure_ascii=False))
