"""Fetch, normalize, and verify daily FPT OHLCV data from VCI via vnstock."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
DEFAULT_START_DATE = "2007-01-01"
DEFAULT_END_DATE = "2025-09-30"
EXPECTED_FIRST_SESSION = "2007-01-02"
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
    """Map common API export headers to sorted, canonical FPT OHLCV rows.

    Extra columns are discarded. If the export contains a symbol/ticker column,
    rows are restricted to FPT. Suspicious OHLC relationships are retained for
    audit because the historical archive contains three such rows.
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


def verify_snapshot(
    path: Path = DEFAULT_OUTPUT,
    expected_last_date: str | None = DEFAULT_END_DATE,
) -> dict[str, Any]:
    """Validate the stored OHLCV dataset and its expected date coverage."""
    if not path.is_file():
        raise DataValidationError(f"Không tìm thấy snapshot: {path}")
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        raise DataValidationError(f"Không đọc được snapshot CSV: {exc}") from exc
    if list(raw.columns) != CANONICAL_COLUMNS:
        raise DataValidationError(f"Schema snapshot sai: {raw.columns.tolist()}")
    parsed_dates = pd.to_datetime(raw["time"], errors="coerce")
    if parsed_dates.isna().any():
        raise DataValidationError("Cột time trong snapshot có ngày không đọc được.")
    if not parsed_dates.is_monotonic_increasing:
        raise DataValidationError("Snapshot phải được sắp xếp tăng dần theo ngày.")
    summary = audit_ohlcv(raw)
    if summary["first_date"] != EXPECTED_FIRST_SESSION:
        raise DataValidationError(
            f"Ngày đầu sai: mong đợi {EXPECTED_FIRST_SESSION}, nhận {summary['first_date']}."
        )
    if expected_last_date and summary["last_date"] != expected_last_date:
        raise DataValidationError(
            f"Ngày cuối sai: mong đợi {expected_last_date}, nhận {summary['last_date']}."
        )
    summary["sha256"] = _sha256(path)
    summary["path"] = str(path)
    return summary


def merge_recent_with_archive(
    archive_path: Path,
    recent: pd.DataFrame,
    requested_start: str,
) -> tuple[pd.DataFrame, float, int]:
    """Extend an existing archive when the provider returns only a recent window.

    VCI revises historical OHLC after corporate actions. A stable price ratio in
    the overlap is applied to the older archive so both vintages share one basis.
    Volume is not scaled because it is not a price field.
    """
    if not archive_path.is_file():
        raise DataValidationError(
            "API chỉ trả một cửa sổ lịch sử gần đây và không tìm thấy archive cũ để nối. "
            "Cần cung cấp archive OHLCV từ ngày bắt đầu trước khi tải lại."
        )
    archive = normalize_ohlcv(_read_export(archive_path))
    archive_start = pd.Timestamp(archive["time"].iloc[0])
    requested_start_timestamp = pd.Timestamp(requested_start)
    if archive_start > requested_start_timestamp + pd.Timedelta(days=7):
        raise DataValidationError(
            f"Archive bắt đầu {archive['time'].iloc[0]}, sau ngày yêu cầu {requested_start}."
        )

    recent_start = recent["time"].iloc[0]
    overlap = archive.merge(recent, on="time", suffixes=("_archive", "_current"))
    if len(overlap) < 3:
        raise DataValidationError(
            "Không đủ ngày chồng lấn giữa archive và VCI để kiểm tra basis điều chỉnh giá."
        )

    ratios = np.concatenate(
        [
            (overlap[f"{column}_current"] / overlap[f"{column}_archive"]).to_numpy(dtype=float)
            for column in ("open", "high", "low", "close")
        ]
    )
    factor = float(np.median(ratios))
    relative_spread = float((ratios.max() - ratios.min()) / factor)
    if not np.isfinite(factor) or factor <= 0 or relative_spread > 0.005:
        raise DataValidationError(
            "Basis giá giữa archive và VCI không khớp theo một hệ số ổn định; "
            f"độ phân tán tương đối {relative_spread:.6%} vượt ngưỡng 0,5%. "
            "Không nối dữ liệu để tránh tạo chuỗi giá sai."
        )

    history = archive.loc[archive["time"] < recent_start].copy()
    history.loc[:, ["open", "high", "low", "close"]] *= factor
    combined = pd.concat([history, recent], ignore_index=True)
    combined = normalize_ohlcv(combined)
    return combined, factor, len(overlap)


