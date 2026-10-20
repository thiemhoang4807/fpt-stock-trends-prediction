from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fetch_data import DataValidationError, download_via_vnstock, normalize_ohlcv, verify_snapshot


def test_normalize_api_export_aliases_and_sorting():
    exported = pd.DataFrame(
        {
            "Date": ["2024-01-03", "2024-01-02"],
            "Giá mở cửa": ["21.0", "20.5"],
            "Cao nhất": ["22.0", "21.0"],
            "Thấp nhất": ["20.0", "20.0"],
            "Giá đóng cửa": ["21.5", "20.8"],
            "KL khớp lệnh": ["1,200", "900"],
            "Ticker": ["FPT", "FPT"],
            "Unused": ["x", "y"],
        }
    )

    result = normalize_ohlcv(exported)

    assert result.columns.tolist() == ["time", "open", "high", "low", "close", "volume"]
    assert result["time"].tolist() == ["2024-01-02", "2024-01-03"]
    assert result["volume"].tolist() == [900, 1200]
    assert result["open"].tolist() == [20.5, 21.0]


def test_normalize_rejects_duplicate_dates():
    frame = pd.DataFrame(
        {
            "time": ["2024-01-02", "2024-01-02"],
            "open": [20, 20], "high": [21, 21], "low": [19, 19],
            "close": [20, 20], "volume": [100, 100],
        }
    )
    with pytest.raises(DataValidationError, match="trùng"):
        normalize_ohlcv(frame)


def test_normalize_parses_day_first_dates_from_local_exports():
    frame = pd.DataFrame(
        {
            "Date": ["03/01/2024", "02/01/2024"],
            "open": [21, 20], "high": [22, 21], "low": [20, 19],
            "close": [21.5, 20.5], "volume": [1200, 900],
        }
    )
    result = normalize_ohlcv(frame)
    assert result["time"].tolist() == ["2024-01-02", "2024-01-03"]


@pytest.mark.parametrize(
    "column,values,match",
    [
        ("close", [None], "thiếu"),
        ("open", [-1], "lớn hơn 0"),
        ("volume", [-1], "không được âm"),
        ("volume", [1.5], "số nguyên"),
        ("time", ["not-a-date"], "ngày"),
    ],
)
def test_normalize_rejects_invalid_values(column, values, match):
    row = {
        "time": ["2024-01-02"], "open": [20], "high": [21],
        "low": [19], "close": [20], "volume": [100],
    }
    row[column] = values
    with pytest.raises(DataValidationError, match=match):
        normalize_ohlcv(pd.DataFrame(row))


def test_snapshot_matches_locked_upstream_copy():
    project_root = Path(__file__).resolve().parents[1]
    summary = verify_snapshot(project_root / "data" / "raw" / "fpt" / "fpt_historical_price.csv")
    assert summary["rows"] == 4678
    assert summary["first_date"] == "2007-01-02"
    assert summary["last_date"] == "2025-10-09"
    assert summary["ohlc_inconsistent_rows"] == 3


def test_vnstock_download_uses_upstream_quote_and_normalizes(monkeypatch):
    calls = {}

    class FakeQuote:
        def __init__(self, **kwargs):
            calls["constructor"] = kwargs

        def history(self, **kwargs):
            calls["history"] = kwargs
            return pd.DataFrame(
                {
                    "time": ["2025-10-09"], "open": [95], "high": [96],
                    "low": [93], "close": [94.2], "volume": [5716300],
                }
            )

    monkeypatch.setitem(sys.modules, "vnstock", SimpleNamespace(Quote=FakeQuote))
    result = download_via_vnstock("2007-01-01", "2025-10-09")

    assert calls["constructor"] == {"symbol": "FPT", "source": "VCI"}
    assert calls["history"] == {"start": "2007-01-01", "end": "2025-10-09", "interval": "1D"}
    assert result.loc[0, "close"] == 94.2
