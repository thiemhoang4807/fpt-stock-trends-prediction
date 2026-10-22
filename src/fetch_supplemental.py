"""Fetch and align market, macroeconomic, and FPT financial features safely."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "supplemental"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "fpt_multisource_features.csv"
DEFAULT_START = "2007-01-01"
DEFAULT_END = "2026-09-30"

DAILY_FILES = {
    "vnindex": "vnindex_ohlcv.csv",
    "fx": "usd_vnd_daily.csv",
    "gold": "gold_xauusd_daily.csv",
}


def _as_date(values: pd.Series) -> pd.Series:
    parsed = pd.Series(pd.to_datetime(values, errors="coerce", utc=True))
    result = parsed.dt.tz_convert("Asia/Ho_Chi_Minh").dt.tz_localize(None).dt.normalize()
    if isinstance(values, pd.Series):
        result.index = values.index
    return result


def _period_end(period: str) -> pd.Timestamp:
    """Convert a Vnstock reporting period such as 2026-Q2 to its final date."""
    text = str(period).strip()
    if "-Q" in text:
        year, quarter = text.split("-Q", maxsplit=1)
        quarter_num = int(quarter)
        if quarter_num not in (1, 2, 3, 4):
            raise ValueError(f"Invalid quarter: {period}")
        month = quarter_num * 3
        return pd.Timestamp(int(year), month, 1) + pd.offsets.MonthEnd(0)
    return pd.Timestamp(int(text), 12, 31)


def release_aware_asof(
    trading_dates: pd.Series,
    observations: pd.DataFrame,
    *,
    date_column: str = "time",
    delay_days: int,
    value_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Use only observations whose conservative availability date is <= session.

    Missing values before an observation becomes available remain missing. This
    function intentionally never backfills.
    """
    if date_column not in observations:
        raise ValueError(f"Missing observation date column: {date_column}")
    values = value_columns or [column for column in observations.columns if column != date_column]
    missing = sorted(set(values) - set(observations.columns))
    if missing:
        raise ValueError(f"Missing observation columns: {missing}")
    left = pd.DataFrame({"date": _as_date(trading_dates)}).sort_values("date")
    right = observations[[date_column, *values]].copy()
    right[date_column] = _as_date(right[date_column])
    right = right.dropna(subset=[date_column]).sort_values(date_column)
    right["available_date"] = right[date_column] + pd.to_timedelta(delay_days, unit="D")
    right = right.drop(columns=[date_column]).sort_values("available_date")
    right = right.drop_duplicates("available_date", keep="last")
    merged = pd.merge_asof(
        left,
        right,
        left_on="date",
        right_on="available_date",
        direction="backward",
        allow_exact_matches=True,
    )
    return merged.drop(columns=["available_date"])


def _market_frame(frame: pd.DataFrame, output_column: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["time", output_column])
    data = frame.copy()
    if "time" not in data.columns and "date" in data.columns:
        data = data.rename(columns={"date": "time"})
    price_column = "close" if "close" in data.columns else None
    if price_column is None:
        raise ValueError(f"Market response has no close column: {list(data.columns)}")
    return pd.DataFrame({"time": _as_date(data["time"]), output_column: pd.to_numeric(data[price_column], errors="coerce")})


