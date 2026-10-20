# Agent Work Log — FPT Stock Trends Prediction

## Objective
Build a reproducible, leakage-safe ML project to classify next-session FPT stock direction using source-repository data; produce real EDA/model results, Vietnamese proposal/report/docs, and publish to the specified GitHub repository.

## Phase checklist and state

### Phase 1 — Setup & EDA
- [x] Inspect workspace and Git state; inspect source repository and identify usable stock dataset(s).
- [x] Bring source data into the project workspace and document provenance/license/access details where available.
- [x] Audit columns, types, date range, missing values, duplicates, and outliers; record findings here.
- [x] Implement reproducible EDA and save Close, Volume, and return-distribution figures under `figures/`.
- [x] Record dataset summary and EDA outcomes here.

### Phase 2 — Preprocessing & feature engineering
- [x] Define prediction time and next-session binary target to avoid target leakage.
- [x] Implement date handling, missing-data policy, lagged returns, SMA/EMA, RSI, MACD, Bollinger features, and other justified technical features.
- [x] Make chronological train/validation/test splits; fit preprocessing only on train.
- [x] Record feature and split details here.

### Phase 3 — Modeling & evaluation
- [x] Establish majority-class and/or logistic-regression baseline.
- [x] Train and compare at least 2–3 appropriate approaches (e.g. Logistic Regression, Random Forest, XGBoost; add sequence model only if data/compute justify it).
- [x] Evaluate on untouched chronological test data with classification metrics; include RMSE/MAE only if a price-regression experiment is actually run and clearly separate it from the main classification task.
- [x] Save metrics, predictions, comparison table, plots, and best model artifact under project directories.
- [x] Record actual results and limitations here.

### Phase 4 — Academic documentation
- [x] Write `docs/PROPOSAL.md` in Vietnamese based on the finalized scope and available data.
- [x] Write `docs/REPORT.md` using only executed results; link figures and describe methods, metrics, limitations, and future work.
- [x] Write root `README.md` with setup, commands, structure, and actual results.

### Phase 5 — Packaging & GitHub
- [x] Add `.gitignore` and complete `requirements.txt`.
- [x] Run end-to-end checks from a reproducible invocation; check repository contents and Git status.
- [x] Update this log with final completion status and any limitations.
- [x] Configure the authorized target remote, commit changes, and push to `main`.

## Work log
- Initial checklist was created before project code; this file is updated as each phase completes.

- 2026-10-20: GitHub source and empty target repo cloned after execution-environment approval for network access. Existing Krafton files are preserved; FPT project is isolated in this directory.
- 2026-10-20: Selected `data/raw/fpt/fpt_historical_price.csv`: 4,678 rows, 6 columns (`time, open, high, low, close, volume`), 2007-01-02 to 2025-10-09. No missing values, duplicate dates, or unsorted rows; two zero-volume sessions; three OHLC consistency violations; max absolute close return is about 6.99%, with no return above 20%. The Phase 6 notebook/history audit later identified the provider as `vnstock`/VCI; unit and adjustment metadata remain unconfirmed. Source repository has no LICENSE.
- 2026-10-20: The synthesized dataset has extensive missingness (GDP missing on 1,524/1,529 rows; several company/industry features missing on 1,507–1,510 rows). The precomputed dataset includes scaled features with unclear fit period. Exclude both from the main run to avoid ambiguous preprocessing and leakage.
- 2026-10-20: Next-session returns have 2,121 up, 2,077 down, and 479 unchanged labels among 4,677 targets. The main classifier will exclude unchanged sessions and report this choice; a supplementary next-close regression keeps all labels. Use only close/volume-derived features, so OHLC inconsistencies do not enter technical indicators.
- 2026-10-20: Source OHLCV copied into `data/raw/fpt/`; provenance limitations recorded in `data/README.md`. EDA, model runs, and documentation are complete.

