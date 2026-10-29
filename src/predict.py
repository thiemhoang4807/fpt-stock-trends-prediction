"""Generate next-session FPT direction and close estimates from the latest row."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sequence_models import predict_sequence_artifact, predict_statistical_artifact
from features import build_feature_table, load_price_data
from prepare import merge_supplemental


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
DEFAULT_SUPPLEMENTAL = ROOT / "data" / "processed" / "fpt_multisource_features.csv"


def predict_latest(input_path: Path, models_dir: Path, output_path: Path, supplemental_path: Path = DEFAULT_SUPPLEMENTAL) -> dict:
    data = load_price_data(input_path)
    table = build_feature_table(data)
    classifier = joblib.load(models_dir / "best_classifier.joblib")
    regressor = joblib.load(models_dir / "best_regressor.joblib")
    required_columns = set(classifier["feature_columns"]) | set(regressor["feature_columns"])
    if not required_columns.issubset(table.columns):
        table, _ = merge_supplemental(table, supplemental_path)
    if not required_columns.issubset(table.columns):
        missing = sorted(required_columns - set(table.columns))
        raise ValueError(f"Không thể tạo các đặc trưng cần cho mô hình đã lưu: {missing}")
    latest = table.iloc[[-1]]
    if latest["date"].iloc[0] != data["time"].iloc[-1]:
        raise ValueError("The last raw session has incomplete technical features")
    missing_latest = sorted(column for column in required_columns if latest[column].isna().any())
    if missing_latest:
        raise ValueError(f"Latest session is missing required inputs: {missing_latest}")
    def forecast(artifact):
        kind = artifact.get("model_kind", "tabular")
        if kind == "sequence":
            return float(predict_sequence_artifact(artifact, table)[0])
        if kind == "statistical":
            return float(predict_statistical_artifact(artifact, table)[0])
        return float(artifact["model"].predict(latest[artifact["feature_columns"]])[0])
    kind = classifier.get("model_kind", "tabular")
    direction_prob_up = None
    class_score_value = forecast(classifier)
    if kind == "sequence":
        direction_prob_up = class_score_value
        direction_value = int(class_score_value >= .5)
    elif kind == "statistical":
        direction_value = int(class_score_value > 0)
    else:
        direction_value = int(class_score_value)
        if hasattr(classifier["model"], "predict_proba"):
            direction_prob_up = float(classifier["model"].predict_proba(latest[classifier["feature_columns"]])[0,1])
        else:
            class_score_value = float(classifier["model"].decision_function(latest[classifier["feature_columns"]])[0])
    predicted_log_return = forecast(regressor)
    predicted_close = float(latest.current_close.iloc[0] * np.exp(predicted_log_return))
    current_close = float(latest["current_close"].iloc[0])
    result = {
        "as_of_session": latest["date"].iloc[0].strftime("%Y-%m-%d"),
        "prediction_target": "next observed trading session",
        "price_unit": "thousand VND per share",
        "current_close": current_close,
        "classifier_model": classifier["model_name"],
        "classifier_feature_set": classifier.get("feature_set", "Branch_1_Price_Only"),
        "predicted_direction": "up" if direction_value == 1 else "down",
        "probability_up_conditional_on_nonflat_direction": direction_prob_up,
        "regression_model": regressor["model_name"],
        "regression_feature_set": regressor.get("feature_set", "Branch_1_Price_Only"),
        "predicted_next_log_return": predicted_log_return,
        "direction_score": class_score_value,
        "direction_score_note": "Probability is null for SVC margins or statistical return forecasts; do not interpret these scores as probabilities.",
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
    parser.add_argument("--supplemental", type=Path, default=DEFAULT_SUPPLEMENTAL)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "latest_prediction.json")
    args = parser.parse_args()
    predict_latest(args.input, args.models, args.output, args.supplemental)


if __name__ == "__main__":
    main()
