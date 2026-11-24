# Forecasting daily bikeshare demand: report

> **DRAFT.** Sections marked **TODO(you)** are judgement calls the rubric
> requires to be yours. Delete this note and every TODO before submitting.

## Results

All numbers are from `make all`: the "after" rows are `reports/metrics.json`,
the "before" rows are `reports/metrics_before_feature.json` (the same command
run on the unmodified starter, commit `a2fabd7`). Train = 2011, validation =
H1 2012, test = H2 2012. R² is computed against each split's own mean, so 0
means "as good as a constant nobody could have known in advance".

| Model | Features | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| `baseline_mean` | before (14 features, LAG_WARMUP 7) | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| `baseline_persistence` | before (14 features, LAG_WARMUP 7) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| `ridge` | before (14 features, LAG_WARMUP 7) | 0.6475 | 832.9 | 0.5833 | 947.1 |
| `hgb` | before (14 features, LAG_WARMUP 7) | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| `baseline_mean` | after (+ `cnt_roll_28`, LAG_WARMUP 28) | -0.6894 | 1877.3 | -1.7717 | 2659.6 |
| `baseline_persistence` | after (+ `cnt_roll_28`, LAG_WARMUP 28) | 0.4507 | 900.6 | 0.5099 | 840.1 |
| `ridge` | after (+ `cnt_roll_28`, LAG_WARMUP 28) | 0.6839 | 777.5 | 0.6239 | 879.3 |
| `hgb` | after (+ `cnt_roll_28`, LAG_WARMUP 28) | 0.2415 | 1296.6 | -0.46 | 1952.4 |

Rows: before train/valid/test = 348/182/184; after = 306/182/184.

The persistence rows are identical before and after. The longer warm-up only
removes January 2011 rows from *training*, and persistence fits nothing. The
mean baseline improves (−0.93 → −0.69 on validation) for the same reason: the
dropped rows were the lowest-demand days, so the 2011 mean moved toward 2012.

## Headline finding

A naive evaluation scores R² = 1.000 (`python -m src.leakage_demo`), and it is
invalid: `casual + registered == cnt` on every row, so the model learns
addition. Under a temporal split, predicting the 2011 mean scores −1.77 on the
H2 2012 test set, because ridership grew about 65% (test mean 6,043 rides a
day). Ridge on audited features reaches **0.6239** test R² against a
persistence baseline ("yesterday's count") of **0.5099**, but it still loses to
persistence on MAE (879.3 vs 840.1 rides). Gradient boosting scores −0.46. That
is far better than the mean baseline, but it cannot predict above the largest
count it saw in training (6,043, on 2011-07-04), and 57% of test days exceed it.

Adding `cnt_roll_28` (the mean of the previous 28 days) raised validation R²
on identical training rows from 0.6462 to 0.6839 for ridge and from 0.1929 to
0.2415 for gradient boosting. **TODO(you): one sentence: did you keep it, and
why?** (The table's "after" rows assume it is kept. If you drop it, revert
commit `62589b6`, rerun `make all`, and regenerate this table.)

## Exercise 4: target transformation

Gradient boosting fails because a tree predicts by averaging training targets,
so it cannot extrapolate a growing level. The fix tried: predict demand
*relative to recent demand*, then convert back to rides. Code:
`src/train.py --target-transform {ratio,diff} --base <lag column>`
(`RelativeTarget`). The committed `reports/metrics.json` is untransformed.

Validation only. **The test set has not been touched for this exercise.**

| Variant | Ridge valid R² | HGB valid R² |
|---|---|---|
| untransformed | 0.6839 | 0.2415 |
| ratio to `cnt_roll_28` | 0.4039 | 0.6754 |
| ratio to `cnt_roll_7` | 0.4380 | 0.7329 |
| ratio to `cnt_lag_7` | −1.1804 | 0.3453 |
| difference from `cnt_roll_28` | 0.6932 | 0.6950 |
| difference from `cnt_roll_7` | 0.6849 | 0.7139 |
| difference from `cnt_lag_7` | 0.6839 | 0.4811 |

