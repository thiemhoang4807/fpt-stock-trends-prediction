"""Normalize frozen public-source snapshots and align them without future filling."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "supplemental"
PRICE_PATH = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "fpt_multisource_features.csv"
DEFAULT_END = "2025-09-30"

# Every declared field is required for the common two-branch comparison.
MODEL_SUPPLEMENTAL_COLUMNS = [
    "usd_vnd_rate",
    "gold_vnd_per_ounce",
    "cpi_yoy_pct",
    "gdp_usd",
    "ict_market_cap_vnd",
    "ict_pe",
    "ict_absolute_pe",
    "fpt_net_revenue_vnd",
    "fpt_gross_profit_vnd",
    "fpt_ebit_vnd",
    "fpt_parent_net_profit_vnd",
    "fpt_shares_outstanding",
]


def _parse_dates(values: pd.Series, fmt: str) -> pd.Series:
    result = pd.to_datetime(values, format=fmt, errors="coerce")
    return pd.Series(result, index=values.index).dt.normalize()


def _numeric(values: pd.Series, *, percent: bool = False) -> pd.Series:
    text = values.astype("string").str.strip().str.replace(",", "", regex=False)
    if percent:
        text = text.str.replace("%", "", regex=False)
    return pd.to_numeric(text, errors="coerce")


def _market_cap_vnd(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.strip().str.replace(",", "", regex=False)
    trillion = text.str.contains("t", case=False, na=False)
    number = pd.to_numeric(text.str.replace(r"[^0-9.\\-]", "", regex=True), errors="coerce")
    return number * np.where(trillion, 1_000_000_000_000.0, 1.0)


def _multiple(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.strip().str.replace("x", "", case=False, regex=False)
    return pd.to_numeric(text, errors="coerce")


def _quarter_end(year: pd.Series, quarter: pd.Series) -> pd.Series:
    year_number = pd.to_numeric(year, errors="coerce")
    quarter_number = pd.to_numeric(quarter, errors="coerce")
    month = quarter_number * 3
    return pd.to_datetime(
        year_number.astype("Int64").astype("string") + "-" + month.astype("Int64").astype("string") + "-01",
        errors="coerce",
    ) + pd.offsets.MonthEnd(0)


def _period_end(period: str) -> pd.Timestamp:
    """Parse a YYYY-Qn reporting period for API export compatibility."""
    text = str(period).strip()
    if "-Q" not in text:
        return pd.Timestamp(int(text), 12, 31)
    year, quarter = text.split("-Q", maxsplit=1)
    quarter_number = int(quarter)
    if quarter_number not in (1, 2, 3, 4):
        raise ValueError(f"Kỳ báo cáo không hợp lệ: {period}")
    return pd.Timestamp(int(year), quarter_number * 3, 1) + pd.offsets.MonthEnd(0)


def _quarterly_fundamentals(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize a long-form financial API response when one is provided."""
    if frame.empty:
        return pd.DataFrame(columns=["time"])
    data = frame.copy()
    if {"period", "id", "value"}.issubset(data.columns):
        data["value"] = pd.to_numeric(data["value"], errors="coerce")
        data = data.pivot_table(index="period", columns="id", values="value", aggfunc="last").reset_index()
        data["time"] = data["period"].map(_period_end)
    if "time" not in data.columns:
        raise ValueError("Báo cáo tài chính phải có period hoặc time")
    mapping = {
        "IS_NET_REVENUE": "fpt_net_revenue_vnd",
        "IS_GROSS_PROFIT": "fpt_gross_profit_vnd",
        "IS_EBIT": "fpt_ebit_vnd",
        "IS_NET_PROFIT_AFTER_TAX_PARENT": "fpt_parent_net_profit_vnd",
    }
    selected = [column for column in mapping if column in data.columns]
    return data[["time", *selected]].rename(columns=mapping).sort_values("time").reset_index(drop=True)


