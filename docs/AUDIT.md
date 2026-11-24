# Audit (Exercise 3)

> **TODO(you): this file needs a teammate's repository.** Fill in each
> section, then delete this note.

## Repository audited

TODO: teammate's repository URL and the commit audited (`git rev-parse HEAD`).

## How it was run

```bash
git clone <teammate-url> ../teammate-repo
cd ../teammate-repo && claude        # from the teammate's repo root
# inside Claude Code:
#   /agents  -> confirm leakage-auditor is listed
#   Use the leakage-auditor subagent to audit this repo against its first commit.
```

Model: TODO (e.g. `bikeshare-coder` = qwen3.5:9b via Ollama, 64k context).

## `/leakage-auditor` output, verbatim

```
TODO: paste the subagent's full reply here, unedited.
```

## My verdict

TODO: one paragraph, in your own words. For each finding: does it change a
number in their `reports/metrics.json` or invalidate a conclusion in their
report? Say which findings you agree with and which you reject, and why. If
the auditor found nothing, say so and keep the output above as evidence that
it ran. Keep the auditor's claims (above) separate from your judgement (here).

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