def _quarterly_fundamentals(frame: pd.DataFrame) -> pd.DataFrame:
    """Select stable statement IDs where available, preserving missing metrics."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["time"])
    data = frame.copy()
    if "period" in data.columns:
        if "id" in data.columns and "value" in data.columns:
            data = data.loc[:, ["period", "id", "value"]]
            data["value"] = pd.to_numeric(data["value"], errors="coerce")
            data = data.pivot_table(index="period", columns="id", values="value", aggfunc="last").reset_index()
        data["time"] = data["period"].astype(str).map(_period_end)
    elif "time" not in data.columns:
        raise ValueError("Financial statement must include period or time")
    rename_candidates = {
        "IS_NET_REVENUE": "fpt_net_revenue_vnd",
        "IS_GROSS_PROFIT": "fpt_gross_profit_vnd",
        "IS_EBIT": "fpt_ebit_vnd",
        "IS_NET_PROFIT_AFTER_TAX": "fpt_net_profit_after_tax_vnd",
        "IS_NET_PROFIT_AFTER_TAX_PARENT": "fpt_parent_net_profit_vnd",
        "IS_NET_PROFIT_AFTER_TAX_ATTRIBUTABLE_TO_OWNERS": "fpt_parent_net_profit_vnd",
    }
    available = [column for column in rename_candidates if column in data.columns]
    selected = data.loc[:, ["time", *available]].rename(columns=rename_candidates)
    selected["time"] = _as_date(selected["time"])
    selected = selected.sort_values("time").drop_duplicates("time", keep="last")
    # The public quarterly statement may expose only consolidated NPAT. Keep the
    # parent-only field absent unless the source explicitly identifies it.
    return selected.reset_index(drop=True)


def _fetch_vnstock(start: str, end: str) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Download available series and preserve per-source errors for audit."""
    result: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    try:
        from vnstock import Fundamental, Macro, Market

        market = Market()
        macro = Macro()
        econ = macro.economy()
        currency = macro.currency()
    except Exception as exc:
        return result, {"client_initialization": f"{type(exc).__name__}: {exc}"}

    def fetch(name: str, callback, transform=None) -> None:
        try:
            frame = callback()
            result[name] = transform(frame) if transform else frame
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
            result[name] = pd.DataFrame()

    fetch(
        "vnindex",
        lambda: market.index("VNINDEX").ohlcv(start=start, end=end),
        lambda frame: _market_frame(frame, "vnindex_close_points"),
    )

    def normalize_fx(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=["time", "usd_vnd_market_rate", "usd_vnd_vcb_rate"])
        frame = frame.rename(columns={"market_rate": "usd_vnd_market_rate", "vcb_rate": "usd_vnd_vcb_rate"})
        frame["time"] = _as_date(frame["time"])
        keep = [column for column in ("time", "usd_vnd_market_rate", "usd_vnd_vcb_rate") if column in frame.columns]
        return frame[keep]

    fetch("fx", lambda: currency.exchange_rate(start=start, end=end, period="day"), normalize_fx)
    fetch(
        "gold",
        lambda: market.commodity("XAUUSD").ohlcv(start=start, end=end, floating=None),
        lambda frame: _market_frame(frame, "gold_usd_per_troy_ounce"),
    )
    fetch("cpi", lambda: econ.cpi(start=start, end=end, period="month"))
    fetch("gdp", lambda: econ.gdp(start=start, end=end, period="quarter"))
    for key in ("cpi", "gdp"):
        if key in result and not result[key].empty and "time" in result[key].columns:
            result[key]["time"] = _as_date(result[key]["time"])

    fetch(
        "fundamentals",
        lambda: Fundamental().equity("FPT").income_statement(
            period="quarter", lang="en", format="time_series", source="vci"
        ),
        _quarterly_fundamentals,
    )
    return result, errors


def _write_raw(frames: dict[str, pd.DataFrame], raw_dir: Path) -> dict[str, dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "vnindex": "vnindex_ohlcv.csv",
        "fx": "usd_vnd_daily.csv",
        "gold": "gold_xauusd_daily.csv",
        "cpi": "vietnam_cpi.csv",
        "gdp": "vietnam_gdp.csv",
        "fundamentals": "fpt_fundamentals_quarterly.csv",
    }
    empty_columns = {
        "vnindex": ["time", "open", "high", "low", "close", "volume"],
        "fx": ["time", "usd_vnd_market_rate", "usd_vnd_vcb_rate"],
        "gold": ["time", "open", "high", "low", "close", "volume"],
        "cpi": ["time", "cpi_total", "cpi_core"],
        "gdp": ["time", "gdp"],
        "fundamentals": ["time"],
    }
    info = {}
    for key, name in mapping.items():
        frame = frames.get(key, pd.DataFrame())
        if frame.empty and not len(frame.columns):
            frame = pd.DataFrame(columns=empty_columns[key])
        path = raw_dir / name
        frame.to_csv(path, index=False)
        date_column = "time" if "time" in frame.columns else None
        info[key] = {
            "file": path.name,
            "rows": int(len(frame)),
            "first_observation": str(frame[date_column].min())[:10] if date_column and len(frame) else None,
            "last_observation": str(frame[date_column].max())[:10] if date_column and len(frame) else None,
            "columns": list(frame.columns),
        }
    return info


