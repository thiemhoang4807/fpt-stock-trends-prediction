"""Validate raw data and export backward-looking indicators and next-session targets."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from features import (
    PRICE_ONLY_FEATURE_COLUMNS,
    FEATURE_COLUMNS,
    OHLC_FEATURE_COLUMNS,
    build_feature_table,
    load_price_data,
)
from fetch_supplemental import MODEL_SUPPLEMENTAL_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "fpt_next_session_features.csv"
DEFAULT_SUPPLEMENTAL = ROOT / "data" / "processed" / "fpt_multisource_features.csv"
BRANCH_PRICE = "Branch_1_Price_Only"
BRANCH_MACRO = "Branch_2_Macro_Fundamental"


def merge_supplemental(
    table: pd.DataFrame, path: Path
) -> tuple[pd.DataFrame, list[str]]:
    """Join only declared input columns, never outcomes or arbitrary CSV fields."""
    if not path.is_file():
        raise FileNotFoundError(f"Run fetch_supplemental.py first: {path}")
    supplement = pd.read_csv(path)
    required = ["date", *MODEL_SUPPLEMENTAL_COLUMNS]
    missing = sorted(set(required) - set(supplement.columns))
    if missing:
        raise ValueError(f"Missing required supplementary columns: {missing}")
    supplement = supplement[required].copy()
    supplement["date"] = pd.to_datetime(
        supplement["date"], errors="coerce"
    ).dt.normalize()
    if supplement["date"].isna().any() or supplement["date"].duplicated().any():
        raise ValueError("Supplementary session dates must be valid and unique")
    for column in MODEL_SUPPLEMENTAL_COLUMNS:
        supplement[column] = pd.to_numeric(supplement[column], errors="coerce")
    supplement = supplement.replace([np.inf, -np.inf], np.nan)
    return table.merge(supplement, on="date", how="left", validate="one_to_one"), list(
        MODEL_SUPPLEMENTAL_COLUMNS
    )


def build_experiment_table(
    input_path: Path, supplemental_path: Path = DEFAULT_SUPPLEMENTAL
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, list[str]]]:
    """Return all price features, the common two-branch cohort, and input lists."""
    raw = load_price_data(input_path)
    base = build_feature_table(raw)
    joined, supplemental_columns = merge_supplemental(base, supplemental_path)
    branches = {
        BRANCH_PRICE: list(PRICE_ONLY_FEATURE_COLUMNS),
        BRANCH_MACRO: list(PRICE_ONLY_FEATURE_COLUMNS) + supplemental_columns,
    }
    complete = joined[branches[BRANCH_MACRO]].notna().all(axis=1)
    # Same dates for all lookbacks; never compress holes into adjacent sessions.
    consecutive = joined["session_index"].diff(59).eq(59)
    eligible = complete.rolling(60, min_periods=60).sum().eq(60) & consecutive
    common = joined.loc[eligible].copy().reset_index(drop=True)
    common.attrs["sequence_context"] = joined
    if common.empty:
        raise ValueError("No common observations with complete two-branch inputs")
    return base, common, branches


def feature_groups() -> dict[str, list[str]]:
    """Cumulative ablation inputs; the unavailable sector block is explicit."""
    g1 = ["current_close", "current_volume"] + [
        c
        for c in FEATURE_COLUMNS
        if c.startswith("return_") or c.startswith("log_volume_")
    ]
    g2 = list(dict.fromkeys(g1 + FEATURE_COLUMNS))
    g3 = list(PRICE_ONLY_FEATURE_COLUMNS)
    financial = [c for c in MODEL_SUPPLEMENTAL_COLUMNS if c.startswith("fpt_")]
    sector = [c for c in MODEL_SUPPLEMENTAL_COLUMNS if c.startswith("ict_")]
    macro = [c for c in MODEL_SUPPLEMENTAL_COLUMNS if c not in financial + sector]
    return {
        "G1": g1,
        "G2": g2,
        "G3": g3,
        "G4": g3 + macro,
        "G5": g3 + macro + sector,
        "G6": g3 + macro + sector + financial,
    }


def prepare(
    input_path: Path, output_path: Path, supplemental_path: Path = DEFAULT_SUPPLEMENTAL
) -> tuple[int, int]:
    raw = load_price_data(input_path)
    table, common, branches = build_experiment_table(input_path, supplemental_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False)
    common.to_csv(output_path.parent / "fpt_two_branch_features.csv", index=False)
    usable_outcomes = int(table["target_date"].notna().sum())
    print(f"Raw rows: {len(raw)}")
    print(f"Rows with complete backward-looking features: {len(table)}")
    print(f"Labeled next-session rows: {usable_outcomes}")
    print(f"Branch 1 input columns: {len(branches[BRANCH_PRICE])}")
    print(f"Branch 2 input columns: {len(branches[BRANCH_MACRO])}")
    print(f"Common two-branch rows (including latest unlabeled row): {len(common)}")
    print(f"Saved: {output_path}")
    return len(table), usable_outcomes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare FPT next-session features without future filling."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--supplemental", type=Path, default=DEFAULT_SUPPLEMENTAL)
    args = parser.parse_args()
    prepare(args.input, args.output, args.supplemental)


if __name__ == "__main__":
    main()
