# Forecasting daily bikeshare demand: report

> **DRAFT.** Sections marked **TODO(you)** are judgement calls the rubric
> requires to be yours. Delete this note and every TODO before submitting.

## Results

All numbers are from `make all`: the "after" rows are `reports/metrics.json`,
the "before" rows are `reports/metrics_before_feature.json` (the same command
run on the unmodified starter, commit `fe101a9`). Train = 2011, validation =
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
0.2415 for gradient boosting. I kept it: both gains are well above the 0.01
noise floor, and the cost is 42 fewer 2011 training rows (348 → 306).

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

**Chosen variant: difference from `cnt_roll_7`.** It is the only variant near
the top for both models (ridge R² 0.6849, gradient boosting R² 0.7139 on
validation). The ratio variants score higher for the tree but drop ridge to
R² 0.40–0.44.

**Test set, scored once** after choosing (commit `2c03b3e`,
`reports/metrics_diff_cnt_roll_7.json`):

| Model | Test R² | Test MAE |
|---|---|---|
| gradient boosting, untransformed | −0.46 | 1952.4 |
| gradient boosting, difference from `cnt_roll_7` | 0.6331 | 830.1 |
| ridge, untransformed | 0.6239 | 879.3 |
| ridge, difference from `cnt_roll_7` | 0.6228 | 880.3 |
| persistence | 0.5099 | 840.1 |

**Verdict: defensible.** It fixes a known limitation of trees (they cannot
predict outside their training range) using only past data: `cnt_roll_7` on
date d is built from d−7 … d−1. The transformation leaves ridge unchanged,
which is consistent with it fixing the tree's extrapolation problem rather
than adding information. The committed `reports/metrics.json` remains the
untransformed pipeline.

## Exercise 5: ridge vs persistence

**Persistence is the better choice to deploy.** On the H2 2012 test set, ridge
has the higher R² (0.6239 vs 0.5099) but the higher MAE (879.3 vs 840.1) and
median error (807 vs 506), and it is closer to the truth on only 43% of the
184 days. The two metrics disagree because R² squares errors, so the few
large misses dominate it. On the 52 days where demand moved by more than
1,000 rides from the day before (a threshold chosen for this analysis), ridge
errs by 1,196 rides on average against persistence's 1,977, saving about
(1,977 − 1,196) × 52 ≈ 40,600 rides of error. On the other 132 days it errs by
755 against 392, adding about (755 − 392) × 132 ≈ 47,900. Net, ridge is about
7,300 rides worse over the half-year, matching its MAE gap (39.2 rides × 184
days ≈ 7,200; the small difference is rounding in the per-group averages). Since the
typical daily error is the cost that matters here, persistence wins. Ridge
would be the better choice if a large miss cost far more than a small one,
and it has a fixable flaw: it underpredicts by about 427 rides a day because
it was fit on 2011 levels.

Supporting numbers (test set, after the feature, ridge as in `metrics.json`):

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

Agent: Claude Code driving **Claude Opus 5.5**
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

**Decisions that were mine** (each has a line in `docs/DECISIONS.md`):
- Keep `cnt_roll_28` (the agent proposed the feature).
- Exercise 4: use the difference from `cnt_roll_7`, chosen on validation
  before one test run; judged defensible.
- Exercise 5: persistence over ridge for deployment, on MAE.
- TODO(you): items still under review; see the end of this conversation.
