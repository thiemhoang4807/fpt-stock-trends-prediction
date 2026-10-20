"""Generate next-session FPT direction and close estimates from the latest row."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from features import build_feature_table, load_price_data


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"


def predict_latest(input_path: Path, models_dir: Path, output_path: Path) -> dict:
    data = load_price_data(input_path)
    table = build_feature_table(data)
    latest = table.iloc[[-1]]
    classifier = joblib.load(models_dir / "best_classifier.joblib")
    regressor = joblib.load(models_dir / "best_regressor.joblib")
    features = latest[classifier["feature_columns"]]
    direction_value = int(classifier["model"].predict(features)[0])
    direction_prob_up = float(classifier["model"].predict_proba(features)[0, 1])
    if regressor["strategy"] == "last_close":
        predicted_close = float(latest["current_close"].iloc[0])
    else:
        predicted_close = float(regressor["model"].predict(latest[regressor["feature_columns"]])[0])
    current_close = float(latest["current_close"].iloc[0])
    result = {
        "as_of_session": latest["date"].iloc[0].strftime("%Y-%m-%d"),
        "prediction_target": "next observed trading session",
        "price_unit": "thousand VND per share",
        "current_close": current_close,
        "classifier_model": classifier["model_name"],
        "predicted_direction": "up" if direction_value == 1 else "down",
        "probability_up_conditional_on_nonflat_direction": direction_prob_up,
        "regression_model": regressor["model_name"],
        "predicted_next_close": predicted_close,
        "predicted_change_percent_from_current": (predicted_close / current_close - 1.0) * 100.0,
        "note": "Educational model output based on source history through the as-of session; not an investment recommendation.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict FPT's next observed trading-session direction and close.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--models", type=Path, default=ROOT / "models")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "latest_prediction.json")
    args = parser.parse_args()
    predict_latest(args.input, args.models, args.output)


if __name__ == "__main__":
    main()
