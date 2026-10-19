"""Dataset audit and exploratory plots for FPT daily OHLCV data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from features import load_price_data


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"


def _ohlc_violations(data):
    valid = (
        data["low"].le(data[["open", "close"]].min(axis=1))
        & data["high"].ge(data[["open", "close"]].max(axis=1))
        & data["low"].le(data["high"])
    )
    return data.loc[~valid, ["time", "open", "high", "low", "close"]]


def run_eda(input_path: Path, figures_dir: Path, reports_dir: Path) -> dict:
    data = load_price_data(input_path)
    daily_return = data["close"].pct_change().dropna()
    next_return = data["close"].shift(-1) / data["close"] - 1.0
    counts = {
        "up": int(next_return.gt(0.0).sum()),
        "down": int(next_return.lt(0.0).sum()),
        "unchanged": int(np.isclose(next_return.fillna(np.nan), 0.0).sum()),
    }
    ohlc_errors = _ohlc_violations(data)
    figures_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(12, 5))
    plt.plot(data["time"], data["close"], linewidth=1.0, color="#2457A7")
    plt.title("Giá đóng cửa FPT theo ngày")
    plt.xlabel("Ngày giao dịch")
    plt.ylabel("Close (đơn vị theo dữ liệu nguồn)")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(figures_dir / "01_fpt_close.png", dpi=160)
    plt.close()

    plt.figure(figsize=(12, 5))
    plt.plot(data["time"], data["volume"], linewidth=0.8, color="#238B57")
    plt.yscale("symlog", linthresh=1.0)
    plt.title("Khối lượng giao dịch FPT theo ngày")
    plt.xlabel("Ngày giao dịch")
    plt.ylabel("Volume (symlog scale)")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(figures_dir / "02_fpt_volume.png", dpi=160)
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.hist(daily_return, bins=60, color="#5D78A8", edgecolor="white", linewidth=0.3)
    plt.axvline(0.0, color="#B33A3A", linestyle="--", linewidth=1.0)
    plt.title("Phân phối lợi nhuận đóng cửa-ngày trên ngày của FPT")
    plt.xlabel("Simple return")
    plt.ylabel("Số phiên")
    plt.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(figures_dir / "03_daily_return_distribution.png", dpi=160)
    plt.close()

    class_labels = ["Giảm", "Tăng", "Không đổi"]
    class_values = [counts["down"], counts["up"], counts["unchanged"]]
    plt.figure(figsize=(7, 4.5))
    plt.bar(class_labels, class_values, color=["#C85B55", "#368C68", "#9AA3AD"])
    plt.title("Hướng biến động đóng cửa ở phiên kế tiếp")
    plt.ylabel("Số phiên")
    plt.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(figures_dir / "04_next_session_class_balance.png", dpi=160)
    plt.close()

    q = daily_return.quantile([0.01, 0.25, 0.5, 0.75, 0.99])
    summary = {
        "input_file": str(input_path),
        "row_count": int(len(data)),
        "columns": list(data.columns),
        "date_start": data["time"].min().strftime("%Y-%m-%d"),
        "date_end": data["time"].max().strftime("%Y-%m-%d"),
        "missing_values_by_column": {key: int(value) for key, value in data.isna().sum().items()},
        "duplicate_dates": int(data["time"].duplicated().sum()),
        "is_chronologically_sorted": bool(data["time"].is_monotonic_increasing),
        "zero_volume_sessions": int(data["volume"].eq(0).sum()),
        "ohlc_consistency_violations": int(len(ohlc_errors)),
        "ohlc_violation_dates": [d.strftime("%Y-%m-%d") for d in ohlc_errors["time"]],
        "daily_return_min": float(daily_return.min()),
        "daily_return_max": float(daily_return.max()),
        "daily_return_mean": float(daily_return.mean()),
        "daily_return_std": float(daily_return.std(ddof=1)),
        "daily_return_quantiles": {str(k): float(v) for k, v in q.items()},
        "next_session_direction_counts": counts,
        "figures": [
            "figures/01_fpt_close.png",
            "figures/02_fpt_volume.png",
            "figures/03_daily_return_distribution.png",
            "figures/04_next_session_class_balance.png",
        ],
    }
    audit_path = reports_dir / "data_audit.json"
    audit_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit FPT OHLCV data and save EDA figures.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--figures", type=Path, default=ROOT / "figures")
    parser.add_argument("--reports", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    run_eda(args.input, args.figures, args.reports)


if __name__ == "__main__":
    main()
