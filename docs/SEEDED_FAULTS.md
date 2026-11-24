# Seeded faults (Exercise 2)

Every block below is pasted output, captured with the commands in
`.claude/skills/seed-fault/SKILL.md`. "Hook stderr" is the real
`.claude/hooks/check_leakage.sh`, fed the same JSON payload Claude Code
sends after an Edit.

**How the hook was exercised.** The agent session that seeded these faults
was launched from the parent directory, so the repo's `.claude/settings.json`
hook config was not loaded and the hook did not fire *live* on those edits.
The stderr below comes from piping the exact PostToolUse payload into the
script. TODO(you): from the repo root, run `claude`, ask it to re-seed
fault 1, and confirm the hook's message appears in the session.

| # | Fault | Suite | Hook | Agent turns to fix | Commits |
|---|-------|-------|------|--------------------|---------|
| 1 | `"casual"` appended to `feature_columns` | red (`test_no_forbidden_features`) | exit 2 | 1 | `5e0b87a`, `83171d5` |
| 2 | `.shift(1)` removed from `cnt_roll_7` | red (`test_rolling_mean_excludes_today`) | exit 2 | 1 | `a5e9d68`, `d38f303` |
| 3 | `raise` removed from `encode_weather` | **green**, until a new test was added | exit 0, then exit 2 | 1 (+1 to write the test) | `2d0b02b`, `2043990`, `e1cb6ad` |
| 4 | `cp` over `data/raw/bike_daily.csv` from Bash | green before the fix; red after | never runs (Bash is not `Edit\|Write`) | n/a | `909fbc7` |

## Fault 1: a forbidden column in `feature_columns`

```diff
diff --git a/src/features.py b/src/features.py
index 04c28d9..2bb2a2e 100644
--- a/src/features.py
+++ b/src/features.py
@@ -89,7 +89,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 
 if __name__ == "__main__":
```

`make test`:
```
......F..........                                                        [100%]
=================================== FAILURES ===================================
E   AssertionError: forbidden columns in feature set: {'casual'}
    assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_28', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})
/Users/eubin/Downloads/bikeshare-open/tests/test_leakage.py:31: AssertionError: forbidden columns in feature set: {'casual'}
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 1.37s
```

Hook stderr:
```
Leakage tests failed after editing /Users/eubin/Downloads/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7  cnt_roll_28
0   2011-01-31     31.0  WINTER  ...     141....142857  4071.321429
671 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  3969.428571

[672 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_28', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 8 passed in 0.32s
(hook exit code: 2)
```

## Fault 2: `.shift(1)` deleted from `cnt_roll_7`

```diff
diff --git a/src/features.py b/src/features.py
index 04c28d9..9b89cb6 100644
--- a/src/features.py
+++ b/src/features.py
@@ -76,7 +76,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # 28-day lag the moment a longer feature arrives.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(7)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(7).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(7).mean()
 
     # 28-day trailing level of demand. Shifted before rolling, so the
     # window for date d is d-28 .. d-1. Gives the model the current level
```

`make test`:
```
.........F.......                                                        [100%]
=================================== FAILURES ===================================
E   assert np.float64(4605.285714285715) == 4724.428571428572 ± 0.00472443
      comparison failed
      Obtained: 4605.285714285715
      Expected: 4724.428571428572 ± 0.00472443
/Users/eubin/Downloads/bikeshare-open/tests/test_leakage.py:57: assert np.float64(4605.285714285715) == 4724.428571428572 ± 0.00472443
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 1.15s
```

Hook stderr:
```
Leakage tests failed after editing /Users/eubin/Downloads/bikeshare-open/src/features.py:
[672 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4605.285714285715) == 4724.428571428572 ± 0.00472443
E             
E             comparison failed
E             Obtained: 4605.285714285715
E             Expected: 4724.428571428572 ± 0.00472443

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 8 passed in 0.32s
(hook exit code: 2)
```

The rolling-mean test checks one date (row 200). It caught this fault, but
it would silently pass (`if all(...)`) if that row's window crossed the
2011-03-10 gap.

## Fault 3: the weather encoder's `raise` removed

