"""Draw the experiment figures from one-session forecasts or saved report tables."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_TITLES = {
    "main_benchmark": "Đối sánh năm phương pháp trên dữ liệu FPT",
    "ablation": "XGBoost khi bổ sung từng nhóm dữ liệu",
    "statistical_extension": "Đối sánh ARIMA và SARIMAX",
    "lookback": "GRU với cửa sổ 20 và 60 phiên",
}
FEATURE_LABELS = {
    "price_32": "32 biến FPT",
    "macro_38": "38 biến (+ thị trường, vĩ mô)",
    "financial_42": "42 biến (+ tài chính)",
}
MODEL_LABELS = {"Last-Close Baseline": "Giữ giá", "Ridge Regression": "Ridge"}
COLORS = ("#676b73", "#0072b2", "#d55e00", "#009e73", "#9262a5")
LINE_STYLES = ("--", "-.", "-", ":", "--")


def _price_chart(name, frames, figures_dir):
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), layout="constrained")
    fig.suptitle(EXPERIMENT_TITLES[name], weight="bold", fontsize=15)
    for ax, zoom in zip(axes, (False, True)):
        actual = frames[0].tail(80) if zoom else frames[0]
        ax.plot(
            actual.target_date, actual.actual_close,
            color="#252a31", lw=1.7, label="Giá thực tế", zorder=5,
        )
        for index, frame in enumerate(frames):
            frame = frame.tail(80) if zoom else frame
            if name == "ablation":
                label = FEATURE_LABELS[frame.feature_level.iloc[0]]
            else:
                model = frame.model.iloc[0]
                label = MODEL_LABELS.get(model, model)
            ax.plot(
                frame.target_date, frame.predicted_close, label=label,
                color=COLORS[index], linestyle=LINE_STYLES[index], lw=1.15,
            )
        locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(
                locator, formats=["%Y", "%m/%Y", "%d/%m", "%H:%M", "%H:%M", "%S"]
            )
        )
        ax.set_ylabel("Nghìn VND/cổ phiếu")
        scope = "80 phiên Test cuối" if zoom else f"Toàn bộ {len(actual)} phiên Test"
        ax.set_title(scope, loc="left", fontsize=11)
        ax.grid(alpha=0.2)
    axes[0].legend(ncol=3, fontsize=9, loc="upper left")
    fig.savefig(figures_dir / f"{name}_prices.png", dpi=190)
    plt.close(fig)


def _metric_chart(name, frame, figures_dir):
    if name == "ablation":
        labels = frame.feature_level.map({
            "price_32": "32 biến\nFPT",
            "macro_38": "38 biến\n+ Thị trường, vĩ mô",
            "financial_42": "42 biến\n+ Tài chính",
        })
    else:
        labels = frame.model.replace(MODEL_LABELS)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), layout="constrained")
    fig.suptitle(EXPERIMENT_TITLES[name], weight="bold", fontsize=15)
    measures = [
        (
            frame.cv_rmse_mean * 100, frame.cv_rmse_std * 100,
            "RMSE log return qua 5 fold Train\nTrung bình ± độ lệch chuẩn", "% log return", 3,
        ),
        (frame.mae, None, "MAE giá trên Test", "Nghìn VND/cổ phiếu", 4),
        (
            frame.directional_accuracy_nonflat_percent, None,
            "Đúng hướng trên Test", "% phiên có biến động", 2,
        ),
    ]
    x = np.arange(len(frame))
    for ax, (values, errors, title, unit, places) in zip(axes, measures):
        bars = ax.bar(x, values, yerr=errors, capsize=4, color=COLORS[:len(frame)])
        ax.bar_label(bars, fmt=f"%.{places}f", padding=3, fontsize=8)
        ax.set_xticks(x, labels, fontsize=9)
        if name == "main_benchmark":
            ax.tick_params(axis="x", labelrotation=18)
        ax.set_title(title, fontsize=11)
        ax.set_ylabel(unit)
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=0.2)
        ax.margins(y=0.14)
    axes[-1].set_ylim(0, 100)
    fig.savefig(figures_dir / f"{name}_metrics.png", dpi=190)
    plt.close(fig)


def draw_experiments(metrics, predictions, experiments, figures_dir):
    figures_dir.mkdir(parents=True, exist_ok=True)
    curves = {
        config: frame.assign(target_date=pd.to_datetime(frame.target_date)).sort_values(
            "target_date"
        )
        for config, frame in predictions.groupby("config_id")
    }
    for name in ("main_benchmark", "ablation", "statistical_extension"):
        _price_chart(name, [curves[config] for config in experiments[name]], figures_dir)

    indexed = metrics.set_index("config_id")
    for name in ("main_benchmark", "ablation", "lookback"):
        _metric_chart(name, indexed.loc[experiments[name]], figures_dir)


if __name__ == "__main__":
    reports = ROOT / "reports"
    draw_experiments(
        pd.read_csv(reports / "all_test_metrics.csv"),
        pd.read_csv(reports / "test_predictions.csv"),
        {
            name: pd.read_csv(reports / f"{name}.csv").config_id.tolist()
            for name in EXPERIMENT_TITLES
        },
        ROOT / "figures",
    )
