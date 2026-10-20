from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fetch_data import (
    DataValidationError,
    download_via_vnstock,
    main,
    merge_recent_with_archive,
    normalize_ohlcv,
    verify_snapshot,
)


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


def test_verify_snapshot_checks_schema_and_requested_date_coverage():
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp_dir:
        path = Path(temp_dir) / "prices.csv"
        pd.DataFrame(
            {
                "time": ["2007-01-02", "2026-09-30"],
                "open": [10.0, 63.4], "high": [11.0, 64.0],
                "low": [9.0, 63.0], "close": [10.5, 63.0],
                "volume": [1000, 3_063_973],
            }
        ).to_csv(path, index=False)

        summary = verify_snapshot(path)

        assert summary["rows"] == 2
        assert summary["first_date"] == "2007-01-02"
        assert summary["last_date"] == "2026-09-30"
        assert len(summary["sha256"]) == 64


def test_verify_snapshot_rejects_wrong_end_date():
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp_dir:
        path = Path(temp_dir) / "prices.csv"
        pd.DataFrame(
            {
                "time": ["2007-01-02", "2026-09-29"],
                "open": [10.0, 63.7], "high": [11.0, 64.1],
                "low": [9.0, 63.1], "close": [10.5, 63.2],
                "volume": [1000, 3_141_350],
            }
        ).to_csv(path, index=False)

        with pytest.raises(DataValidationError, match="Ngày cuối sai"):
            verify_snapshot(path)


def test_recent_window_extends_archive_on_stable_provider_rebase():
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp_dir:
        archive_path = Path(temp_dir) / "archive.csv"
        archive = pd.DataFrame(
            {
                "time": ["2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30"],
                "open": [100, 101, 102, 103, 104],
                "high": [101, 102, 103, 104, 105],
                "low": [99, 100, 101, 102, 103],
                "close": [100.5, 101.5, 102.5, 103.5, 104.5],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )
        archive.to_csv(archive_path, index=False)
        recent = archive.iloc[2:].copy()
        recent[["open", "high", "low", "close"]] *= 0.9
        recent = pd.concat(
            [
                recent,
                pd.DataFrame(
                    {
                        "time": ["2026-10-01"], "open": [94.5], "high": [95.4],
                        "low": [93.6], "close": [94.8], "volume": [1500],
                    }
                ),
            ],
            ignore_index=True,
        )

        merged, factor, overlap_rows = merge_recent_with_archive(archive_path, recent, "2026-09-24")

        assert factor == pytest.approx(0.9)
        assert overlap_rows == 3
        assert merged["time"].is_monotonic_increasing
        assert not merged["time"].duplicated().any()
        assert merged["time"].iloc[0] == "2026-09-24"
        assert merged["time"].iloc[-1] == "2026-10-01"
        assert merged.loc[0, "close"] == pytest.approx(90.45)


def test_vnstock_download_uses_vci_quote_and_normalizes(monkeypatch):
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

    assert calls["constructor"] == {"symbol": "FPT", "source": "VCI", "show_log": False}
    assert calls["history"] == {"start": "2007-01-01", "end": "2025-10-09", "interval": "1D"}
    assert result.loc[0, "close"] == 94.2


def test_no_mode_defaults_to_download_through_september_cutoff(monkeypatch):
    import fetch_data

    with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp_dir:
        tmp_path = Path(temp_dir)
        monkeypatch.setattr(fetch_data, "PROJECT_ROOT", tmp_path)
        calls = {}

        def fake_download(start, end):
            calls["dates"] = (start, end)
            return pd.DataFrame(
                {
                    "time": ["2007-01-02", "2026-09-30"],
                    "open": [10.0, 63.4], "high": [11.0, 64.0],
                    "low": [9.0, 63.0], "close": [10.5, 63.0],
                    "volume": [1000, 3_063_973],
                }
            )

        monkeypatch.setattr(fetch_data, "download_via_vnstock", fake_download)
        output = tmp_path / "fpt.csv"

        assert main(["--output", str(output)]) == 0
        assert calls["dates"] == ("2007-01-01", "2026-09-30")
        assert pd.read_csv(output)["time"].iloc[-1] == "2026-09-30"
        assert (tmp_path / "reports" / "data_lineage.json").is_file()
