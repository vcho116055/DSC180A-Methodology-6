# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-24 Add `cnt_roll_28` (mean cnt over d-28..d-1). Availability: every input is a count from a day strictly before d, known at prediction time. LAG_WARMUP 7 -> 28 (train rows 348 -> 306). `cnt_lag_7`/`cnt_roll_7` decoupled from LAG_WARMUP, which would otherwise have become 28-day windows; new test guards cnt_lag_7. Validation R^2 on identical rows: ridge 0.6462 -> 0.6839 (+0.038), hgb 0.1929 -> 0.2415 (+0.049). Test set not consulted.
- 2026-11-24 Hook `check_leakage.sh` now runs `.venv/bin/python` (fallback `python3`). The starter called bare `python`, which does not exist on macOS outside an activated venv, so every src/ edit produced a false "leakage tests failed: python: command not found".
- 2026-11-24 Raw data is checked by SHA-256 in `src.ingest.load_raw` and `test_raw_data_is_unmodified`. Deny rules bind only Edit/Write and the PostToolUse hook only matches Edit|Write, so a `cp` into data/raw/ from Bash was invisible; now every pipeline stage and the suite fail on it.
- 2026-11-24 CLAUDE.md: added rules for LAG_WARMUP (longest window, never a specific lag), classifying every raw column, raw-data hash; named both skills and the headline-number command. 50 lines.
- 2026-11-24 Keep `cnt_roll_28`: validation gains (+0.038 ridge, +0.049 HGB R^2) are well above the 0.01 noise floor; cost is 42 fewer training rows (348 -> 306).
- 2026-11-24 Makefile: use `.venv/bin/python` when present, and write the Modelfile to a temp file for `make model` (`ollama create -f -` fails on Ollama 0.40). Tooling only; no effect on metrics.
- 2026-11-24 Exercise 4: target = cnt minus `cnt_roll_7`, the only variant near the top for both models on validation (ridge R^2 0.6849, HGB 0.7139). Test scored once afterwards: HGB R^2 0.6331, MAE 830.1. Defensible: fixes trees' inability to extrapolate, using only past data. Committed metrics.json stays untransformed.
- 2026-11-24 Exercise 5: persistence over ridge for deployment. Ridge has higher test R^2 (0.6239 vs 0.5099) but higher MAE (879.3 vs 840.1); its gains on 52 big-swing days (~40,600 rides of error) are outweighed by losses on 132 calm days (~47,900).
- 2026-11-24 Reviewed and accepted the starter's rules: leakage set (`casual`, `registered`), exclusions (`cnt_2d_bfr`, time indexes), the 2011 / H1 2012 / H2 2012 split, and both baselines.
- 2026-11-24 Ignore raw `season`, `mnth`, `weekday` (IGNORED_COLS): `month_sin`/`month_cos` and `dayofweek`, derived from dteday, carry the same information.
- 2026-11-24 Believable as a modest claim only: ridge beats persistence on R^2 (0.6239 vs 0.5099) but not on MAE (879.3 vs 840.1) and underpredicts by ~427 rides/day. The headline is a small, real gain on large swings, not a better everyday forecaster.
- 2026-11-24 Adopt the SHA-256 raw-data check (`verify_raw`) as the Fault-4 defence after reviewing it: it catches changes from any tool, where a PreToolUse pattern on Bash could be evaded.
- 2026-11-24 Add `.gitattributes` with `data/raw/** -text`. Git on Windows (core.autocrlf=true) rewrote the raw CSV with CRLF on checkout, so `verify_raw` rejected the official file (sha256 13e33ae5... vs a6bed157...) and `git checkout -- data/raw/` could not repair it. Found on a Windows machine during the audit run.
- 2026-11-24 `agent/audit.py`: max_turns 40 -> 150, SDK exceptions become a `run_failed` row instead of crashing the batch, and `repo` is always the directory name (the model's own `repo` value used to overwrite it). With 40 turns the qwen3.5:27b run raised "Reached maximum number of turns (40)" and wrote nothing.
- 2026-11-24 In `reports/audit.jsonl`, replace the model-written `repo` value (a local Windows path with a username) with `DSC180A-Methodology-6` for privacy; all other fields verbatim. Documented in docs/AUDIT.md.
