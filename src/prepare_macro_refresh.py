"""Validate the XAU/USD export and prepare annual CPI/GDP for source review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from fetch_historical_candidates import CUTOFF, DEST, ROOT, normalize_gdp
from fetch_supplemental import PRICE_PATH, RAW_DIR, release_aware_asof

OUTPUT = ROOT / "data/local/macro_2007"
GOLD_URL = "https://vn.investing.com/currencies/xau-usd-historical-data"
CPI_URL = "https://api.worldbank.org/v2/en/indicator/FP.CPI.TOTL.ZG?downloadformat=csv"
GOLD_HEADERS = {"Mở": "open", "Cao": "high", "Thấp": "low", "Lần cuối": "close"}


def normalize_gold(source: bytes) -> tuple[pd.DataFrame, dict]:
    """Read the Investing.com Vietnamese export with day-first dates and US prices."""
    columns = ["Ngày", *GOLD_HEADERS]
    frame = pd.read_csv(
        io.BytesIO(source), encoding="utf-8-sig", usecols=columns, dtype=str
    )
    frame = frame.rename(columns={"Ngày": "time", **GOLD_HEADERS})
    frame["time"] = pd.to_datetime(frame.time, format="%d/%m/%Y", errors="raise")
    if frame.empty or frame.time.isna().any() or frame.time.duplicated().any():
        raise ValueError("XAU/USD dates must be present and unique")
    prices = list(GOLD_HEADERS.values())
    for col in prices:
        values = frame[col].str.strip()
        if (
            not values.str.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?")
            .fillna(False)
            .all()
        ):
            raise ValueError(f"Invalid or missing XAU/USD price in {col}")
        frame[col] = pd.to_numeric(values.str.replace(",", "", regex=False))
    if not np.isfinite(frame[prices]).all().all() or frame[prices].le(0).any().any():
        raise ValueError("XAU/USD prices must be finite and positive")
    if (frame.low > frame[["open", "close"]].min(axis=1)).any() or (
        frame.high < frame[["open", "close"]].max(axis=1)
    ).any():
        raise ValueError("XAU/USD OHLC violates the reported daily range")
    frame = frame.sort_values("time")[["time", "open", "high", "low", "close"]]
    after_cutoff = frame.time.gt(CUTOFF)
    audit = {
        "source_url": GOLD_URL,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_rows": len(frame),
        "source_start": frame.time.iloc[0].strftime("%Y-%m-%d"),
        "source_end": frame.time.iloc[-1].strftime("%Y-%m-%d"),
        "rows_after_cutoff_removed": int(after_cutoff.sum()),
        "price_unit": "USD per troy ounce",
    }
    frame = frame.loc[~after_cutoff].reset_index(drop=True)
    if (
        frame.empty
        or frame.time.iloc[0] > pd.Timestamp("2007-01-01")
        or frame.time.iloc[-1] != CUTOFF
    ):
        raise ValueError("XAU/USD export lacks a required study boundary")
    return frame, audit


def normalize_annual_cpi(source: bytes) -> pd.DataFrame:
    """Extract WDI's reported annual inflation percentage, retaining its vintage."""
    prefix = "API_FP.CPI.TOTL.ZG_"
    with ZipFile(io.BytesIO(source)) as archive:
        names = [
            name
            for name in archive.namelist()
            if name.startswith(prefix) and name.endswith(".csv")
        ]
        if len(names) != 1:
            raise ValueError("Expected one World Bank annual inflation data CSV")
        rows = list(csv.reader(io.StringIO(archive.read(names[0]).decode("utf-8-sig"))))
    header = next(
        i for i, row in enumerate(rows) if row[:2] == ["Country Name", "Country Code"]
    )
    vintage = next(
        row[1] for row in rows[:header] if row and row[0] == "Last Updated Date"
    )
    series = [
        dict(zip(rows[header], row))
        for row in rows[header + 1 :]
        if row[1:2] == ["VNM"] and row[3:4] == ["FP.CPI.TOTL.ZG"]
    ]
    if len(series) != 1:
        raise ValueError("Expected one Vietnam annual inflation series")
    years = list(range(2005, CUTOFF.year))
    values = pd.to_numeric(
        pd.Series([series[0].get(str(year)) for year in years]), errors="raise"
    )
    if not np.isfinite(values).all():
        raise ValueError(
            "Vietnam annual inflation has missing or nonfinite values in 2005–2024"
        )
    return pd.DataFrame(
        {
            "year": years,
            "period_end": pd.to_datetime([f"{year}-12-31" for year in years]),
            "cpi_annual_inflation_pct": values,
            "publication_date": pd.NaT,
            "api_vintage": vintage,
        }
    )


