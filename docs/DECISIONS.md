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