def trim_source_exports(raw_dir: Path, end: str) -> dict[str, int]:
    """Freeze vendor exports at the requested cutoff, retaining their schema."""
    date_specs = {
        "usd_vnd_source.csv": ("Ngày", "%d/%m/%Y"),
        "gold_xauusd_source.csv": ("Ngày", "%d/%m/%Y"),
        "vietnam_cpi_source.csv": ("Ngày Phát Hành", "%m/%d/%Y"),
        "ict_industry_source.csv": ("Date", "%d-%m-%Y"),
    }
    removed = {}
    cutoff = pd.Timestamp(end)
    for filename, (column, fmt) in date_specs.items():
        path = raw_dir / filename
        frame = pd.read_csv(path)
        dates = _parse_dates(frame[column], fmt)
        if dates.isna().any():
            raise ValueError(f"Invalid source dates in {filename}")
        keep = dates.le(cutoff)
        removed[filename] = int((~keep).sum())
        frame.loc[keep].to_csv(path, index=False, lineterminator="\n")
    for filename in ("vietnam_gdp_source.csv", "fpt_income_statement_source.csv"):
        path = raw_dir / filename
        frame = pd.read_csv(path)
        if "GDP" in " ".join(frame.columns):
            keep = pd.to_numeric(frame["Year"], errors="raise").lt(cutoff.year)
        else:
            keep = _quarter_end(frame["Năm"], frame["Kỳ"]).le(cutoff)
        removed[filename] = int((~keep).sum())
        frame.loc[keep].to_csv(path, index=False, lineterminator="\n")
    return removed


