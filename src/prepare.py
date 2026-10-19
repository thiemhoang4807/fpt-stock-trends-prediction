"""Validate raw data and export backward-looking indicators and next-session targets."""

from __future__ import annotations

import argparse
from pathlib import Path

from features import FEATURE_COLUMNS, build_feature_table, load_price_data


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "fpt" / "fpt_historical_price.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "fpt_next_session_features.csv"


def prepare(input_path: Path, output_path: Path) -> tuple[int, int]:
    raw = load_price_data(input_path)
    table = build_feature_table(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False)
    usable_outcomes = int(table["target_date"].notna().sum())
    print(f"Raw rows: {len(raw)}")
    print(f"Rows with complete backward-looking features: {len(table)}")
    print(f"Labeled next-session rows: {usable_outcomes}")
    print(f"Feature count: {len(FEATURE_COLUMNS)}")
    print(f"Saved: {output_path}")
    return len(table), usable_outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare FPT next-session features without future filling.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    prepare(args.input, args.output)


if __name__ == "__main__":
    main()
