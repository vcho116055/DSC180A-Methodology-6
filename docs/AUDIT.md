# Audit (Exercise 3)

## Repository audited

https://github.com/j2doan/bikeshare-open (a teammate's repository, private),
audited at commit `f5a01ad` ("Add seed-fault skill"), 20 commits. First commit
(the unmodified starter): `0b8c4d0`.

## How it was run

On a Windows PC (Radeon 7900 XTX), in a fresh clone with its own venv
(`pip install -r requirements.txt`; their suite: 17 passed before the audit):

```
cd teammate-bikeshare-open
claude          # model from their .claude/settings.json
```

Prompt: *"Use the leakage-auditor subagent to audit this repository. Have it
review everything changed since the first commit (git diff
<first-commit-hash>..HEAD) plus the current code in src/ and tests/. It must not
edit, commit, or push anything. When it finishes, print the subagent's full reply
verbatim."* The run took 7 min 8 s. `git status` was clean before the audit.
TODO(you): confirm `git status --porcelain` in their clone was still empty afterwards.

Model: `bikeshare-coder` (named in their `.claude/settings.json`), which on that PC is
the `qwen3.5:27b` build with a 64k context (Ollama id `47a87cd9e8fe`).

## `/leakage-auditor` output, verbatim

```
  Leakage Audit Findings

  Based on a comprehensive review of all code changes since commit 0b8c4d088a1a96f822b713a88403e148cb55064b and the
  current state of src/ and tests/, all five checks pass without issues that change numbers or invalidate conclusions.

  ---

  Check 1: Target Leakage — PASS

  Files reviewed: src/config.py, src/features.py, tests/test_leakage.py

  - FORBIDDEN in config.py (line 46) correctly includes LEAKAGE_COLS = {"casual", "registered", "cnt"}
  - feature_columns() in features.py (lines 86-89) explicitly filters out all forbidden columns
  - Test test_no_forbidden_features asserts no overlap between feature set and FORBIDDEN
  - Test test_leakage_identity_holds documents that casual + registered == cnt exactly

  Verified: Running code confirms no leaked columns:
  >>> cols = set(feature_columns(df))
  >>> cols & FORBIDDEN
  set()  # Empty - no leakage

  ---

  Check 2: Temporal Ordering — PASS

  Files reviewed: src/features.py, src/train.py, tests/test_split.py

  - All lag features use .shift() before any computation:
    - Line 74: cnt_lag_1 = out[TARGET].shift(1)
    - Line 75: cnt_lag_7 = out[TARGET].shift(LAG_WARMUP)
    - Line 76: cnt_roll_7 = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
    - Line 81: temp_lag_1 = out["temp"].shift(1)
  - Split is temporal, not random (train.py lines 59-62):
  train = df[df.dteday <= "2011-12-31"]    # 348 rows
  valid = df[(df.dteday > "2011-12-31") & (df.dteday <= "2012-06-30")]  # 182 rows
  test = df[df.dteday > "2012-06-30"]      # 184 rows
  - Test test_splits_are_ordered_in_time verifies train.max < valid.min and valid.max < test.min

  ---

  Check 3: Calendar Gaps — PASS

  Files reviewed: src/features.py, tests/test_leakage.py

  - reindex_to_calendar() (lines 34-50) is called FIRST in build_features() before any lag computation
  - Test test_lags_are_true_calendar_lags verifies cnt_lag_1 for date d equals cnt on d-1 calendar days
  - Test test_temp_lag_1_is_yesterdays_temp similarly validates the new temperature lag feature

  ---

  Check 4: Silent Row Loss — PASS

  Files reviewed: tests/test_contract.py, src/config.py

  - test_only_expected_rows_are_dropped (lines 28-43) bounds allowed row loss:
  allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days  # 7 + 7*1 = 14 rows max
  lost = len(raw) - len(feats)
  assert lost <= allowed_loss
  - Actual loss: 728 raw rows - 714 feature rows = 14 rows (exactly at bound)

  ---

  Check 5: Unreported Baseline — PASS

  Files reviewed: src/train.py, reports/metrics.json

  Both baselines are reported in metrics.json with their full scores:

  ┌──────────────────────┬──────────┬─────────┐
  │        Model         │ Valid R² │ Test R² │
  ├──────────────────────┼──────────┼─────────┤
  │ baseline_mean        │ -0.9318  │ -2.1441 │
  ├──────────────────────┼──────────┼─────────┤
  │ baseline_persistence │ 0.4507   │ 0.5099  │
  ├──────────────────────┼──────────┼─────────┤
  │ ridge                │ 0.6951   │ 0.6238  │
  ├──────────────────────┼──────────┼─────────┤
  │ hgb                  │ 0.1936   │ -0.5785 │
  └──────────────────────┴──────────┴─────────┘

  - Test test_persistence_baseline_is_reported asserts "baseline_persistence" in MODELS
  - Negative R² for mean baseline on test set is correctly reported (not hidden) — this shows the distribution shift
    CLAUDE.md warns about

  ---

  Note on Seeded Faults

  The git log shows seeded faults that were introduced and fixed during development:
  - Fault 1: casual added to features → caught by test, removed
  - Fault 2: .shift(1) removed from cnt_roll_7 → caught by test, restored
  - Fault 3: raise removed from encode_weather → caught by test, restored

  The current codebase represents the fixed state after all faults were corrected.

  ---

  Final verdict: All five checks pass. No findings that change a number or invalidate a conclusion.
```

