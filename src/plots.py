"""Figures for the three experiments; all lines are one-session forecasts."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def draw_experiments(metrics, predictions, experiments, figures_dir):
    figures_dir.mkdir(parents=True, exist_ok=True)
    for name in ["main_benchmark", "ablation", "statistical_extension"]:
        fig, axes = plt.subplots(2, 1, figsize=(13, 8))
        for ax, zoom in zip(axes, [False, True]):
            for index, config in enumerate(experiments[name]):
                frame = predictions[predictions.config_id.eq(config)].sort_values(
                    "target_date"
                )
                if zoom:
                    frame = frame.tail(80)
                dates = pd.to_datetime(frame.target_date)
                if index == 0:
                    ax.plot(
                        dates,
                        frame.actual_close,
                        color="black",
                        lw=1.6,
                        label="Actual close",
                    )
                label = frame.model.iloc[0]
                if name == "ablation":
                    label += " / " + frame.feature_level.iloc[0]
                ax.plot(dates, frame.predicted_close, lw=0.9, alpha=0.85, label=label)
            ax.set_ylabel("Thousand VND/share")
            ax.set_title(
                f"{name}: {'last 80 Test sessions' if zoom else 'all Test sessions'}"
            )
            ax.grid(alpha=0.2)
            ax.legend(ncol=3, fontsize=8)
        fig.tight_layout()
        fig.savefig(figures_dir / f"{name}_prices.png", dpi=190)
        plt.close(fig)
    for name in ["main_benchmark", "ablation", "lookback"]:
        frame = metrics.set_index("config_id").loc[experiments[name]]
        labels = frame.feature_level if name == "ablation" else frame.model
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
        measures = [
            ("cv_rmse_mean", "Train CV log-return RMSE"),
            ("mae", "Test MAE (thousand VND)"),
            ("directional_accuracy_nonflat_percent", "Test direction accuracy (%)"),
        ]
        for ax, (column, title) in zip(axes, measures):
            x = np.arange(len(frame))
            ax.bar(
                x,
                frame[column],
                yerr=frame.cv_rmse_std if column == "cv_rmse_mean" else None,
                capsize=4,
                color="#397a9e",
            )
            ax.set_xticks(x, labels, rotation=25, ha="right", fontsize=8)
            ax.set_title(title, fontsize=10)
            ax.grid(axis="y", alpha=0.2)
        fig.tight_layout()
        fig.savefig(figures_dir / f"{name}_metrics.png", dpi=190)
        plt.close(fig)
