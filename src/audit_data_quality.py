"""Read-only source review: coverage, internal gaps and accounting consistency.

Writes a separate review report; never fills inputs or changes experiment artefacts.
Calendar differences are candidates for source verification, not proof of bad data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "fpt": "data/raw/fpt/fpt_historical_price.csv",
    "vnindex": "data/raw/supplemental/vnindex_source.csv",
    "usd_vnd": "data/raw/supplemental/usd_vnd_daily.csv",
    "gold": "data/raw/supplemental/gold_xauusd_daily.csv",
    "cpi": "data/raw/supplemental/vietnam_cpi.csv",
    "gdp": "data/raw/supplemental/vietnam_gdp.csv",
    "financial": "data/raw/supplemental/fpt_fundamentals_quarterly.csv",
    "shares": "data/raw/supplemental/fpt_shares_outstanding.csv",
}


def missing_runs(dates: pd.Series, missing: pd.Series) -> list[dict]:
    """Describe consecutive missing rows on the supplied FPT session calendar."""
    missing = missing.reset_index(drop=True).astype(bool)
    dates = pd.to_datetime(dates).reset_index(drop=True)
    groups = missing.ne(missing.shift(fill_value=False)).cumsum()
    runs = []
    for _, positions in missing.loc[missing].groupby(groups[missing]).groups.items():
        first, last = int(positions[0]), int(positions[-1])
        runs.append({
            "first_session": str(dates.iloc[first].date()),
            "last_session": str(dates.iloc[last].date()),
            "rows": len(positions),
            "position": "leading" if first == 0 else "trailing" if last == len(dates) - 1 else "internal",
        })
    return runs


def review(root: Path = ROOT) -> dict:
    """Audit existing raw and aligned files without modifying those files."""
    frames = {}
    sources = {}
    hashes = {}
    for name, relative in SOURCES.items():
        path = root / relative
        frame = pd.read_csv(path)
        dates = pd.to_datetime(frame["time"], errors="coerce")
        numeric = frame.select_dtypes(include="number")
        sources[name] = {
            "file": relative,
            "rows": len(frame),
            "first_date": str(dates.min().date()),
            "last_date": str(dates.max().date()),
            "invalid_dates": int(dates.isna().sum()),
            "duplicate_dates": int(dates.duplicated().sum()),
            "ascending_dates": bool(dates.is_monotonic_increasing),
            "nulls_by_column": {c: int(n) for c, n in frame.isna().sum().items()},
            "nonfinite_numeric_values": int((~np.isfinite(numeric)).sum().sum()),
        }
        frame["time"] = dates
        frames[name] = frame.sort_values("time").reset_index(drop=True)
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()

    fpt, vn = frames["fpt"], frames["vnindex"]
    invalid_ohlc = (fpt.low > fpt[["open", "close"]].min(axis=1)) | (
        fpt.high < fpt[["open", "close"]].max(axis=1)
    ) | (fpt.low > fpt.high)
    ohlc_rows = fpt.loc[invalid_ohlc].copy()
    ohlc_rows["time"] = ohlc_rows.time.dt.strftime("%Y-%m-%d")
    dates_fpt, dates_vn = set(fpt.time), set(vn.time)
    fpt_only = sorted(dates_fpt - dates_vn)
    vn_only = sorted(dates_vn - dates_fpt)

    # A difference between calendars is recorded, not filled or labelled a holiday.
    vn_intervals = []
    for prior, current in zip(vn.time.iloc[:-1], vn.time.iloc[1:]):
        skipped = [d for d in fpt_only if prior < d < current]
        if skipped:
            vn_intervals.append({
                "previous_source_date": str(prior.date()),
                "source_date": str(current.date()),
                "fpt_dates_between": [str(d.date()) for d in skipped],
                "interpretation": "Return across adjacent source rows spans multiple FPT-calendar sessions; verify source and exchange calendar.",
            })

    aligned_path = root / "data/processed/fpt_multisource_features.csv"
    aligned = pd.read_csv(aligned_path, parse_dates=["date"])
    if not aligned.date.reset_index(drop=True).equals(fpt.time.reset_index(drop=True)):
        raise ValueError("Aligned data must use the same ordered FPT dates")
    coverage = {}
    for column in MODEL_SUPPLEMENTAL_COLUMNS:
        missing = aligned[column].isna()
        valid_dates = aligned.loc[~missing, "date"]
        runs = missing_runs(aligned.date, missing)
        coverage[column] = {
            "first_valid_session": str(valid_dates.min().date()) if len(valid_dates) else None,
            "last_valid_session": str(valid_dates.max().date()) if len(valid_dates) else None,
            "missing_rows": int(missing.sum()),
            "missing_pct": float(missing.mean() * 100),
            "internal_missing_rows": sum(r["rows"] for r in runs if r["position"] == "internal"),
            "missing_runs": runs,
        }
    hashes[str(aligned_path.relative_to(root)).replace("\\", "/")] = hashlib.sha256(aligned_path.read_bytes()).hexdigest()

    # Missing reporting quarters differ from blank numeric cells in observed rows.
    quarters = frames["financial"].time.dt.to_period("Q")
    expected_quarters = pd.period_range(quarters.min(), quarters.max(), freq="Q")
    absent_quarters = expected_quarters.difference(pd.PeriodIndex(quarters))
    financial_path = root / "data/raw/supplemental/fpt_income_statement_source.csv"
    financial = pd.read_csv(financial_path)
    hashes[str(financial_path.relative_to(root)).replace("\\", "/")] = hashlib.sha256(financial_path.read_bytes()).hexdigest()
    checks = {
        "net_revenue_equals_sales_plus_signed_deductions": (
            financial["Doanh thu bán hàng và cung cấp dịch vụ"] + financial["Các khoản giảm trừ doanh thu"], financial["Doanh thu thuần"]
        ),
        "gross_profit_equals_net_revenue_plus_signed_cost": (
            financial["Doanh thu thuần"] + financial["Giá vốn hàng bán"], financial["Lãi gộp"]
        ),
        "net_profit_equals_parent_plus_noncontrolling": (
            financial["Cổ đông của Công ty mẹ"] + financial["Cổ đông thiểu số"], financial["Lợi nhuận thuần"]
        ),
    }
    accounting = {}
    for name, (expected, observed) in checks.items():
        residual = (expected - observed).abs()
        accounting[name] = {"max_absolute_residual_vnd": float(residual.max()), "rows_residual_over_1_vnd": int(residual.gt(1).sum())}

    return {
        "scope": "Structural and internal consistency of existing snapshots; no independent certification of vendor values or release dates.",
        "cutoff": "2025-09-30",
        "source_files": sources,
        "fpt_ohlc_violations": ohlc_rows.to_dict(orient="records"),
        "fpt_zero_volume_dates": fpt.loc[fpt.volume.eq(0), "time"].dt.strftime("%Y-%m-%d").tolist(),
        "calendar_comparison": {
            "fpt_dates_absent_from_vnindex": [str(d.date()) for d in fpt_only],
            "vnindex_dates_absent_from_fpt": [str(d.date()) for d in vn_only],
            "vnindex_return_intervals_needing_review": vn_intervals,
            "note": "Not an exchange holiday calendar. Forward carry can hide missing source dates; investigate rather than invent bars.",
        },
        "aligned_model_feature_coverage": coverage,
        "financial_missing_quarters_inside_archive": [str(q) for q in absent_quarters],
        "financial_accounting_checks": accounting,
        "cpi_reference_period_status": "Release date and value are stored, but reference month is not a separate field. Missing release-calendar months cannot establish missing economic reference months.",
        "publication_date_status": "Quarter-end+45 and year-end+180 are assumptions; shares include one assumed availability date. Historical revision vintages have not been verified.",
        "source_file_sha256": hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/data_quality_review.json")
    args = parser.parse_args()
    report = review()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved: {args.output}")
    print(f"OHLC exceptions: {len(report['fpt_ohlc_violations'])}")
    print(f"FPT dates absent from VN-Index: {len(report['calendar_comparison']['fpt_dates_absent_from_vnindex'])}")
    print(f"Missing financial quarters: {len(report['financial_missing_quarters_inside_archive'])}")


if __name__ == "__main__":
    main()