def normalize_source_snapshots(raw_dir: Path = RAW_DIR, end: str = DEFAULT_END) -> dict[str, dict]:
    """Convert vendor-export CSVs into stable, documented machine-readable tables."""
    end_date = pd.Timestamp(end).normalize()
    outputs: dict[str, pd.DataFrame] = {}
    specs = {
        "usd_vnd_source.csv": "usd_vnd_daily.csv",
        "gold_xauusd_source.csv": "gold_xauusd_daily.csv",
        "vietnam_cpi_source.csv": "vietnam_cpi.csv",
        "vietnam_gdp_source.csv": "vietnam_gdp.csv",
        "ict_industry_source.csv": "ict_industry.csv",
        "fpt_income_statement_source.csv": "fpt_fundamentals_quarterly.csv",
    }
    missing_files = [name for name in specs if not (raw_dir / name).is_file()]
    if missing_files:
        raise FileNotFoundError(f"Thiếu snapshot nguồn: {missing_files}")

    fx = pd.read_csv(raw_dir / "usd_vnd_source.csv")
    outputs["usd_vnd_daily.csv"] = pd.DataFrame({
        "time": _parse_dates(fx["Ngày"], "%d/%m/%Y"),
        "usd_vnd_rate": _numeric(fx["Lần cuối"]),
    })

    gold = pd.read_csv(raw_dir / "gold_xauusd_source.csv")
    outputs["gold_xauusd_daily.csv"] = pd.DataFrame({
        "time": _parse_dates(gold["Ngày"], "%d/%m/%Y"),
        "gold_usd_per_ounce": _numeric(gold["Lần cuối"]),
    })

    cpi = pd.read_csv(raw_dir / "vietnam_cpi_source.csv")
    outputs["vietnam_cpi.csv"] = pd.DataFrame({
        "time": _parse_dates(cpi["Ngày Phát Hành"], "%m/%d/%Y"),
        "cpi_yoy_pct": _numeric(cpi["Thực tế"], percent=True),
    })

    gdp = pd.read_csv(raw_dir / "vietnam_gdp_source.csv")
    gdp_year = pd.to_numeric(gdp["Year"], errors="coerce")
    gdp = gdp.loc[gdp_year.le(end_date.year - 1)].copy()
    # Annual GDP is considered observable only after a conservative six-month lag.
    outputs["vietnam_gdp.csv"] = pd.DataFrame({
        "time": pd.to_datetime(pd.to_numeric(gdp["Year"], errors="coerce").astype("Int64").astype("string") + "-12-31", errors="coerce"),
        "gdp_usd": pd.to_numeric(gdp["GDP_in_USD"], errors="coerce"),
    })

    industry = pd.read_csv(raw_dir / "ict_industry_source.csv")
    outputs["ict_industry.csv"] = pd.DataFrame({
        "time": _parse_dates(industry["Date"], "%d-%m-%Y"),
        "ict_market_cap_vnd": _market_cap_vnd(industry["Market Cap"]),
        "ict_pe": _multiple(industry["PE"]),
        "ict_absolute_pe": _multiple(industry["Absolute PE"]),
    })

    financial = pd.read_csv(raw_dir / "fpt_income_statement_source.csv")
    report_date = _quarter_end(financial["Năm"], financial["Kỳ"])
    outputs["fpt_fundamentals_quarterly.csv"] = pd.DataFrame({
        "time": report_date,
        "fpt_net_revenue_vnd": _numeric(financial["Doanh thu thuần"]),
        "fpt_gross_profit_vnd": _numeric(financial["Lãi gộp"]),
        # Source interest expenses are signed negative: EBT - signed interest
        # expense = earnings before interest and tax under this definition.
        "fpt_ebit_vnd": _numeric(financial["LN trước thuế"]) + _numeric(financial["Chi phí tiền lãi vay"]).abs(),
        "fpt_parent_net_profit_vnd": _numeric(financial["Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)"]),
    })

    audit: dict[str, dict] = {}
    for filename, frame in outputs.items():
        frame = frame.dropna(subset=["time"]).copy()
        frame = frame.loc[frame["time"].le(end_date)]
        value_columns = [column for column in frame.columns if column != "time"]
        frame = frame.dropna(subset=value_columns, how="all")
        frame = frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
        frame.to_csv(raw_dir / filename, index=False, date_format="%Y-%m-%d", lineterminator="\n")
        audit[filename] = {
            "rows": int(len(frame)),
            "first_date": str(frame["time"].min().date()) if len(frame) else None,
            "last_date": str(frame["time"].max().date()) if len(frame) else None,
            "columns": list(frame.columns),
            "missing_values": {column: int(frame[column].isna().sum()) for column in frame.columns},
            "sha256": hashlib.sha256((raw_dir / filename).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        }
    return audit


def release_aware_asof(
    trading_dates: pd.Series,
    observations: pd.DataFrame,
    *,
    date_column: str = "time",
    delay_days: int,
    value_columns: list[str] | None = None,
    max_age_days: int | None = None,
) -> pd.DataFrame:
    """Join only values whose conservative availability date is not in the future."""
    if date_column not in observations:
        raise ValueError(f"Thiếu cột ngày {date_column}")
    values = value_columns or [column for column in observations.columns if column != date_column]
    left_dates = pd.Series(pd.to_datetime(trading_dates, errors="coerce"))
    left = pd.DataFrame({"date": left_dates.dt.normalize()})
    right = observations[[date_column, *values]].copy()
    right[date_column] = pd.to_datetime(right[date_column], errors="coerce").dt.normalize()
    right = right.dropna(subset=[date_column]).sort_values(date_column)
    right["available_date"] = right[date_column] + pd.to_timedelta(delay_days, unit="D")
    right = right.drop(columns=[date_column]).sort_values("available_date")
    right = right.drop_duplicates("available_date", keep="last")
    if delay_days < 0 or (max_age_days is not None and max_age_days < 0):
        raise ValueError("Availability delay and maximum age cannot be negative")
    return pd.merge_asof(
        left.sort_values("date"), right, left_on="date", right_on="available_date",
        direction="backward", allow_exact_matches=True,
        tolerance=pd.Timedelta(days=max_age_days) if max_age_days is not None else None,
    ).drop(columns=["available_date"])


def prepare_multisource_features(price_data: pd.DataFrame, raw_dir: Path = RAW_DIR, end: str = DEFAULT_END) -> tuple[pd.DataFrame, dict]:
    """Create one point-in-time feature row per FPT session; never backfill."""
    data = price_data.copy()
    data["date"] = pd.to_datetime(data["time"], errors="coerce").dt.normalize()
    end_date = pd.Timestamp(end)
    data = data.loc[data["date"].le(end_date)].sort_values("date").reset_index(drop=True)
    delays = {
        "usd_vnd_daily.csv": ("usd_vnd", ["usd_vnd_rate"], 1, 10),
        "gold_xauusd_daily.csv": ("gold", ["gold_usd_per_ounce"], 1, 10),
        "vietnam_cpi.csv": ("cpi", ["cpi_yoy_pct"], 1, 65),
        "vietnam_gdp.csv": ("gdp", ["gdp_usd"], 180, 550),
        "ict_industry.csv": ("industry", ["ict_market_cap_vnd", "ict_pe", "ict_absolute_pe"], 1, 180),
        "fpt_fundamentals_quarterly.csv": (
            "fundamentals",
            ["fpt_net_revenue_vnd", "fpt_gross_profit_vnd", "fpt_ebit_vnd", "fpt_parent_net_profit_vnd"],
            45, 150,
        ),
        "fpt_shares_outstanding.csv": ("shares", ["fpt_shares_outstanding"], 1, 550),
    }
    source_audit: dict[str, dict] = {}
    for filename, (group, columns, delay, max_age) in delays.items():
        path = raw_dir / filename
        if not path.is_file():
            source_audit[group] = {"status": "missing", "file": filename}
            continue
        raw = pd.read_csv(path)
        selected = [column for column in columns if column in raw.columns]
        if raw.empty or "time" not in raw.columns or not selected:
            source_audit[group] = {"status": "empty_or_invalid", "file": filename, "rows": int(len(raw))}
            continue
        for column in selected:
            raw[column] = pd.to_numeric(raw[column], errors="coerce")
        aligned = release_aware_asof(data["date"], raw, delay_days=delay, value_columns=selected, max_age_days=max_age)
        for column in selected:
            data[column] = aligned[column].to_numpy()
        valid = data[selected].notna().any(axis=1)
        source_audit[group] = {
            "status": "aligned",
            "file": filename,
            "raw_rows": int(len(raw)),
            "selected_columns": selected,
            "availability_delay_calendar_days": int(delay),
            "maximum_age_after_availability_calendar_days": int(max_age),
            "first_available_session": str(data.loc[valid, "date"].min().date()) if valid.any() else None,
            "last_available_session": str(data.loc[valid, "date"].max().date()) if valid.any() else None,
            "missing_session_values": {column: int(data[column].isna().sum()) for column in selected},
        }
    if {"gold_usd_per_ounce", "usd_vnd_rate"}.issubset(data.columns):
        data["gold_vnd_per_ounce"] = data["gold_usd_per_ounce"] * data["usd_vnd_rate"]
    audit = {
        "cutoff_date": end,
        "rows": int(len(data)),
        "date_start": str(data["date"].min().date()) if len(data) else None,
        "date_end": str(data["date"].max().date()) if len(data) else None,
        "no_backfill": True,
        "alignment": "backward as-of join; each value appears only after its availability date",
        "release_delays_calendar_days": {
            "daily_market_fx_gold_and_industry": 1,
            "cpi_after_source_release_date": 1,
            "annual_gdp_after_period_end": 180,
            "quarterly_fundamentals_after_period_end": 45,
            "shares_outstanding_after_source_availability_date": 1,
        },
        "model_supplemental_columns": MODEL_SUPPLEMENTAL_COLUMNS,
        "point_in_time_limitations": "Financial +45d and annual GDP +180d are assumed release dates, not a historical release-vintage archive; revisions and index constituent changes can remain.",
        "source_audit": source_audit,
    }
    return data, audit


def run_from_cache(raw_dir: Path, output_path: Path, end: str = DEFAULT_END, trim_inputs: bool = False) -> dict:
    end = pd.Timestamp(end).strftime("%Y-%m-%d")
    trimmed = trim_source_exports(raw_dir, end) if trim_inputs else {}
    raw_audit = normalize_source_snapshots(raw_dir, end=end)
    prices = pd.read_csv(PRICE_PATH)
    prices["time"] = pd.to_datetime(prices["time"], errors="coerce")
    prices = prices.loc[prices["time"].le(pd.Timestamp(end))]
    aligned, audit = prepare_multisource_features(prices, raw_dir, end=end)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(output_path, index=False, date_format="%Y-%m-%d", lineterminator="\n")
    audit["normalized_raw_sources"] = raw_audit
    audit["input_rows_removed_by_cutoff_this_run"] = trimmed
    audit["input_snapshots"] = {
        path.name: {"sha256": hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(), "bytes": path.stat().st_size}
        for path in sorted(raw_dir.glob("*_source.csv"))
    }
    shares_path = raw_dir / "fpt_shares_outstanding.csv"
    audit["input_snapshots"][shares_path.name] = {"sha256": hashlib.sha256(shares_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(), "bytes": shares_path.stat().st_size}
    audit["output_file"] = output_path.relative_to(ROOT).as_posix() if output_path.is_relative_to(ROOT) else str(output_path)
    audit_path = ROOT / "reports" / "supplemental_data_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Normalize archived macro, industry, and FPT financial CSVs; align them without look-ahead.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--from-cache", action="store_true", help="Explicitly select the offline, reproducible snapshot workflow.")
    parser.add_argument("--trim-inputs", action="store_true", help="Also remove source-export observations after the cutoff and GDP forecast year.")
    args = parser.parse_args()
    audit = run_from_cache(args.raw_dir, args.output, end=args.end, trim_inputs=args.trim_inputs)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