def prepare_multisource_features(price_data: pd.DataFrame, raw_dir: Path = RAW_DIR) -> tuple[pd.DataFrame, dict]:
    """As-of align cached source files to FPT trading dates using release delays."""
    data = price_data.copy()
    dates = pd.to_datetime(data["time"], errors="coerce")
    data["date"] = dates.dt.normalize()
    reports: dict[str, dict] = {}
    specs = [
        ("vnindex_ohlcv.csv", ["vnindex_close_points"], 0, "vnindex"),
        ("usd_vnd_daily.csv", ["usd_vnd_market_rate", "usd_vnd_vcb_rate"], 1, "usd_vnd"),
        ("gold_xauusd_daily.csv", ["gold_usd_per_troy_ounce"], 1, "gold"),
        ("vietnam_cpi.csv", ["cpi_total", "cpi_core"], 10, "cpi"),
        ("vietnam_gdp.csv", ["gdp"], 45, "gdp"),
        (
            "fpt_fundamentals_quarterly.csv",
            [
                "fpt_net_revenue_vnd",
                "fpt_gross_profit_vnd",
                "fpt_ebit_vnd",
                "fpt_net_profit_after_tax_vnd",
                "fpt_parent_net_profit_vnd",
            ],
            45,
            "financial",
        ),
    ]
    for filename, candidates, delay, prefix in specs:
        path = raw_dir / filename
        if not path.is_file():
            reports[prefix] = {"status": "missing_file", "file": filename}
            continue
        raw = pd.read_csv(path)
        if raw.empty or "time" not in raw.columns:
            reports[prefix] = {"status": "empty_or_invalid", "file": filename, "rows": int(len(raw))}
            continue
        columns = [column for column in candidates if column in raw.columns]
        columns = [column for column in columns if pd.to_numeric(raw[column], errors="coerce").notna().any()]
        if not columns:
            reports[prefix] = {"status": "no_usable_columns", "file": filename, "rows": int(len(raw))}
            continue
        aligned = release_aware_asof(data["date"], raw, date_column="time", delay_days=delay, value_columns=columns)
        for column in columns:
            aligned[column] = pd.to_numeric(aligned[column], errors="coerce")
            data[column] = aligned[column].to_numpy()
        reports[prefix] = {
            "status": "aligned",
            "file": filename,
            "rows": int(len(raw)),
            "selected_columns": columns,
            "release_lag_calendar_days": delay,
            "first_feature_date": str(data.loc[data[columns].notna().any(axis=1), "date"].min())[:10]
            if data[columns].notna().any(axis=1).any()
            else None,
        }
    selected_features = [
        column
        for report in reports.values()
        for column in report.get("selected_columns", [])
    ]
    audit = {
        "date_start": str(dates.min())[:10],
        "date_end": str(dates.max())[:10],
        "rows": int(len(data)),
        "available_feature_columns": selected_features,
        "source_audit": reports,
        "no_backfill": True,
        "release_lags_calendar_days": {
            "daily_market_and_fx_gold": 1,
            "monthly_cpi": 10,
            "quarterly_gdp_and_company_financials": 45,
        },
    }
    return data, audit


def run_fetch(start: str, end: str, raw_dir: Path, output_path: Path) -> dict:
    if pd.Timestamp(start) > pd.Timestamp(end):
        raise ValueError("start must be on or before end")
    frames, fetch_errors = _fetch_vnstock(start, end)
    raw_info = _write_raw(frames, raw_dir)
    prices = pd.read_csv(ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv")
    prices["time"] = pd.to_datetime(prices["time"])
    aligned, audit = prepare_multisource_features(prices, raw_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(output_path, index=False)
    audit["raw_sources"] = raw_info
    audit["fetch_errors"] = fetch_errors
    audit["output_file"] = str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path)
    audit_path = ROOT / "reports" / "supplemental_data_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def run_from_cache(raw_dir: Path, output_path: Path) -> dict:
    prices = pd.read_csv(ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv")
    prices["time"] = pd.to_datetime(prices["time"])
    aligned, audit = prepare_multisource_features(prices, raw_dir)
    if not audit["available_feature_columns"]:
        raise ValueError("No usable supplementary feature columns were found in the cached source files")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(output_path, index=False)
    audit["output_file"] = str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path)
    (ROOT / "reports" / "supplemental_data_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return audit


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Fetch and align release-aware supplementary FPT features.")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--from-cache", action="store_true", help="Build from existing CSV source files without network calls.")
    args = parser.parse_args()
    audit = run_from_cache(args.raw_dir, args.output) if args.from_cache else run_fetch(args.start, args.end, args.raw_dir, args.output)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
