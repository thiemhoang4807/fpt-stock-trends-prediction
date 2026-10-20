"""Fetch or normalize daily FPT OHLCV data and verify the project snapshot.

The upstream DS111 notebook uses ``vnstock.Quote`` with ``source="VCI"``.
This module keeps that provider optional so the modeling pipeline can still be
installed and run offline from the committed snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
SNAPSHOT_SHA256 = "263eced0cb25bc0380ed0dba7dc6f8d77b409146c7b4e2b1b0fd9f0ddbf25e98"
SNAPSHOT_ROWS = 4678
SNAPSHOT_FIRST_DATE = "2007-01-02"
SNAPSHOT_LAST_DATE = "2025-10-09"
CANONICAL_COLUMNS = ["time", "open", "high", "low", "close", "volume"]

_COLUMN_ALIASES = {
    "time": {"time", "date", "datetime", "timestamp", "tradingdate", "ngay", "ngaygiaodich"},
    "open": {"open", "openprice", "giamo", "giamocua"},
    "high": {"high", "highest", "highprice", "caonhat", "cao", "giacaonhat"},
    "low": {"low", "lowest", "lowprice", "thapnhat", "thap", "giathapnhat"},
    "close": {"close", "closeprice", "last", "lastprice", "lancuoi", "dongcua", "giadongcua"},
    "volume": {"volume", "vol", "matchvolume", "matchedvolume", "kl", "klgd", "klkhoplenh", "klgdkhoplenh", "khoiluong"},
}


class DataValidationError(ValueError):
    """Raised when an input does not meet the OHLCV data contract."""


def _fold_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("đ", "d")
    return re.sub(r"[^a-z0-9]", "", text)


def _sha256(path: Path) -> str:
    # Git stores text CSV with LF; normalize checkout CRLF so Linux/Windows
    # compute the same integrity hash for the same data rows.
    canonical_bytes = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(canonical_bytes).hexdigest()


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Map common API/widget CSV headers to sorted, canonical FPT OHLCV rows.

    Extra columns are discarded. If the export contains a symbol/ticker column,
    rows are restricted to FPT. Suspicious OHLC relationships are retained for
    audit because the original committed snapshot contains three such rows.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise DataValidationError("Dữ liệu đầu vào phải là DataFrame không rỗng.")

    aliases = {alias: canonical for canonical, names in _COLUMN_ALIASES.items() for alias in names}
    rename: dict[Any, str] = {}
    for column in frame.columns:
        folded = _fold_name(column)
        if folded in aliases:
            rename[column] = aliases[folded]

    data = frame.rename(columns=rename).copy()
    if "symbol" not in data.columns:
        for column in frame.columns:
            if _fold_name(column) in {"symbol", "ticker", "mack", "mck"}:
                data = data.rename(columns={column: "symbol"})
                break
    if "symbol" in data.columns:
        symbols = data["symbol"].astype(str).str.strip().str.upper()
        data = data.loc[symbols.eq("FPT")].copy()
        if data.empty:
            raise DataValidationError("Không tìm thấy dòng mã FPT trong tệp xuất.")

    missing = [column for column in CANONICAL_COLUMNS if column not in data.columns]
    if missing:
        raise DataValidationError(f"Thiếu cột OHLCV bắt buộc: {', '.join(missing)}")
    if any(list(data.columns).count(column) > 1 for column in CANONICAL_COLUMNS):
        raise DataValidationError("Tệp đầu vào có nhiều cột ánh xạ về cùng một trường OHLCV.")

    data = data[CANONICAL_COLUMNS].copy()
    raw_dates = data["time"].astype(str).str.strip()
    dates = pd.to_datetime(raw_dates, errors="coerce", format="ISO8601")
    non_iso = dates.isna()
    if non_iso.any():
        dates.loc[non_iso] = pd.to_datetime(raw_dates.loc[non_iso], errors="coerce", dayfirst=True)
    if dates.isna().any():
        raise DataValidationError(f"Cột ngày có {int(dates.isna().sum())} giá trị không đọc được.")
    data["time"] = dates.dt.strftime("%Y-%m-%d")

    for column in CANONICAL_COLUMNS[1:]:
        values = data[column].astype(str).str.strip().str.replace(",", "", regex=False)
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.isna().any() or not numeric.map(lambda value: pd.notna(value) and abs(value) != float("inf")).all():
            raise DataValidationError(f"Cột {column} chứa giá trị thiếu, vô hạn hoặc không phải số.")
        data[column] = numeric.astype(float)

    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataValidationError("Các giá OHLC phải lớn hơn 0.")
    if (data["volume"] < 0).any():
        raise DataValidationError("Khối lượng giao dịch không được âm.")
    if not (data["volume"] % 1 == 0).all():
        raise DataValidationError("Khối lượng phải là số nguyên.")
    data["volume"] = data["volume"].astype("int64")

    duplicates = data["time"].duplicated(keep=False)
    if duplicates.any():
        dates_found = data.loc[duplicates, "time"].unique().tolist()[:5]
        raise DataValidationError(f"Ngày giao dịch bị trùng, ví dụ: {dates_found}")

    data = data.sort_values("time", kind="stable").reset_index(drop=True)
    return data[CANONICAL_COLUMNS]


def audit_ohlcv(frame: pd.DataFrame) -> dict[str, Any]:
    """Summarize a canonical OHLCV table, including retained OHLC anomalies."""
    if list(frame.columns) != CANONICAL_COLUMNS:
        raise DataValidationError(f"Cột phải đúng thứ tự: {CANONICAL_COLUMNS}")
    canonical = normalize_ohlcv(frame)
    high_bad = canonical["high"] < canonical[["open", "close", "low"]].max(axis=1)
    low_bad = canonical["low"] > canonical[["open", "close", "high"]].min(axis=1)
    return {
        "rows": len(canonical),
        "first_date": canonical["time"].iloc[0],
        "last_date": canonical["time"].iloc[-1],
        "price_min": float(canonical[["open", "high", "low", "close"]].min().min()),
        "price_max": float(canonical[["open", "high", "low", "close"]].max().max()),
        "close_min": float(canonical["close"].min()),
        "close_max": float(canonical["close"].max()),
        "volume_min": int(canonical["volume"].min()),
        "volume_max": int(canonical["volume"].max()),
        "ohlc_inconsistent_rows": int((high_bad | low_bad).sum()),
    }


def verify_snapshot(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Verify schema, integrity summary, and exact snapshot bytes against baseline."""
    if not path.is_file():
        raise DataValidationError(f"Không tìm thấy snapshot: {path}")
    actual_digest = _sha256(path)
    if actual_digest != SNAPSHOT_SHA256:
        raise DataValidationError(
            "SHA-256 snapshot không khớp bản kiểm toán; dữ liệu đã thay đổi. "
            f"Mong đợi {SNAPSHOT_SHA256}, nhận được {actual_digest}."
        )
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        raise DataValidationError(f"Không đọc được snapshot CSV: {exc}") from exc
    if list(raw.columns) != CANONICAL_COLUMNS:
        raise DataValidationError(f"Schema snapshot sai: {raw.columns.tolist()}")
    summary = audit_ohlcv(raw)
    if summary["rows"] != SNAPSHOT_ROWS:
        raise DataValidationError(f"Số dòng sai: mong đợi {SNAPSHOT_ROWS}, nhận {summary['rows']}.")
    if (summary["first_date"], summary["last_date"]) != (SNAPSHOT_FIRST_DATE, SNAPSHOT_LAST_DATE):
        raise DataValidationError(
            f"Khoảng ngày sai: {summary['first_date']}–{summary['last_date']}.")
    summary["sha256"] = actual_digest
    summary["path"] = str(path)
    return summary