## Independent checks (run by the agent, not the auditor)

To test the auditor's claims rather than accept them, the agent cloned the same
commit separately and ran:

| Check | Result |
|---|---|
| Their pipeline (`src.ingest`, `src.features`, `src.train`) with the pinned packages, then `git diff reports/metrics.json` | Reproduced **exactly** |
| `pytest tests/` | 17 passed |
| `temp_lag_1`: built after `reindex_to_calendar`, `.shift(1)`, tested against temp on d−1 | Correct; inputs are all from before day d |
| Row accounting: 728 raw → 714 rows, bound 14 | Matches the auditor's Check 4 |
| `git check-ignore reports/audit.jsonl` | **Ignored**, by the bare `audit.jsonl` line still in their `.gitignore` |

Things the auditor did not mention, none of which changes a number:
1. Their `.gitignore` still ignores `audit.jsonl` everywhere, so their
   `reports/audit.jsonl` (rubric item 6) cannot be committed without removing it.
2. Their hook parses its input with `python3`. On Windows that is missing or a
   Store stub, so the hook silently does nothing there.
3. No `.gitattributes`: a Windows checkout writes the raw CSV with CRLF, so its
   bytes (and SHA-256) differ from the committed file.
4. `cnt_lag_7 = shift(LAG_WARMUP)` is correct only while `LAG_WARMUP == 7`.
   Raising it for a longer feature would silently turn it into a longer lag.
5. The auditor's "Note on Seeded Faults" says fault 3 was "caught by test". Their
   own commit `cbe70b9` records that no test caught it until `3598b4a` added one.

## My verdict

TODO(you): one paragraph, in your own words.

## `agent/audit.py` on my own repository

`reports/audit.jsonl` is one run of `python agent/audit.py <repo> --out
reports/audit.jsonl` against this repository at commit `8294e91`.

- **Model:** `bikeshare-coder` = `qwen3.5:27b`, 64k context, 100% GPU (Ollama 0.40.17,
  Windows 11, Radeon 7900 XTX). Runtime 197 s.
- **Script:** the first run with the starter script crashed with
  `Reached maximum number of turns (40)` and wrote no row, because the SDK raises
  instead of returning an error. The row comes from a copy with `max_turns=150` and
  that exception caught; the same changes are now in `agent/audit.py` (commit `462eb6b`).
- **One edit:** the `repo` value was the model's own, the full local Windows path
  including a username. It was replaced with `DSC180A-Methodology-6` for privacy.
  Every other field is verbatim. The patched script now sets `repo` itself.

**Result:** leakage `none`; `temporal_ok`, `baseline_reported` and `reproducible` all
`true`; confidence `high`. Its four "findings" are things the code does correctly,
not problems, so nothing needed fixing or arguing.

**What the auditor did to the working tree.** With Bash access, it changed tracked
files during its run: it rewrote `data/raw/bike_daily.csv` (line endings only; that
exposed the CRLF bug fixed by `.gitattributes` in `c80dd54`), wrote
`tmp_features.csv`, and regenerated `reports/metrics.json` with a different hgb row
(test R² −0.4442 vs the committed −0.46). A clean clone on the same Windows PC
reproduces the committed `reports/metrics.json` exactly and passes all 19 tests,
and the unmodified starter matches all eight values published in the assignment.
So the different row came from whatever the auditor ran, not from the pipeline.
Its `reproducible: true` holds, but it was not checked by the auditor's own run.
The read-only boundary the script's comments describe ("no Edit or Write to
grant") does not stop writes through Bash.