Every transform based on a rolling mean lets the tree compete (0.68–0.73,
against 0.24 untransformed), because the tree now predicts a ratio or offset
that stays inside its training range. A ratio hurts ridge (a linear model of a
ratio, multiplied back by the level, is no longer linear in the features). A
difference leaves ridge essentially unchanged.

**TODO(you):**
1. Pick **one** variant and say why, *before* scoring the test set. Six
   variants on 182 validation days means the best one is partly selected by
   noise.
2. Score the test set once:
   `.venv/bin/python -m src.train --target-transform <mode> --base <col> --final`,
   and paste the test R² and MAE here, saying it was run once.
3. Decide: defensible, or a way to win the comparison? Points to weigh:
   relative-to-recent-demand is a standard way to model a trending series and
   uses only past data, but the gain might come from the transform doing the
   extrapolation rather than the tree learning anything. Compare the
   transformed tree with the transformed ridge, not just with untransformed
   ridge.

## Exercise 5: ridge vs persistence

**TODO(you): one paragraph arguing that ridge is, or is not, worth deploying
over "yesterday again".** Either answer is accepted; an unargued one is not.
Evidence (test set, after the feature, ridge as in `metrics.json`):

- Test R² 0.6239 vs 0.5099 (+0.11), but MAE 879.3 vs 840.1: ridge is *worse*
  on the average day.
- Median absolute error: ridge 807, persistence 506. Ridge is closer on only
  43% of the 184 test days (52% of validation days).
- On the 52 test days where demand changed by more than 1,000 rides from the
  day before, ridge MAE is 1,196 vs 1,977. On the other 132 days it is 755
  vs 392. Ridge wins on big swings, which drive R², and loses on calm days,
  which drive MAE.
- 90th-percentile error: ridge 1,711 vs 1,960.
- Ridge is biased low by 427 rides a day on test (+396 on validation): it was
  fit on 2011 levels.
- Standardised coefficients: `cnt_roll_7` 403, `cnt_lag_1` 321,
  `weather_severity` −290, `temp` 228, `cnt_roll_28` 165, `windspeed` −160,
  `hum` −121. It is more than "yesterday again": weather moves the forecast.

## Attribution

**TODO(you): confirm this line.** Agent: Claude Code driving **Claude Opus 5.5**
(hosted, Anthropic), not a local model. That model did the code, tests, fault
seeding and docs in this repo. The local open-weight model `qwen3.5:9b`
(Ollama, built as `bikeshare-coder`, 64k context) was used only to run
`agent/audit.py` (`reports/audit.jsonl`) **TODO: and /leakage-auditor in
docs/AUDIT.md, if you run it with qwen**. Models were switched between those
two tasks.

**Generated by the agent:**
- `src/features.py`: `cnt_roll_28`; literal window lengths for `cnt_lag_7` / `cnt_roll_7`
- `src/config.py`: `LAG_WARMUP = 28`, `RAW_FEATURE_COLS` / `ENCODED_COLS` / `IGNORED_COLS`, `RAW_SHA256`
- `src/ingest.py`: `verify_raw`
- `src/train.py`: `RelativeTarget`, `--target-transform` / `--final` flags
- `tests/test_leakage.py`: `test_lag_7_is_a_true_seven_day_lag`, `test_roll_28_is_mean_of_28_strictly_earlier_days`, `test_weather_encoder_rejects_unknown_labels`
- `tests/test_contract.py`: `test_every_raw_column_is_classified`, `test_raw_data_is_unmodified`
- `.claude/hooks/check_leakage.sh` venv fix; `Makefile` venv and `make model` fixes
- `.claude/skills/seed-fault/SKILL.md`
- `docs/SEEDED_FAULTS.md`, drafts of this report and of `docs/DECISIONS.md` entries
- The analyses in Exercises 4 and 5 (numbers only)

**Decisions that were mine:** **TODO(you): keep this list short, make it
true, and make every item match a line in `docs/DECISIONS.md`.**
Expected items: whether to keep `cnt_roll_28`; which Exercise 4 variant to
use and whether it is defensible; your Exercise 5 position; accepting the
leakage / split / baseline rules from the starter (or changing them).
