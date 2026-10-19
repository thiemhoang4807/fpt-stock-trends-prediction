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
- [ ] Update this log with final completion status and any limitations.
- [ ] Configure the authorized target remote, commit changes, and push to `main` if network/authentication allow.

## Work log
- Initial checklist was created before project code; this file is updated as each phase completes.

- 2026-10-20: GitHub source and empty target repo cloned after execution-environment approval for network access. Existing Krafton files are preserved; FPT project is isolated in this directory.
- 2026-10-20: Selected `data/raw/fpt/fpt_historical_price.csv`: 4,678 rows, 6 columns (`time, open, high, low, close, volume`), 2007-01-02 to 2025-10-09. No missing values, duplicate dates, or unsorted rows; two zero-volume sessions; three OHLC consistency violations; max absolute close return is about 6.99%, with no return above 20%. Source repository README does not identify the precise provider for this file and has no LICENSE.
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
- 2026-10-20: Added README, proposal, detailed report, `.gitignore`, and `requirements.txt`. Report uses the final generated metrics and figure paths. Local repository review and GitHub publication are the remaining steps.
- 2026-10-20: Repository audit found only the intended FPT project artifacts in the target repo. Total working tree is approximately 5.6 MB; no TODO/placeholder markers were found in source, tests, docs, or README. Phase 5 code packaging is ready; commit/push and post-push status are still pending.