def download_via_vnstock(start: str, end: str) -> pd.DataFrame:
    """Reproduce the upstream API call: vnstock Quote, VCI source, daily FPT."""
    try:
        from vnstock import Quote
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài vnstock. Cài theo hướng dẫn ở README.md rồi chạy lại `--download`."
        ) from exc
    quote = Quote(symbol="FPT", source="VCI")
    result = quote.history(start=start, end=end, interval="1D")
    return normalize_ohlcv(result)


def _read_export(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp xuất: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def _write_csv(frame: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False, lineterminator="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tải, chuẩn hóa hoặc kiểm định snapshot OHLCV cổ phiếu FPT.",
        epilog=(
            "Ví dụ: python src/fetch_data.py --verify | "
            "python src/fetch_data.py --download --start 2007-01-01 --end 2025-10-09 "
            "--output data/raw/fpt/fpt_historical_price.csv | "
            "python src/fetch_data.py --input export.csv --output normalized.csv"
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true", help="Kiểm tra snapshot committed và SHA-256.")
    mode.add_argument("--download", action="store_true", help="Lấy dữ liệu từ vnstock/VCI.")
    mode.add_argument("--input", type=Path, help="Chuẩn hóa CSV đã xuất từ API/widget.")
    parser.add_argument("--start", default="2007-01-01", help="Ngày đầu cho --download (YYYY-MM-DD).")
    parser.add_argument("--end", default=date.today().isoformat(), help="Ngày cuối cho --download (YYYY-MM-DD).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="CSV đích cho --download/--input.")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        if args.verify:
            summary = verify_snapshot()
            print("SNAPSHOT VERIFIED — nội dung khớp chính xác baseline đã commit.")
            for key, value in summary.items():
                print(f"{key}: {value}")
            return 0

        if args.download:
            frame = download_via_vnstock(args.start, args.end)
        else:
            frame = normalize_ohlcv(_read_export(args.input))
        _write_csv(frame, args.output)
        summary = audit_ohlcv(frame)
        print(f"Đã ghi {summary['rows']} dòng vào {args.output}")
        print(
            f"Khoảng ngày {summary['first_date']}–{summary['last_date']}; "
            f"OHLC anomalies được giữ nguyên: {summary['ohlc_inconsistent_rows']} dòng."
        )
        if args.download:
            print("Lưu ý: dữ liệu VCI có thể được cập nhật/điều chỉnh lại; hãy kiểm tra hash và metrics trước khi thay snapshot nghiên cứu.")
        return 0
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