def prepare_sources(gold_path: Path, cpi_path: Path) -> dict:
    gold, audit = normalize_gold(gold_path.read_bytes())
    cpi_bytes = cpi_path.read_bytes()
    cpi = normalize_annual_cpi(cpi_bytes)
    gdp_source = (DEST / "raw/worldbank_gdp.json").read_bytes()
    gdp = normalize_gdp(json.loads(gdp_source))
    if gdp.year.tolist() != cpi.year.tolist():
        raise ValueError("GDP and annual CPI must each cover 2005–2024")

    old_gold = pd.read_csv(RAW_DIR / "gold_xauusd_daily.csv", parse_dates=["time"])
    overlap = old_gold.merge(gold[["time", "close"]], on="time", validate="one_to_one")
    delta = (overlap.close - overlap.gold_usd_per_ounce).abs()
    prices = pd.read_csv(PRICE_PATH, usecols=["time"], parse_dates=["time"])
    dates = prices.loc[prices.time.le(CUTOFF), "time"]
    coverage = release_aware_asof(
        dates, gold[["time", "close"]], delay_days=1, max_age_days=10
    )
    weekdays = pd.date_range(gold.time.iloc[0], gold.time.iloc[-1], freq="B")
    audit.update(
        rows=len(gold),
        start=gold.time.iloc[0].strftime("%Y-%m-%d"),
        end=gold.time.iloc[-1].strftime("%Y-%m-%d"),
        largest_gap_calendar_days=int(gold.time.diff().dt.days.max()),
        weekday_dates_without_bar=weekdays.difference(gold.time)
        .strftime("%Y-%m-%d")
        .tolist(),
        overlap_rows=len(overlap),
        different_closes=int(delta.gt(1e-8).sum()),
        max_absolute_close_difference_usd=float(delta.max()),
        old_snapshot_dates_absent=old_gold.loc[~old_gold.time.isin(gold.time), "time"]
        .dt.strftime("%Y-%m-%d")
        .tolist(),
        fpt_sessions_checked=len(coverage),
        fpt_sessions_without_eligible_gold=int(coverage.close.isna().sum()),
        gold_availability_check={"delay_calendar_days": 1, "max_age_calendar_days": 10},
    )
    report = {
        "cutoff": CUTOFF.strftime("%Y-%m-%d"),
        "xau_usd": audit,
        "annual_cpi": {
            "source_url": CPI_URL,
            "source_sha256": hashlib.sha256(cpi_bytes).hexdigest(),
            "indicator": "FP.CPI.TOTL.ZG",
            "years": cpi.year.tolist(),
            "vintage": cpi.api_vintage.iloc[0],
            "verified_publication_dates": int(cpi.publication_date.notna().sum()),
        },
        "annual_gdp": {
            "indicator": "NY.GDP.MKTP.CD",
            "source_sha256": hashlib.sha256(gdp_source).hexdigest(),
            "years": gdp.year.tolist(),
            "verified_publication_dates": int(gdp.publication_date.notna().sum()),
        },
        "pipeline_status": "source_review_before_training",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, frame in {
        "gold_xauusd_ohlc.csv": gold,
        "gold_xauusd_daily.csv": gold[["time", "close"]].rename(
            columns={"close": "gold_usd_per_ounce"}
        ),
        "vietnam_cpi_annual.csv": cpi,
        "vietnam_gdp_annual.csv": gdp,
    }.items():
        frame.to_csv(OUTPUT / name, index=False, date_format="%Y-%m-%d")
    (OUTPUT / "audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-csv", type=Path, required=True)
    parser.add_argument("--cpi-zip", type=Path, required=True)
    args = parser.parse_args()
    prepare_sources(args.gold_csv, args.cpi_zip)
    print(f"Prepared local data and source audit in {OUTPUT}")
