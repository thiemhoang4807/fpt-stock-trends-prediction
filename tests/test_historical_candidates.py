"""Historical imports must preserve dates, units and unknown publication dates."""

import json
import lzma
from pathlib import Path
import struct
from urllib.error import HTTPError

import numpy as np
import pandas as pd
import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import fetch_historical_candidates as history


def cpi_payload():
    records = [
        {
            "countryiso3code": "",
            "country": {"id": "VNM"},
            "indicator": {"id": "CPTOTNSXN"},
            "date": str(p).replace("-", "M"),
            "value": 100.0 + i,
        }
        for i, p in enumerate(pd.period_range("2006-01", periods=24, freq="M"))
    ]
    return [{"total": 24, "lastupdated": "2026-09-08"}, records[::-1]]


def test_cpi_computes_same_month_year_ago_without_inventing_release_dates():
    frame = history.normalize_cpi(cpi_payload())
    assert frame.cpi_yoy_pct.iloc[:12].isna().all()
    assert frame.cpi_yoy_pct.iloc[12] == pytest.approx(12.0)
    assert frame.period.iloc[12] == "2007-01"
    assert frame.publication_date.isna().all()
    assert frame.publication_status.eq("unverified").all()


@pytest.mark.parametrize(
    "problem", ["gap", "duplicate", "country", "indicator", "null", "pagination"]
)
def test_cpi_rejects_inputs_that_would_silently_corrupt_inflation(problem):
    payload = cpi_payload()
    if problem == "gap":
        payload[1].pop(5)
        payload[0]["total"] -= 1
    elif problem == "duplicate":
        payload[1][0]["date"] = payload[1][1]["date"]
    elif problem == "country":
        payload[1][0]["country"]["id"] = "USA"
    elif problem == "indicator":
        payload[1][0]["indicator"]["id"] = "FP.CPI.TOTL.ZG"
    elif problem == "null":
        payload[1][0]["value"] = None
    else:
        payload[0]["total"] = 100
    with pytest.raises(ValueError):
        history.normalize_cpi(payload)


def test_gold_decoding_preserves_ohlc_order_scale_and_availability():
    real = struct.pack(">5If", 0, 600000, 601000, 599000, 602000, 2.0)
    filler = struct.pack(">5If", 86400, 601000, 601000, 601000, 601000, 0.0)
    frame, audit = history.decode_gold(lzma.compress(real + filler), 2007)
    assert frame.iloc[0][["open", "high", "low", "close"]].tolist() == [
        600,
        602,
        599,
        601,
    ]
    assert frame.bar_complete_at_utc.iloc[0] == "2007-01-02T00:00:00Z"
    assert audit["flat_fillers_removed"] == 1
    assert len(frame) == 1


@pytest.mark.parametrize(
    "problem", ["length", "duplicate", "ohlc", "time", "nonfinite"]
)
def test_gold_rejects_corrupt_bars(problem):
    values = [0, 600000, 601000, 599000, 602000, 1.0]
    if problem == "ohlc":
        values[3] = 603000
    elif problem == "time":
        values[0] = 3600
    elif problem == "nonfinite":
        values[-1] = np.nan
    body = struct.pack(">5If", *values)
    if problem == "length":
        body += b"x"
    elif problem == "duplicate":
        body *= 2
    with pytest.raises(ValueError):
        history.decode_gold(lzma.compress(body), 2007)


def test_gdp_snapshot_is_annual_and_does_not_claim_release_dates():
    payload = json.loads((history.DEST / "raw/worldbank_gdp.json").read_text())
    frame = history.normalize_gdp(payload)
    assert frame.year.tolist() == list(range(2005, 2025))
    assert frame.publication_date.isna().all()
    assert frame.loc[frame.year.eq(2007), "gdp_usd"].iloc[0] == pytest.approx(
        77414425532.2452
    )


def test_gold_cutoff_excludes_future_bars_and_reports_incomplete_year():
    start = pd.Timestamp("2025-01-01")
    body = b"".join(
        struct.pack(
            ">5If",
            int((pd.Timestamp(day) - start).total_seconds()),
            600000,
            601000,
            599000,
            602000,
            1.0,
        )
        for day in ["2025-09-30", "2025-10-01"]
    )
    frame, audit = history.decode_gold(lzma.compress(body), 2025)
    assert frame.time.tolist() == [pd.Timestamp("2025-09-30")]
    assert frame.bar_complete_at_utc.iloc[0] == "2025-10-01T00:00:00Z"
    assert audit["missing_calendar_days_before_cutoff"] == 272


def test_download_keeps_cached_sources_and_stops_host_after_429(tmp_path, monkeypatch):
    for name in history.SOURCE_URLS:
        (tmp_path / name).write_bytes(b"keep cached data")
    requested = []

    def rate_limited(request, timeout):
        requested.append(request.full_url)
        raise HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(history, "urlopen", rate_limited)
    records = history.download_missing(tmp_path, [2007, 2008])
    assert len(requested) == 1
    assert records[0]["status"] == 429
    assert "Skipped" in records[1]["error"]
    assert all(
        (tmp_path / n).read_bytes() == b"keep cached data" for n in history.SOURCE_URLS
    )