```diff
diff --git a/src/features.py b/src/features.py
index 04c28d9..16a1390 100644
--- a/src/features.py
+++ b/src/features.py
@@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

`make test`, with the starter suite: **green**.
```
.................                                                        [100%]
17 passed in 1.15s
```

Hook: nothing on stderr.
```
(hook exit code: 0)
```

This fault was invisible. The real data only contains GOOD / MISTY / BAD,
so nothing ever reaches the `raise`, and the row-loss bound never sees an
unmapped label. Added `test_weather_encoder_rejects_unknown_labels`, which
calls `encode_weather` on a series containing `"HAIL"`. With the fault
still in place:

```
............F.....                                                       [100%]
=================================== FAILURES ===================================
E   Failed: DID NOT RAISE ValueError
/Users/eubin/Downloads/bikeshare-open/tests/test_leakage.py:92: Failed: DID NOT RAISE ValueError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...
1 failed, 17 passed in 1.16s
```

Hook stderr:
```
Leakage tests failed after editing /Users/eubin/Downloads/bikeshare-open/src/features.py:
.......F..                                                               [100%]
=================================== FAILURES ===================================
_________________ test_weather_encoder_rejects_unknown_labels __________________

    def test_weather_encoder_rejects_unknown_labels():
        """The real data only has GOOD/MISTY/BAD, so the row-loss bound never sees
        an unmapped label. Feed one directly: a silent .map() would return NaN
        here and let a later dropna() delete those days without a word."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:92: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...
1 failed, 9 passed in 0.31s
(hook exit code: 2)
```

## Fault 4: a `cp` into `data/raw/` from Bash

**What happened.** The agent's attempt to run
`cp ../ma6-scratch/bike_daily_tampered.csv data/raw/bike_daily.csv`
(one row, 2012-07-04, with `temp` lowered by 10) was blocked, but not by
anything in this repo. Claude Code's auto-mode safety classifier refused it:

```
Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Undermining Oversight].
```

The repo's own rules would not have stopped it. `deny: Edit(./data/raw/**)`
and `Write(./data/raw/**)` bind only those two tools, and the PostToolUse
hook matches `Edit|Write`, so a Bash `cp` never reaches it. Before the fix,
a tampered CSV with the same columns and the `casual + registered == cnt`
identity intact passes every test and silently changes the metrics.

**Run by hand** in a separate clone, from a plain terminal (no agent):

```
$ git checkout 909fbc7~1
HEAD is now at e1cb6ad Fix seeded fault 3: restore the raise in encode_weather (1 agent turn)
$ cp /tmp/tampered.csv data/raw/bike_daily.csv && make test | tail -1
18 passed in 2.20s
```

Before the fix the tampered file passes the whole suite. After it, on `main`:

```
$ cp /tmp/tampered.csv data/raw/bike_daily.csv && make test | tail -3
make: *** [test] Error 1
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: bike...
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: bike_daily...
2 failed, 3 passed, 14 errors in 1.93s
$ git checkout -- data/raw/ && shasum -a 256 data/raw/bike_daily.csv
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv
```

Every test that loads the data errors on the hash check, `test_raw_data_is_unmodified`
fails, and the file is restored to the audited hash.

**What would catch it.**
- A **hash check** on the raw file in the pipeline and the tests
  (implemented, below). It catches any change, from any tool or person.
- A **PreToolUse hook on `Bash`** that rejects commands writing under
  `data/raw/`. It stops the agent before the write, but pattern-matching
  shell commands is easy to evade (`cp`, `mv`, `>`, `python -c`, ...).
- **Filesystem permissions**: `chmod -w data/raw/bike_daily.csv`. This
  binds every process, not just the agent.
- A **Stop hook** running `make test`, which with the hash test in place
  blocks "done" while the file differs.

**Implemented: SHA-256 check** (commit `909fbc7`). `src/config.py` gains
`RAW_SHA256`. `src/ingest.verify_raw()` runs inside `load_raw()`, so every
stage fails, and `tests/test_contract.py::test_raw_data_is_unmodified`
makes `make test` fail too.

```diff
+def verify_raw(path=None) -> None:
+    path = path or RAW
+    digest = hashlib.sha256(path.read_bytes()).hexdigest()
+    if digest != RAW_SHA256:
+        raise ValueError(
+            f"{path.name} has sha256 {digest[:16]}..., expected {RAW_SHA256[:16]}...: "
+            "raw data was modified. Restore it with `git checkout -- data/raw/`."
+        )
```

Checked against the tampered copy, outside the repo:

```
ValueError: bike_daily_tampered.csv has sha256 0a0416c1bc21a1d5..., expected a6bed1577f6e4de5...: raw data was modified. Restore it with `git checkout -- data/raw/`.
```

**To reproduce the fault yourself** (restores the file at the end):

```bash
.venv/bin/python -c "import pandas as pd; df=pd.read_csv('data/raw/bike_daily.csv'); df.loc[df.dteday=='2012-07-04','temp']-=10; df.to_csv('/tmp/tampered.csv', index=False)"
git stash -u; git checkout 909fbc7~1          # before the hash check
cp /tmp/tampered.csv data/raw/bike_daily.csv && make test | tail -1   # expect: all pass
git checkout -- data/raw/ && git checkout main && git stash pop
cp /tmp/tampered.csv data/raw/bike_daily.csv && make test | tail -3   # expect: red
git checkout -- data/raw/ && shasum -a 256 data/raw/bike_daily.csv    # a6bed1577f6e4de5...
```

## Exercise 1: the cnt_roll_28 test, failing before the feature existed

Commit `a9ee4c5` (test only). `make test`:

```
The above exception was the direct cause of the following exception:
E   KeyError: 'cnt_roll_28'
/Users/eubin/Downloads/bikeshare-open/.venv/lib/python3.12/site-packages/pandas/core/indexes/base.py:3648: KeyError: 'cnt_roll_28'
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_roll_28_is_mean_of_28_strictly_earlier_days
1 failed, 15 passed in 1.15s
```

It fails for the right reason: the column does not exist yet. Commit `55ee7cb` adds the feature and the suite goes to 16 passed.
