"""Temporal estimators with explicit forecasting origins and fold-local transforms.

Adapters take positional indices into the common evaluation table. When that
table contains ``attrs['sequence_context']``, windows and state updates use the
full trading-session context, not a compressed sequence of retained examples.
"""

from __future__ import annotations

import copy
import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
import torch
from torch import nn


class RecurrentForecaster(nn.Module):
    """One recurrent layer followed by a scalar forecast from its last state."""

    def __init__(self, input_size: int, hidden_size: int, kind: str):
        super().__init__()
        layer = nn.LSTM if kind.upper() == "LSTM" else nn.GRU
        self.recurrent = layer(input_size, hidden_size, batch_first=True)
        self.head = nn.Linear(hidden_size, 1)

    def forward(self, values):
        sequence, _ = self.recurrent(values)
        return self.head(sequence[:, -1, :]).squeeze(-1)


def _context(table: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    context = table.attrs.get("sequence_context", table)
    context = context.copy()
    context.attrs = {}
    if "session_index" in context:
        context = context.sort_values("session_index").reset_index(drop=True)
        session_ids = context["session_index"].to_numpy(dtype=int)
        if len(np.unique(session_ids)) != len(session_ids):
            raise ValueError("Duplicate session_index in sequence context")
        indexer = pd.Index(session_ids).get_indexer(table["session_index"])
        if (indexer < 0).any():
            raise ValueError("Common rows are missing from full session context")
    else:
        context = context.reset_index(drop=True)
        indexer = np.arange(len(table))
        context["session_index"] = np.arange(len(context))
    if "next_log_return" not in context:
        context["next_log_return"] = np.log(
            context["next_close"] / context["current_close"]
        )
    return context, indexer


def _windows(
    context: pd.DataFrame, columns: list[str], positions: np.ndarray, lookback: int
) -> tuple[np.ndarray, np.ndarray]:
    if lookback < 1:
        raise ValueError("lookback must be positive")
    values = context[columns].to_numpy(dtype=float)
    session_ids = context["session_index"].to_numpy(dtype=int)
    row_indices = []
    for position in positions:
        start = int(position) - lookback + 1
        if start < 0:
            raise ValueError(
                f"Insufficient context for lookback={lookback} at position {position}"
            )
        indices = np.arange(start, int(position) + 1)
        if not np.equal(np.diff(session_ids[indices]), 1).all():
            raise ValueError("A sliding window cannot skip trading sessions")
        if not np.isfinite(values[indices]).all():
            raise ValueError("A sliding window contains unavailable inputs")
        row_indices.append(indices)
    if not row_indices:
        return np.empty((0, lookback, len(columns))), np.array([], dtype=int)
    row_indices = np.stack(row_indices)
    return values[row_indices], np.unique(row_indices)


def _validate_indices(table, train_indices, eval_indices):
    train_indices = np.asarray(train_indices, dtype=int)
    eval_indices = np.asarray(eval_indices, dtype=int)
    if not len(train_indices):
        raise ValueError("Training indices cannot be empty")
    if (
        len(np.unique(train_indices)) != len(train_indices)
        or (np.diff(train_indices) <= 0).any()
    ):
        raise ValueError("Training indices must be unique and chronological")
    if len(eval_indices) and (
        (np.diff(eval_indices) <= 0).any() or train_indices[-1] >= eval_indices[0]
    ):
        raise ValueError("Evaluation must strictly follow training")
    if train_indices.min() < 0 or train_indices.max() >= len(table):
        raise ValueError("Training index outside table")
    if len(eval_indices) and (
        eval_indices.min() < 0 or eval_indices.max() >= len(table)
    ):
        raise ValueError("Evaluation index outside table")
    return train_indices, eval_indices


def fit_predict_sequence(
    kind: str,
    task: str,
    table: pd.DataFrame,
    feature_columns: list[str],
    train_indices,
    eval_indices,
    lookback: int = 20,
    epochs: int = 12,
    hidden_size: int = 16,
    seed: int = 42,
    learning_rate: float = 0.001,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit on past windows and return probabilities or next-session log returns.

    Regression targets are multiplied by 100 during neural optimization, then
    divided by 100 on output. No validation/test outcomes control epochs.
    """
    kind = kind.upper()
    if kind not in {"LSTM", "GRU"} or task not in {"classification", "regression"}:
        raise ValueError("Use LSTM/GRU and classification/regression")
    if epochs < 1 or hidden_size < 1:
        raise ValueError("epochs and hidden_size must be positive")
    train_indices, eval_indices = _validate_indices(table, train_indices, eval_indices)
    context, indexer = _context(table)
    target_column = "direction" if task == "classification" else "next_log_return"
    target_values = context[target_column].to_numpy(dtype=float)
    train_positions = indexer[train_indices]
    train_positions = train_positions[np.isfinite(target_values[train_positions])]
    if not len(train_positions):
        raise ValueError("No labeled training windows")
    train_windows, scaler_positions = _windows(
        context, feature_columns, train_positions, lookback
    )
    eval_windows, _ = _windows(
        context, feature_columns, indexer[eval_indices], lookback
    )
    scaler = StandardScaler().fit(context.iloc[scaler_positions][feature_columns])
    n_features = len(feature_columns)
    X_train = scaler.transform(
        pd.DataFrame(train_windows.reshape(-1, n_features), columns=feature_columns)
    ).reshape(train_windows.shape)
    y_train = target_values[train_positions].astype(np.float32)
    target_scale = 100.0 if task == "regression" else 1.0
    y_train = y_train * target_scale
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True)
    model = RecurrentForecaster(n_features, hidden_size, kind)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=learning_rate, weight_decay=1e-4
    )
    loss_function = nn.BCEWithLogitsLoss() if task == "classification" else nn.MSELoss()
    train_x = torch.as_tensor(X_train, dtype=torch.float32)
    train_y = torch.as_tensor(y_train, dtype=torch.float32)
    epoch_losses = []
    model.train()
    for _ in range(epochs):
        # Order is preserved; each window remains an independent training sample.
        total_loss = 0.0
        for start in range(0, len(train_x), 64):
            batch_x = train_x[start : start + 64]
            batch_y = train_y[start : start + 64]
            optimizer.zero_grad()
            loss = loss_function(model(batch_x), batch_y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.detach()) * len(batch_x)
        epoch_losses.append(total_loss / len(train_x))
    artifact = {
        "model_kind": "sequence",
        "architecture": kind,
        "task": task,
        "feature_columns": list(feature_columns),
        "lookback": int(lookback),
        "hidden_size": int(hidden_size),
        "epochs": int(epochs),
        "seed": int(seed),
        "learning_rate": float(learning_rate),
        "target_scale": target_scale,
        "scaler": scaler,
        "state_dict": copy.deepcopy(model.state_dict()),
        "training_loss": epoch_losses,
        "training_window_count": len(train_x),
        "scaler_context_rows": int(len(scaler_positions)),
        "scaler_last_session_index": int(
            context.iloc[scaler_positions[-1]]["session_index"]
        ),
        "trained_through_target_date": str(
            pd.Timestamp(context.iloc[train_positions[-1]]["target_date"]).date()
        ),
        "fit_scope": "training windows only; fixed epochs chosen without test outcomes",
    }
    prediction = _sequence_predictions(artifact, eval_windows)
    return prediction, artifact


def _sequence_predictions(artifact: dict, windows: np.ndarray) -> np.ndarray:
    if not len(windows):
        return np.array([], dtype=float)
    columns = artifact["feature_columns"]
    values = (
        artifact["scaler"]
        .transform(pd.DataFrame(windows.reshape(-1, len(columns)), columns=columns))
        .reshape(windows.shape)
    )
    model = RecurrentForecaster(
        len(columns), artifact["hidden_size"], artifact["architecture"]
    )
    model.load_state_dict(artifact["state_dict"])
    model.eval()
    with torch.no_grad():
        output = model(torch.as_tensor(values, dtype=torch.float32))
        if artifact["task"] == "classification":
            output = torch.sigmoid(output)
        return output.numpy().astype(float) / artifact["target_scale"]


def predict_sequence_artifact(artifact: dict, table: pd.DataFrame) -> np.ndarray:
    """Predict the last input row, retaining real consecutive context sessions."""
    context, indexer = _context(table)
    windows, _ = _windows(
        context, artifact["feature_columns"], indexer[-1:], artifact["lookback"]
    )
    return _sequence_predictions(artifact, windows)


def fit_predict_statistical(
    kind: str,
    table: pd.DataFrame,
    exog_columns: list[str],
    train_indices,
    eval_indices,
    order: tuple[int, int, int] = (1, 0, 0),
) -> tuple[np.ndarray, dict[str, Any]]:
    """One-step ARIMA/ARIMAX forecasts with frozen fitted parameters.

    State updates consume an observed return only AFTER forecasting that return.
    Intervening non-evaluation sessions, including a CV purge row, are processed
    in order. Exogenous values are aligned at input-session t to target t+1.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    kind = kind.upper()
    if kind not in {"ARIMA", "SARIMAX", "ARIMAX"}:
        raise ValueError("Unknown statistical model")
    train_indices, eval_indices = _validate_indices(table, train_indices, eval_indices)
    context, indexer = _context(table)
    first, last = int(indexer[train_indices[0]]), int(indexer[train_indices[-1]])
    training = context.iloc[first : last + 1]
    if not np.equal(np.diff(training["session_index"]), 1).all():
        raise ValueError(
            "Statistical training context must preserve all trading sessions"
        )
    y_train = training["next_log_return"].to_numpy(dtype=float) * 100.0
    if not np.isfinite(y_train).all():
        raise ValueError("Statistical model training outcomes must be observed")
    columns = list(exog_columns) if kind != "ARIMA" else []
    imputer = scaler = None
    train_exog = None
    missing_count = 0
    if columns:
        raw_exog = training[columns].to_numpy(dtype=float)
        if np.isnan(raw_exog).all(axis=0).any():
            raise ValueError(
                "A SARIMAX exogenous column is unavailable throughout Train"
            )
        missing_count = int(np.isnan(raw_exog).sum())
        imputer = SimpleImputer(strategy="median")
        scaler = StandardScaler()
        train_exog = scaler.fit_transform(imputer.fit_transform(raw_exog))
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        model = SARIMAX(
            y_train,
            exog=train_exog,
            order=tuple(order),
            seasonal_order=(0, 0, 0, 0),
            trend="n" if columns else "c",
            enforce_stationarity=True,
            enforce_invertibility=True,
        )
        fitted = model.fit(disp=False, maxiter=100)
    artifact = {
        "model_kind": "statistical",
        "architecture": kind,
        "task": "regression",
        "feature_columns": columns,
        "order": tuple(order),
        "seasonal_order": (0, 0, 0, 0),
        "model": fitted,
        "imputer": imputer,
        "scaler": scaler,
        "target_scale": 100.0,
        "training_context_rows": int(len(training)),
        "training_exog_missing_cells_imputed": missing_count,
        "training_first_input_date": str(pd.Timestamp(training.iloc[0]["date"]).date()),
        "training_last_input_date": str(pd.Timestamp(training.iloc[-1]["date"]).date()),
        "trained_through_target_date": str(
            pd.Timestamp(training.iloc[-1]["target_date"]).date()
        ),
        "converged": bool(fitted.mle_retvals.get("converged", True)),
        "warnings": sorted(set(str(item.message) for item in captured)),
        "fit_scope": "parameters fitted on Train calendar interval; test filtering updates states only",
        "exog_missing_policy": "median imputer and standard scaler fitted on Train only; no source backfill",
    }
    eval_positions = indexer[eval_indices]
    predicted = _statistical_roll(artifact, context, last + 1, eval_positions)
    return predicted, artifact


def _statistical_roll(
    artifact: dict, context: pd.DataFrame, start: int, eval_positions: np.ndarray
) -> np.ndarray:
    if not len(eval_positions):
        return np.array([], dtype=float)
    model = artifact["model"]
    columns = artifact["feature_columns"]
    selected = {int(position): i for i, position in enumerate(eval_positions)}
    prediction = np.empty(len(eval_positions), dtype=float)
    previous_target_date = pd.Timestamp(artifact["trained_through_target_date"])
    for position in range(start, int(max(eval_positions)) + 1):
        row = context.iloc[position]
        # At close t the previous outcome must already be available.
        if previous_target_date > pd.Timestamp(row["date"]):
            raise ValueError(
                "State update would use a target not yet observed at forecast origin"
            )
        exog = None
        if columns:
            values = row[columns].to_numpy(dtype=float).reshape(1, -1)
            exog = artifact["scaler"].transform(artifact["imputer"].transform(values))
        if position in selected:
            forecast = model.get_forecast(steps=1, exog=exog).predicted_mean
            prediction[selected[position]] = (
                float(np.asarray(forecast)[0]) / artifact["target_scale"]
            )
        outcome = row["next_log_return"]
        if pd.notna(outcome):
            model = model.extend(
                np.array([float(outcome) * artifact["target_scale"]]), exog=exog
            )
            previous_target_date = pd.Timestamp(row["target_date"])
        elif position < max(eval_positions):
            raise ValueError(
                "Missing intermediate outcome prevents chronological filtering"
            )
    return prediction


def predict_statistical_artifact(artifact: dict, table: pd.DataFrame) -> np.ndarray:
    """Filter newly observed outcomes since Train, then forecast the last input."""
    context, indexer = _context(table)
    last_fit_date = pd.Timestamp(artifact["training_last_input_date"])
    matched = np.flatnonzero(
        pd.to_datetime(context["date"]).eq(last_fit_date).to_numpy()
    )
    if len(matched) != 1:
        raise ValueError(
            "Cannot locate statistical training endpoint in prediction context"
        )
    start = int(matched[0]) + 1
    if start > indexer[-1]:
        raise ValueError(
            "Latest input must follow the last fitted statistical target row"
        )
    return _statistical_roll(artifact, context, start, indexer[-1:])
