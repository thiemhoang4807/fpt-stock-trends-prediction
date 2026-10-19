"""Leakage-safe feature engineering for next-session FPT stock experiments."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "volume")

FEATURE_COLUMNS = [
    "return_1d",
    "return_2d",
    "return_5d",
    "return_10d",
    "return_20d",
    "sma_5_ratio",
    "sma_10_ratio",
    "sma_20_ratio",
    "sma_50_ratio",
    "ema_5_ratio",
    "ema_10_ratio",
    "ema_20_ratio",
    "ema_50_ratio",
    "rsi_14",
    "macd_ratio",
    "macd_signal_ratio",
    "macd_histogram_ratio",
    "bollinger_percent_b_20",
    "bollinger_width_20",
    "volatility_5d",
    "volatility_20d",
    "log_volume_change_1d",
    "log_volume_zscore_20d",
]

REGRESSION_FEATURE_COLUMNS = FEATURE_COLUMNS + ["current_close"]


def load_price_data(path: str | Path) -> pd.DataFrame:
    """Load and validate daily OHLCV without filling values from the future."""
    data = pd.read_csv(path)
    data.columns = [str(column).strip().lower() for column in data.columns]
    if "date" in data.columns and "time" not in data.columns:
        data = data.rename(columns={"date": "time"})

    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(data.columns))
    if missing_columns:
        raise ValueError(f"Input data is missing required columns: {missing_columns}")

    data = data.loc[:, REQUIRED_COLUMNS].copy()
    data["time"] = pd.to_datetime(data["time"], errors="coerce")
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    invalid = data[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    if invalid.any():
        raise ValueError(f"Input contains {int(invalid.sum())} rows with missing or invalid values")
    if data["time"].duplicated().any():
        duplicated = data.loc[data["time"].duplicated(keep=False), "time"].dt.strftime("%Y-%m-%d").tolist()
        raise ValueError(f"Duplicate trading dates found: {duplicated[:10]}")
    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be strictly positive")
    if (data["volume"] < 0).any():
        raise ValueError("Volume cannot be negative")

    return data.sort_values("time").reset_index(drop=True)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    change = close.diff()
    gain = change.clip(lower=0.0)
    loss = -change.clip(upper=0.0)
    average_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    average_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    result = 100.0 - (100.0 / (1.0 + relative_strength))
    result = result.mask(average_loss.eq(0.0) & average_gain.gt(0.0), 100.0)
    return result.mask(average_loss.eq(0.0) & average_gain.eq(0.0), 50.0)


def build_feature_table(data: pd.DataFrame) -> pd.DataFrame:
    """Create features known at close(t) and outcomes for the next observed session."""
    close = data["close"].astype(float)
    log_volume = np.log1p(data["volume"].astype(float))
    one_day_return = close.pct_change()
    result = pd.DataFrame(index=data.index)
    result["date"] = data["time"]
    result["target_date"] = data["time"].shift(-1)
    result["current_close"] = close
    result["next_close"] = close.shift(-1)
    result["next_return"] = result["next_close"] / result["current_close"] - 1.0
    result["direction"] = np.select(
        [result["next_return"].gt(0.0), result["next_return"].lt(0.0)],
        [1.0, 0.0],
        default=np.nan,
    )

    for period in (1, 2, 5, 10, 20):
        result[f"return_{period}d"] = close.pct_change(period)

    for period in (5, 10, 20, 50):
        sma = close.rolling(period, min_periods=period).mean()
        ema = close.ewm(span=period, min_periods=period, adjust=False).mean()
        result[f"sma_{period}_ratio"] = close / sma - 1.0
        result[f"ema_{period}_ratio"] = close / ema - 1.0

    result["rsi_14"] = _rsi(close, 14) / 100.0
    ema_12 = close.ewm(span=12, min_periods=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, min_periods=26, adjust=False).mean()
    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9, min_periods=9, adjust=False).mean()
    result["macd_ratio"] = macd / close
    result["macd_signal_ratio"] = macd_signal / close
    result["macd_histogram_ratio"] = (macd - macd_signal) / close

    band_mean = close.rolling(20, min_periods=20).mean()
    band_std = close.rolling(20, min_periods=20).std(ddof=0)
    upper_band = band_mean + 2.0 * band_std
    lower_band = band_mean - 2.0 * band_std
    result["bollinger_percent_b_20"] = (close - lower_band) / (upper_band - lower_band)
    result["bollinger_width_20"] = (upper_band - lower_band) / band_mean

    result["volatility_5d"] = one_day_return.rolling(5, min_periods=5).std(ddof=0)
    result["volatility_20d"] = one_day_return.rolling(20, min_periods=20).std(ddof=0)
    result["log_volume_change_1d"] = log_volume.diff()
    volume_mean = log_volume.rolling(20, min_periods=20).mean()
    volume_std = log_volume.rolling(20, min_periods=20).std(ddof=0)
    result["log_volume_zscore_20d"] = (log_volume - volume_mean) / volume_std.replace(0.0, np.nan)

    # Warm-up NaNs arise from backward-looking indicators only. No backward fill is used.
    result = result.replace([np.inf, -np.inf], np.nan)
    return result.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