def download_via_vnstock(start: str, end: str) -> pd.DataFrame:
    """Download daily FPT OHLCV directly from the VCI source using vnstock."""
    try:
        from vnstock import Quote
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài vnstock. Cài theo hướng dẫn ở README.md rồi chạy lại `--download`."
        ) from exc
    quote = Quote(symbol="FPT", source="VCI", show_log=False)
    result = quote.history(start=start, end=end, interval="1D")
    normalized = normalize_ohlcv(result)
    start_date = pd.Timestamp(start).strftime("%Y-%m-%d")
    end_date = pd.Timestamp(end).strftime("%Y-%m-%d")
    normalized = normalized.loc[
        normalized["time"].between(start_date, end_date, inclusive="both")
    ].reset_index(drop=True)
    if normalized.empty:
        raise DataValidationError(f"VCI không trả phiên giao dịch trong khoảng {start_date}–{end_date}.")
    return normalized


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
            "Mặc định tải dữ liệu 2007–2025-09-30. Ví dụ: python src/fetch_data.py | "
            "python src/fetch_data.py --verify | "
            "python src/fetch_data.py --download --start 2007-01-01 --end 2025-09-30 "
            "--output data/raw/fpt/fpt_historical_price.csv | "
            "python src/fetch_data.py --input export.csv --output normalized.csv"
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--verify", action="store_true", help="Kiểm tra schema, dữ liệu và khoảng ngày.")
    mode.add_argument("--download", action="store_true", help="Lấy dữ liệu từ vnstock/VCI.")
    mode.add_argument("--input", type=Path, help="Chuẩn hóa CSV OHLCV đã xuất từ một API.")
    parser.add_argument("--start", default=DEFAULT_START_DATE, help="Ngày đầu cho --download (YYYY-MM-DD).")
    parser.add_argument("--end", default=DEFAULT_END_DATE, help="Ngày cuối cho --download (YYYY-MM-DD).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="CSV đích cho --download/--input.")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        if args.verify:
            summary = verify_snapshot(args.output, expected_last_date=args.end)
            print("DATASET VERIFIED — schema, tính toàn vẹn và khoảng ngày hợp lệ.")
            for key, value in summary.items():
                print(f"{key}: {value}")
            return 0

        lineage_path = PROJECT_ROOT / "reports" / "data_lineage.json"
        prior_lineage = (
            json.loads(lineage_path.read_text(encoding="utf-8"))
            if lineage_path.is_file()
            else {}
        )
        previous_cumulative_factor = prior_lineage.get(
            "historical_archive_cumulative_price_factor",
            prior_lineage.get("price_adjustment_factor_applied_to_archive"),
        )
        adjustment_history = list(prior_lineage.get("historical_price_adjustment_history", []))
        if not adjustment_history:
            prior_factor = prior_lineage.get(
                "price_adjustment_factor_applied_this_run",
                prior_lineage.get("price_adjustment_factor_applied_to_archive"),
            )
            if prior_factor is None:
                prior_factor = previous_cumulative_factor
            if prior_factor is not None and not np.isclose(float(prior_factor), 1.0):
                adjustment_history.append(
                    {
                        "factor": float(prior_factor),
                        "api_window_start": prior_lineage.get("api_window_start"),
                        "overlap_rows": prior_lineage.get(
                            "overlap_rows_for_cumulative_price_factor",
                            prior_lineage.get("overlap_rows_used_for_adjustment_check")
                            if "price_adjustment_factor_applied_to_archive" in prior_lineage
                            else None,
                        ),
                    }
                )
        should_download = args.download or args.input is None
        if should_download:
            recent = download_via_vnstock(args.start, args.end)
            adjustment_factor = None
            overlap_rows = 0
            api_start = recent["time"].iloc[0]
            if pd.Timestamp(api_start) > pd.Timestamp(args.start) + pd.Timedelta(days=7):
                frame, adjustment_factor, overlap_rows = merge_recent_with_archive(
                    args.output, recent, args.start
                )
            else:
                frame = recent
            if args.end == DEFAULT_END_DATE and frame["time"].iloc[-1] != DEFAULT_END_DATE:
                raise DataValidationError(
                    f"VCI chưa trả phiên {DEFAULT_END_DATE}; không ghi đè tệp dữ liệu hiện có."
                )
        else:
            frame = normalize_ohlcv(_read_export(args.input))
            start_date = pd.Timestamp(args.start).strftime("%Y-%m-%d")
            end_date = pd.Timestamp(args.end).strftime("%Y-%m-%d")
            frame = frame.loc[frame["time"].between(start_date, end_date)].reset_index(drop=True)
            if frame.empty:
                raise DataValidationError(
                    f"Tệp đầu vào không có phiên giao dịch trong khoảng {start_date}–{end_date}."
                )
            adjustment_factor = None
            overlap_rows = 0
            api_start = None
        if adjustment_factor is not None and not np.isclose(adjustment_factor, 1.0):
            adjustment_history.append(
                {
                    "factor": adjustment_factor,
                    "api_window_start": api_start,
                    "overlap_rows": overlap_rows,
                }
            )
        _write_csv(frame, args.output)
        summary = audit_ohlcv(frame)
        cumulative_factor = None
        if adjustment_factor is not None:
            cumulative_factor = float(previous_cumulative_factor or 1.0) * adjustment_factor
        elif previous_cumulative_factor is not None:
            cumulative_factor = float(previous_cumulative_factor)
        lineage = {
            "provider": "VCI (Vietcap) via vnstock",
            "connector": "vnstock Quote.history, source=VCI",
            "requested_start": args.start,
            "requested_end": args.end,
            "api_window_start": api_start,
            "output_first_date": summary["first_date"],
            "output_last_date": summary["last_date"],
            "rows": summary["rows"],
            "price_adjustment_factor_applied_this_run": adjustment_factor,
            "historical_archive_cumulative_price_factor": cumulative_factor,
            "historical_price_adjustment_history": adjustment_history,
            "overlap_rows_for_cumulative_price_factor": (
                adjustment_history[-1]["overlap_rows"] if adjustment_history else None
            ),
            "overlap_rows_used_for_adjustment_check": overlap_rows,
            "price_columns_rebased": (
                ["open", "high", "low", "close"]
                if adjustment_factor is not None and not np.isclose(adjustment_factor, 1.0)
                else []
            ),
            "volume_rebased": False,
            "sha256": _sha256(args.output),
        }
        lineage_path.parent.mkdir(parents=True, exist_ok=True)
        lineage_path.write_text(json.dumps(lineage, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Đã ghi {summary['rows']} dòng vào {args.output}")
        print(
            f"Khoảng ngày {summary['first_date']}–{summary['last_date']}; "
            f"OHLC anomalies được giữ nguyên: {summary['ohlc_inconsistent_rows']} dòng."
        )
        if should_download:
            print("Nguồn: VCI qua vnstock; dữ liệu có thể được nhà cung cấp hiệu chỉnh lại theo sự kiện doanh nghiệp.")
            if adjustment_factor is not None:
                print(
                    f"Đã căn chỉnh archive theo hệ số {adjustment_factor:.8f}, "
                    f"tính từ {overlap_rows} phiên OHLC chồng lấn; xem reports/data_lineage.json."
                )
        return 0
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