- 2026-10-20: Implemented `src/eda.py`; `python src/eda.py` completed successfully. Generated four figures: closing price, volume, daily-return distribution, and next-session class counts. Saved machine-readable audit to `reports/data_audit.json`.
- 2026-10-20: EDA confirms 4,678 rows; 4,677 daily returns; average simple return 0.000646, standard deviation 0.01918, min -0.06990, max 0.06992. Next-session classes: 2,121 up, 2,077 down, 479 unchanged. No missing values or duplicate dates. Volume is shown on a symmetric-log axis to retain small values and make spikes visible.
- 2026-10-20: Implemented `src/features.py`, `src/prepare.py`, `src/train.py`, `src/predict.py`, and three regression tests. The target is close(t+1) versus close(t); the final one-session label is attached to the actual target date before chronological splitting.
- 2026-10-20: Features include five lag returns, SMA/EMA ratios at 5/10/20/50 sessions, RSI-14, MACD/signal/histogram ratios, Bollinger %B/width, 5/20-session volatility, and log-volume change/z-score. Classifier uses 23 features; regression adds current close.
- 2026-10-20: Final chronological partitions contain 3,239/694/695 regression rows and 2,850/646/660 non-flat classification rows. Target date boundaries: train through 2020-03-19, validation 2020-03-20–2022-12-22, test 2022-12-23–2025-10-09. StandardScaler is fit inside model pipelines.
- 2026-10-20: Real test results: validation-selected Random Forest classifier Accuracy 0.5318, Balanced Accuracy 0.5270, F1-up 0.5841, ROC-AUC 0.5593; confusion matrix actual down/up by predicted down/up = [[134,180],[129,217]]. HistGradientBoosting had the highest test Balanced Accuracy (0.5528) but was not selected because its validation Balanced Accuracy was lower (0.4908 vs RF 0.5105).
- 2026-10-20: Regression model chosen by validation MAE was Last Close baseline; test RMSE 1.5010, MAE 1.0052, MAPE 1.0978%, directional accuracy 0% (flat predictions on non-flat targets). Linear Regression test MAE 1.0055, directional accuracy 51.82%; tree regressors extrapolated poorly on later price levels. This supports keeping regression supplemental.
- 2026-10-20: `python src/prepare.py`, `python src/train.py`, and `python src/predict.py` completed. Latest in-file prediction is for the next observed session after 2025-10-09: Random Forest predicts down with P(up)=0.4076; regression baseline repeats 94.2.
- 2026-10-20: Final validation passed: `python -m py_compile` for all source/test files; `python -m pytest -q` (3 passed); `src/eda.py`, `src/prepare.py`, `src/train.py`, and `src/predict.py` all completed; `python -m pip check` found no dependency conflicts; all local Markdown image links resolve.
- 2026-10-20: Added README, proposal, detailed report, `.gitignore`, and `requirements.txt`. Report uses the final generated metrics and figure paths.
- 2026-10-20: Repository audit found only the intended FPT project artifacts in the target repo. Total working tree is approximately 5.6 MB; no TODO/placeholder markers were found in source, tests, docs, or README. Phase 5 code packaging was ready before the initial push.
- 2026-10-20: All five phases are complete (100%). First project commit `17b6d4d` was pushed successfully to `https://github.com/thiemhoang4807/fpt-stock-trends-prediction` on `main`; the final status log is included in a follow-up commit.
- Limitations to retain in future work: source ends 2025-10-09; upstream repo lacks a LICENSE; unit is inferred and adjusted/unadjusted details are absent; classification improvement over majority baseline is modest and is not evidence of investment profitability.

## Phase 6 — Data provenance and ingestion
- [x] Deep-audit all upstream notebooks, Python/config files, data generation flow, and full Git history.
- [x] Establish historical-price source/API/library, extraction/normalization behavior, price unit, and adjustment status from direct evidence; separate verified facts from unresolved metadata.
- [x] Implement `src/fetch_data.py` CLI for VCI/vnstock download, exported CSV normalization, and locked-snapshot verification.
- [x] Add unit tests for normalization, invalid values, duplicate dates, and snapshot integrity.
- [x] Update `data/README.md`, root `README.md`, `docs/PROPOSAL.md`, and `docs/REPORT.md` with source provenance and fetch instructions.
- [x] Run tests and `python src/fetch_data.py --verify`; confirm previous metrics/figures remain unchanged.
- [ ] Commit Phase 6 on a new branch and push to the target GitHub repository.

