"""One regression forecast yields a price and a signed direction (-1, 0, +1)."""

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def direction_from_return(values):
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Forecast log returns must be finite")
    return np.sign(values).astype(int)


def restore_price(current_close, predicted_log_return):
    close = np.asarray(current_close, dtype=float)
    returns = np.asarray(predicted_log_return, dtype=float)
    if not np.isfinite(close).all() or (close <= 0).any():
        raise ValueError("Current close must be finite and positive")
    direction_from_return(returns)
    with np.errstate(over="raise", invalid="raise"):
        result = close * np.exp(returns)
    if not np.isfinite(result).all() or (result <= 0).any():
        raise ValueError("Restored prices must be finite and positive")
    return result


def price_metrics(actual, predicted, current_close):
    actual, predicted, current = [
        np.asarray(x, dtype=float) for x in (actual, predicted, current_close)
    ]
    if not (actual.shape == predicted.shape == current.shape) or not actual.size:
        raise ValueError("Nonempty arrays must have matching shapes")
    if not np.isfinite([actual, predicted, current]).all() or (actual <= 0).any():
        raise ValueError("Invalid metric inputs")
    actual_direction = np.sign(actual - current)
    predicted_direction = np.sign(predicted - current)
    nonflat = actual_direction != 0
    relative_error = np.abs(predicted - actual) / actual
    result = {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mape_percent": float(relative_error.mean() * 100),
        "directional_accuracy_nonflat_percent": (
            float(
                (predicted_direction[nonflat] == actual_direction[nonflat]).mean() * 100
            )
            if nonflat.any()
            else float("nan")
        ),
    }
    for label, tolerance in [("0_5", 0.005), ("1", 0.01), ("2", 0.02)]:
        result[f"tolerance_accuracy_{label}_percent"] = float(
            (relative_error <= tolerance).mean() * 100
        )
    return result


def evaluate_returns(frame, predicted):
    predicted = np.asarray(predicted, dtype=float)
    if predicted.shape != (len(frame),):
        raise ValueError("One forecast is required for each evaluation row")
    prices = restore_price(frame.current_close, predicted)
    result = price_metrics(frame.next_close, prices, frame.current_close)
    actual = frame.next_log_return.to_numpy(dtype=float)
    # Compare signs directly; never change an exact zero into the up class.
    nonflat = actual != 0
    result["directional_accuracy_nonflat_percent"] = (
        float(
            (
                direction_from_return(predicted)[nonflat] == np.sign(actual[nonflat])
            ).mean()
            * 100
        )
        if nonflat.any()
        else float("nan")
    )
    result.update(
        log_return_mae=float(mean_absolute_error(actual, predicted)),
        log_return_rmse=float(np.sqrt(mean_squared_error(actual, predicted))),
        evaluation_rows=len(frame),
        nonflat_rows=int(nonflat.sum()),
    )
    return result
