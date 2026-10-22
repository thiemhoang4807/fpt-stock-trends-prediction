from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fetch_supplemental import (
    _period_end,
    _quarterly_fundamentals,
    prepare_multisource_features,
    release_aware_asof,
)
from train import _regression_metrics


def test_quarterly_period_is_made_available_only_after_publication_lag():
    dates = pd.to_datetime(["2026-08-10", "2026-08-14", "2026-08-17", "2026-09-30"])
    raw = pd.DataFrame({"time": ["2026-06-30"], "gdp": [8.2]})
    aligned = release_aware_asof(dates, raw, delay_days=45, value_columns=["gdp"])
    assert aligned["gdp"].isna().tolist() == [True, False, False, False]
    assert aligned.loc[2, "gdp"] == 8.2


def test_release_alignment_never_backfills_before_first_available_observation():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01"])
    raw = pd.DataFrame({"time": ["2024-01-01", "2024-01-10"], "cpi": [3.5, 3.7]})
    aligned = release_aware_asof(dates, raw, delay_days=10, value_columns=["cpi"])
    assert aligned["cpi"].isna().tolist() == [True, True, False]
    assert aligned.loc[2, "cpi"] == 3.7


def test_prepared_multisource_table_retains_session_date_and_only_fills_forward():
    prices = pd.DataFrame({"time": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])})
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp_dir:
        raw_dir = Path(temp_dir)
        pd.DataFrame({"time": ["2024-01-02"], "vnindex_close_points": [1200.0]}).to_csv(
            raw_dir / "vnindex_ohlcv.csv", index=False
        )
        aligned, audit = prepare_multisource_features(prices, raw_dir)
    assert "date" in aligned.columns
    assert aligned["vnindex_close_points"].isna().tolist() == [True, False, False]
    assert aligned["vnindex_close_points"].tolist()[1:] == [1200.0, 1200.0]
    assert audit["no_backfill"] is True


def test_financial_period_parser_and_long_statement_normalization():
    assert _period_end("2026-Q2") == pd.Timestamp("2026-06-30")
    raw = pd.DataFrame(
        {
            "period": ["2026-Q1", "2026-Q1", "2026-Q2", "2026-Q2"],
            "id": ["IS_NET_REVENUE", "IS_GROSS_PROFIT"] * 2,
            "value": [10, 4, 12, 5],
        }
    )
    normalized = _quarterly_fundamentals(raw)
    assert normalized["time"].dt.strftime("%Y-%m-%d").tolist() == ["2026-03-31", "2026-06-30"]
    assert normalized["fpt_net_revenue_vnd"].tolist() == [10, 12]
    assert normalized["fpt_gross_profit_vnd"].tolist() == [4, 5]


def test_regression_metrics_report_relative_tolerance_accuracy():
    actual = [100.0, 100.0, 100.0, 100.0]
    predicted = [100.4, 100.8, 101.5, 103.0]
    metrics = _regression_metrics(actual, predicted, [100.0, 100.0, 100.0, 100.0])
    assert metrics["tolerance_accuracy_0_5_percent"] == 25.0
    assert metrics["tolerance_accuracy_1_percent"] == 50.0
    assert metrics["tolerance_accuracy_2_percent"] == 75.0