### Phase 6 source audit findings
- Full upstream Git history was fetched (not just the shallow checkout). Audited the current seven notebook files, historical notebook versions present at commit `65c7780`, both Python scripts, `requirements.txt`, `.gitignore`, data READMEs, raw-data files, the project report/slide PDFs, and commit history. The upstream `notebook/data_ingestion/news_ingestion.ipynb` is 0 bytes and not valid notebook JSON; price extraction is separately documented in `API_use.ipynb`. The earlier `hehe.ipynb` reads existing CPI/FPT CSVs rather than acquiring them; the old EDA notebook uses a Tesla CSV unrelated to this FPT data.
- Direct evidence for FPT OHLCV is `from vnstock import Quote`; `Quote(symbol='FPT', source='VCI')`; `history(start='2007-01-01', end='2025-10-09')`; and `to_csv(...fpt_historical_price.csv)`. VCI refers to the source selected through vnstock (Vietcap). The notebook uses no widget, Selenium, Playwright, yfinance, or direct API URL for the price pull. `vnstock` is missing from upstream `requirements.txt`, despite being imported in the notebook. The FPT income statement uses `vnstock.Finance(..., source='VCI')`.
- Relevant history: commit `65c7780` (2025-10-16) added the historical CSV, API notebook, and `data/README.md`; `96a6524` (2025-10-16) reorganized the notebook path and added the Selenium/news scraper; `bf714a1` (2025-11-10) moved OHLCV/financial/macro inputs under `data/raw/` and added the synthesis notebook. The source report PDF independently says FPT price/volume/financial indicators use vnstock API; macro series are manually downloaded as CSV; industry market cap/P-E are manually copied; its general market-site list includes CafeF, Vietstock and Investing. Upstream data READMEs name Investing.com for USD/VND, CPI and XAU/USD, World Bank with 2025 IMF forecast for GDP, and Simply Wall St for ICT-industry P/E, but the later `data/raw/README.md` leaves GDP/XAU sources blank and labels XAU-VND despite the XAU/USD file. The source report labels stock-price prediction errors in thousand VND, supporting the dataset's thousand-VND scale though the CSV itself has no unit metadata. `src/datasets/ingest_news.py` controls Google News via Selenium and parses article pages with newspaper3k; it is not connected to the model's training data and its hard-coded example queries are unrelated to FPT.
- `dataset_synthesis.ipynb` outer-joins sparse annual, quarterly, macro and stock series on calendar date. The 1,529-row `synthetized_dataset.csv` has missingness: CPI 1,461 (95.55%), GDP 1,524 (99.67%), market cap and PE 1,510 each (98.76%), each FPT financial metric 1,507 (98.56%), and price/volume 96 each (6.28%). The EDA/preprocessing notebook runs `pipeline.fit_transform(dataset)` over the full table; upstream `src/preprocessor.py` calls `StandardScaler.fit_transform` on the full series and uses both `bfill` and `ffill`. The fit period is not stored, so future-distribution leakage is possible; these precomputed CSVs are excluded.
- Snapshot audit found 4,678 rows, columns `time, open, high, low, close, volume`, dates 2007-01-02 through 2025-10-09, prices min/max 1.76/134.50, close min/max 1.82/133.04, volume min/max 0/23,514,300, and three OHLC-inconsistent rows. LF-normalized SHA-256 is `263eced0cb25bc0380ed0dba7dc6f8d77b409146c7b4e2b1b0fd9f0ddbf25e98`; it matches the Git blob and ignores Windows CRLF conversion. No transforms are applied to the snapshot. Price scale is interpreted as thousands of VND (e.g. 94.2 ≈ 94,200 VND), supported by the source report's price-error units; the CSV/notebook does not have per-column unit metadata. The artifact has no adjusted-price flag or event factors and the notebook performs no adjustment. Smooth returns are consistent with provider-adjusted history, but exact adjustment policy (splits, bonus/right shares, cash dividends) is unverified; docs retain that limitation rather than asserting a definitive basis.
- Implemented `src/fetch_data.py`: `--download` calls the same vnstock `Quote`/VCI daily-history interface; `--input` maps common English/Vietnamese CSV headers, filters FPT if a ticker column exists, validates dates/numeric values/duplicates and writes the canonical six columns; `--verify` checks structure, ranges, dates, OHLC anomalies and exact SHA-256 without editing the file. External API refreshes may be revised; exact reproducibility applies to the pinned committed snapshot, not future API responses.
- Added `tests/test_fetch_data.py`. Validation: final `python -m pytest -q` → 13 passed, including a mocked-provider test for the exact `Quote` call; `python src/fetch_data.py --verify` → passed with expected hash, range and three recorded OHLC anomalies. `git diff main -- figures models reports` was empty, so existing figures, trained models and metrics were not modified.
