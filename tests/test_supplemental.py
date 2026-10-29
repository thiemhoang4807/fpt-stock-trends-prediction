from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fetch_supplemental import (
    _period_end,
    _quarterly_fundamentals,
    prepare_multisource_features,
    release_aware_asof,
)
from train import _regression_metrics
from prepare import merge_supplemental, build_experiment_table, BRANCH_PRICE, BRANCH_MACRO
from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS, _market_cap_vnd


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
        pd.DataFrame({"time": ["2024-01-02"], "usd_vnd_rate": [24500.0]}).to_csv(
            raw_dir / "usd_vnd_daily.csv", index=False
        )
        pd.DataFrame({"time": ["2023-12-29", "2024-01-02"], "close": [1000., 1010.]}).to_csv(raw_dir / "vnindex_source.csv", index=False)
        aligned, audit = prepare_multisource_features(prices, raw_dir)
    assert "date" in aligned.columns
    assert aligned["usd_vnd_rate"].isna().tolist() == [True, True, False]
    assert aligned["usd_vnd_rate"].tolist()[2:] == [24500.0]
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


def test_stale_observation_expires_without_looking_forward():
    dates = pd.Series(pd.to_datetime(["2020-01-02", "2020-01-07", "2020-01-10"]))
    raw = pd.DataFrame({"time": ["2020-01-01", "2020-01-09"], "value": [10.0, 30.0]})
    aligned = release_aware_asof(dates, raw, delay_days=1, value_columns=["value"], max_age_days=3)
    assert aligned.loc[0, "value"] == 10.0
    assert pd.isna(aligned.loc[1, "value"])
    assert aligned.loc[2, "value"] == 30.0


def test_mixed_locale_source_dates_and_units_are_explicit():
    from fetch_supplemental import _parse_dates, _numeric
    assert _parse_dates(pd.Series(["09/10/2025"]), "%d/%m/%Y").iloc[0] == pd.Timestamp("2025-10-09")
    assert _parse_dates(pd.Series(["09/06/2025"]), "%m/%d/%Y").iloc[0] == pd.Timestamp("2025-09-06")
    assert _numeric(pd.Series(["26,421.0"])).iloc[0] == 26421.0
    assert _market_cap_vnd(pd.Series(["₫214.7t"])).iloc[0] == pytest.approx(214.7e12)


def test_required_supplementary_features_cannot_silently_disappear(tmp_path):
    path = tmp_path / "incomplete.csv"
    pd.DataFrame({"date": ["2020-01-01"], "usd_vnd_rate": [23000.0]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Missing required"):
        merge_supplemental(pd.DataFrame({"date": pd.to_datetime(["2020-01-01"])}), path)


def test_committed_sources_have_correct_ebit_and_same_two_branch_cohort():
    root = Path(__file__).resolve().parents[1]
    raw_finance = pd.read_csv(root / "data/raw/supplemental/fpt_income_statement_source.csv")
    normalized = pd.read_csv(root / "data/raw/supplemental/fpt_fundamentals_quarterly.csv")
    last = raw_finance.sort_values(["Năm", "Kỳ"]).iloc[-1]
    assert normalized.iloc[-1]["fpt_ebit_vnd"] == pytest.approx(last["LN trước thuế"] + abs(last["Chi phí tiền lãi vay"]))
    base, common, branches = build_experiment_table(root / "data/raw/fpt/fpt_historical_price.csv")
    assert len(branches[BRANCH_PRICE]) == 32
    assert len(branches[BRANCH_MACRO]) == 43
    assert set(MODEL_SUPPLEMENTAL_COLUMNS).issubset(branches[BRANCH_MACRO])
    assert common[branches[BRANCH_MACRO]].notna().all().all()
    assert common["target_date"].dropna().max() == pd.Timestamp("2025-09-30")
    assert not {"direction", "next_close", "next_return"}.intersection(branches[BRANCH_MACRO])


def test_vnindex_date_units_and_rejected_mismatched_payload():
    from fetch_supplemental import normalize_vnindex_response
    raw={"t":[1704157200],"o":[1100.],"h":[1120.],"l":[1095.],"c":[1110.],"v":[1000.]}
    got=normalize_vnindex_response(raw,"2024-01-01","2024-01-03")
    assert got.close.iloc[0] == 1110.
    raw["v"]=[]
    with pytest.raises(ValueError,match="equal"):
        normalize_vnindex_response(raw,"2024-01-01","2024-01-03")
