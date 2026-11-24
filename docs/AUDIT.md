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

`reports/audit.jsonl` is one run of `python agent/audit.py <this repo> --out
reports/audit.jsonl` against this repository with the local `bikeshare-coder`
model. See REPORT.md if it flagged anything.
