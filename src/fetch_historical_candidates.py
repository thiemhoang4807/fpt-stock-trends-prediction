"""Fetch and audit historical candidates separately from training snapshots.

Default: rebuild the research CSVs offline from the archived source responses.
--download: fetch missing responses; a provider returning HTTP 429 is not retried
in that run. Reference periods are never labelled as verified release dates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import struct
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from fetch_supplemental import normalize_vnindex_response

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/research/history_2007"
CUTOFF = pd.Timestamp("2025-09-30")
SOURCE_URLS = {
    "worldbank_cpi_gem.json": "https://api.worldbank.org/v2/country/VNM/indicator/CPTOTNSXN?source=15&date=2005M01:2025M09&format=json&per_page=1000",
    "worldbank_gdp.json": "https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.CD?date=2005:2024&format=json&per_page=100",
}


def worldbank_records(payload: list, indicator: str) -> tuple[dict, list]:
    """Reject wrong indicators/countries, API errors and truncated pagination."""
    if not isinstance(payload, list) or len(payload) != 2:
        raise ValueError("Expected a World Bank metadata/data response")
    metadata, records = payload
    if not records or int(metadata.get("total", -1)) != len(records):
        raise ValueError("Missing records or incomplete API pagination")
    if any(
        (r.get("countryiso3code") or r.get("country", {}).get("id")) != "VNM"
        or r.get("indicator", {}).get("id") != indicator
        for r in records
    ):
        raise ValueError("Unexpected country or indicator")
    return metadata, records


def normalize_cpi(payload: list) -> pd.DataFrame:
    """Calculate monthly year-on-year inflation only on a complete calendar."""
    metadata, records = worldbank_records(payload, "CPTOTNSXN")
    frame = (
        pd.DataFrame(
            {
                "period": [r["date"].replace("M", "-") for r in records],
                "cpi_index": [r["value"] for r in records],
            }
        )
        .sort_values("period")
        .reset_index(drop=True)
    )
    periods = pd.PeriodIndex(frame["period"], freq="M")
    expected = pd.period_range(periods.min(), periods.max(), freq="M")
    if periods.has_duplicates or not periods.equals(expected):
        raise ValueError("CPI has duplicate or missing reference months")
    values = pd.to_numeric(frame.cpi_index, errors="raise")
    if not np.isfinite(values).all() or values.le(0).any():
        raise ValueError("CPI indices must be finite and positive")
    frame["cpi_index"] = values
    frame["cpi_yoy_pct"] = 100 * (values / values.shift(12) - 1)
    frame["period_end"] = periods.to_timestamp(how="end").normalize()
    frame["publication_date"] = pd.NaT
    frame["publication_status"] = "unverified"
    frame["api_vintage"] = metadata.get("lastupdated", "unknown")
    return frame.loc[frame.period_end.le(CUTOFF)].reset_index(drop=True)


def normalize_gdp(payload: list) -> pd.DataFrame:
    """Keep annual nominal USD GDP distinct from GDP growth or quarterly GDP."""
    metadata, records = worldbank_records(payload, "NY.GDP.MKTP.CD")
    frame = (
        pd.DataFrame(
            {
                "year": [int(r["date"]) for r in records],
                "gdp_usd": [r["value"] for r in records],
            }
        )
        .sort_values("year")
        .reset_index(drop=True)
    )
    if frame.year.duplicated().any() or frame.year.diff().dropna().ne(1).any():
        raise ValueError("GDP has duplicate or missing years")
    frame["gdp_usd"] = pd.to_numeric(frame.gdp_usd, errors="raise")
    if not np.isfinite(frame.gdp_usd).all() or frame.gdp_usd.le(0).any():
        raise ValueError("GDP must be finite and positive")
    frame["period_end"] = pd.to_datetime(frame.year.astype(str) + "-12-31")
    frame["publication_date"] = pd.NaT
    frame["publication_status"] = "unverified"
    frame["api_vintage"] = metadata.get("lastupdated", "unknown")
    return frame.loc[frame.period_end.le(CUTOFF)].reset_index(drop=True)


def decode_gold(content: bytes, year: int) -> tuple[pd.DataFrame, dict]:
    """Decode Dukascopy legacy BID daily bars (UTC, USD/ounce, factor 1,000).

    Record order is seconds/open/close/low/high/activity, not standard OHLC.
    Flat zero-activity calendar fillers are excluded; real Sunday bars remain.
    """
    body = lzma.decompress(content)
    if not body or len(body) % 24:
        raise ValueError("Gold binary payload is empty or has an invalid length")
    frame = pd.DataFrame(
        struct.iter_unpack(">5If", body),
        columns=[
            "seconds",
            "open",
            "close",
            "low",
            "high",
            "provider_activity",
        ],
    )
    frame["time"] = pd.Timestamp(year, 1, 1) + pd.to_timedelta(frame.seconds, unit="s")
    if (
        frame.time.dt.year.ne(year).any()
        or frame.seconds.mod(86400).ne(0).any()
        or frame.time.duplicated().any()
    ):
        raise ValueError("Invalid daily offsets or duplicate gold bars")
    frame[["open", "high", "low", "close"]] /= 1000.0
    numeric = frame[["open", "high", "low", "close", "provider_activity"]]
    if (
        not np.isfinite(numeric).all().all()
        or frame[["open", "high", "low", "close"]].le(0).any().any()
        or frame.provider_activity.lt(0).any()
        or frame.low.gt(frame[["open", "close"]].min(axis=1)).any()
        or frame.high.lt(frame[["open", "close"]].max(axis=1)).any()
    ):
        raise ValueError("Gold bars contain invalid numeric/OHLC values")
    filler = frame.provider_activity.eq(0) & frame.high.eq(frame.low)
    audit = {
        "year": year,
        "calendar_records": len(frame),
        "flat_fillers_removed": int(filler.sum()),
    }
    expected = pd.date_range(
        pd.Timestamp(year, 1, 1), min(pd.Timestamp(year, 12, 31), CUTOFF)
    )
    audit["missing_calendar_days_before_cutoff"] = len(expected.difference(frame.time))
    frame = frame.loc[~filler & frame.time.le(CUTOFF)].sort_values("time").copy()
    # UTC daily close becomes available only after this boundary (07:00 in VN).
    frame["bar_complete_at_utc"] = (frame.time + pd.Timedelta(days=1)).dt.strftime(
        "%Y-%m-%dT00:00:00Z"
    )
    audit["retained_records"] = len(frame)
    return frame.drop(columns="seconds").reset_index(drop=True), audit


def download_missing(raw: Path, gold_years: list[int]) -> list[dict]:
    """Archive responses and hashes; stop requests to a rate-limited provider."""
    urls = dict(SOURCE_URLS)
    urls.update(
        {
            f"gold_dukascopy_{y}.bi5": f"https://datafeed.dukascopy.com/datafeed/XAUUSD/{y}/BID_candles_day_1.bi5"
            for y in gold_years
        }
    )
    raw.mkdir(parents=True, exist_ok=True)
    records, blocked_hosts = [], set()
    for name, url in urls.items():
        if (raw / name).exists():
            continue
        host = urlparse(url).netloc
        record = {
            "file": name,
            "url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        if host in blocked_hosts:
            record["error"] = "Skipped: provider returned HTTP 429 earlier in this run"
        else:
            try:
                with urlopen(
                    Request(url, headers={"User-Agent": "CS114-data-research/1.0"}),
                    timeout=25,
                ) as response:
                    body = response.read()
                if name.endswith(".bi5"):
                    decode_gold(body, int(name.split("_")[-1].split(".")[0]))
                elif "cpi" in name:
                    normalize_cpi(json.loads(body))
                else:
                    normalize_gdp(json.loads(body))
                (raw / name).write_bytes(body)
                record.update(
                    status=200, bytes=len(body), sha256=hashlib.sha256(body).hexdigest()
                )
            except HTTPError as exc:
                record.update(status=exc.code, error=str(exc))
                if exc.code == 429:
                    blocked_hosts.add(host)
            except (URLError, TimeoutError, OSError, ValueError, lzma.LZMAError) as exc:
                record["error"] = str(exc)
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    return records


def compare_sources(
    cpi: pd.DataFrame, gdp: pd.DataFrame, gold: pd.DataFrame, dest: Path
) -> dict:
    """Compare overlaps without interpreting small discrepancies as equality."""
    old_dir = ROOT / "data/raw/supplemental"
    old_cpi = pd.read_csv(old_dir / "vietnam_cpi.csv", parse_dates=["time"])
    # Diagnostic heuristic only: early-month releases refer to the prior month.
    period = old_cpi.time.dt.to_period("M")
    period.loc[old_cpi.time.dt.day.le(15)] -= 1
    old_cpi["period"] = period.astype(str)
    joined = old_cpi.merge(
        cpi[["period", "cpi_yoy_pct"]], on="period", suffixes=("_current", "_candidate")
    )
    joined["difference_percentage_points"] = (
        joined.cpi_yoy_pct_candidate - joined.cpi_yoy_pct_current
    )
    joined.to_csv(dest / "cpi_overlap_diagnostic.csv", index=False)
    old_gdp = pd.read_csv(old_dir / "vietnam_gdp.csv", parse_dates=["time"])
    old_gdp["year"] = old_gdp.time.dt.year
    gd = old_gdp.merge(gdp, on="year", suffixes=("_current", "_candidate"))
    gd["relative_difference_pct"] = 100 * (
        gd.gdp_usd_candidate / gd.gdp_usd_current - 1
    )
    gd[
        ["year", "gdp_usd_current", "gdp_usd_candidate", "relative_difference_pct"]
    ].to_csv(dest / "gdp_overlap.csv", index=False)
    gold_stats = {"rows": 0}
    if not gold.empty:
        old_gold = pd.read_csv(old_dir / "gold_xauusd_daily.csv", parse_dates=["time"])
        go = old_gold.merge(gold[["time", "close"]], on="time")
        go["relative_difference_pct"] = 100 * (go.close / go.gold_usd_per_ounce - 1)
        go.to_csv(dest / "gold_overlap.csv", index=False)
        if len(go):
            gold_stats = {
                "rows": len(go),
                "mean_absolute_relative_difference_pct": float(
                    go.relative_difference_pct.abs().mean()
                ),
                "max_absolute_relative_difference_pct": float(
                    go.relative_difference_pct.abs().max()
                ),
            }
    return {
        "cpi": {
            "rows": len(joined),
            "max_absolute_difference_percentage_points": float(
                joined.difference_percentage_points.abs().max()
            ),
            "reference_period_status": "inferred for diagnostic only; not verified publication history",
        },
        "gdp": {
            "rows": len(gd),
            "max_absolute_relative_difference_pct": float(
                gd.relative_difference_pct.abs().max()
            ),
        },
        "gold": gold_stats,
    }


def build_candidates(dest: Path = DEST) -> dict:
    """Write only research outputs. No training or production files are changed."""
    raw = dest / "raw"
    cpi = normalize_cpi(
        json.loads((raw / "worldbank_cpi_gem.json").read_text(encoding="utf-8"))
    )
    gdp = normalize_gdp(
        json.loads((raw / "worldbank_gdp.json").read_text(encoding="utf-8"))
    )
    cpi.to_csv(dest / "cpi_monthly_index.csv", index=False, date_format="%Y-%m-%d")
    cpi.loc[cpi.cpi_yoy_pct.notna()].to_csv(
        dest / "cpi_monthly_yoy.csv", index=False, date_format="%Y-%m-%d"
    )
    gdp.to_csv(dest / "gdp_annual.csv", index=False, date_format="%Y-%m-%d")
    frames, gold_audit = [], []
    for path in sorted(raw.glob("gold_dukascopy_*.bi5")):
        frame, audit = decode_gold(path.read_bytes(), int(path.stem.split("_")[-1]))
        frames.append(frame)
        gold_audit.append(audit)
    gold = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not gold.empty:
        gold.to_csv(
            dest / "gold_daily_partial.csv", index=False, date_format="%Y-%m-%d"
        )
    years = [a["year"] for a in gold_audit]
    missing_gold_years = sorted(set(range(2007, 2026)) - set(years))
    gold_incomplete = bool(missing_gold_years) or any(
        a["missing_calendar_days_before_cutoff"] for a in gold_audit
    )
    report = {
        "status": "research_candidates_not_training_inputs",
        "cutoff": str(CUTOFF.date()),
        "cpi": {
            "index_months": len(cpi),
            "yoy_months": int(cpi.cpi_yoy_pct.notna().sum()),
            "first_month": cpi.period.iloc[0],
            "last_month": cpi.period.iloc[-1],
            "missing_reference_months": 0,
            "verified_publication_dates": 0,
            "vintage": str(cpi.api_vintage.iloc[0]),
        },
        "gdp": {
            "years": len(gdp),
            "first_year": int(gdp.year.min()),
            "last_year": int(gdp.year.max()),
            "verified_publication_dates": 0,
            "vintage": str(gdp.api_vintage.iloc[0]),
        },
        "gold": {
            "downloaded_years": years,
            "missing_year_files_2007_2025": missing_gold_years,
            "retained_rows": len(gold),
            "by_year": gold_audit,
            "basis": "Dukascopy XAU/USD BID, USD per ounce, UTC daily bars; differs from existing Investing close",
        },
        "overlap": compare_sources(cpi, gdp, gold, dest),
        "ready_to_replace_training_dataset": False,
        "blockers": (["Gold year files incomplete"] if gold_incomplete else [])
        + [
            "CPI/GDP historical publication dates and first-release vintages unverified",
            "Quarterly financial gap and shares chronology not fully reconstructed",
        ],
        "source_hashes": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(raw.iterdir())
            if p.is_file()
        },
    }
    vn_path = raw / "vnindex_refresh.json"
    if vn_path.exists():
        vn = normalize_vnindex_response(
            json.loads(vn_path.read_text()), "2007-01-01", str(CUTOFF.date())
        )
        fpt = pd.read_csv(
            ROOT / "data/raw/fpt/fpt_historical_price.csv", parse_dates=["time"]
        )
        old = pd.read_csv(
            ROOT / "data/raw/supplemental/vnindex_source.csv", parse_dates=["time"]
        )
        joined = vn.merge(old, on="time", suffixes=("_candidate", "_current"))
        missing = sorted(set(fpt.time) - set(vn.time))
        report["vnindex_refresh"] = {
            "rows": len(vn),
            "missing_fpt_sessions": [str(x.date()) for x in missing],
            "new_dates": len(set(vn.time) - set(old.time)),
            "max_absolute_close_change": float(
                (joined.close_candidate - joined.close_current).abs().max()
            ),
        }
    (dest / "audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download missing research responses; never overwrite cached files",
    )
    parser.add_argument(
        "--gold-years", type=int, nargs="*", default=[], choices=range(2005, 2026)
    )
    args = parser.parse_args()
    if args.gold_years and not args.download:
        parser.error("--gold-years requires --download")
    DEST.mkdir(parents=True, exist_ok=True)
    if args.download:
        records = download_missing(DEST / "raw", args.gold_years)
        path = DEST / "download_history.json"
        history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        path.write_text(
            json.dumps(history + records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    report = build_candidates()
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "status",
                    "cpi",
                    "gdp",
                    "gold",
                    "overlap",
                    "ready_to_replace_training_dataset",
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
