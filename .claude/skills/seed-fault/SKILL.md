---
name: seed-fault
description: Deliberately break the pipeline in one named way, record what catches it (tests, hook), then restore and commit. Use when asked to seed, inject, or test a fault, or to check whether the suite would notice a specific mistake.
allowed-tools: Read, Edit, Bash(make*), Bash(python -m pytest*), Bash(.venv/bin/python*), Bash(git diff*), Bash(git status*), Bash(git add*), Bash(git commit*), Bash(git checkout*)
---

# Working tree right now

!`git status --short && git log --oneline -1`

# Fault to seed: $ARGUMENTS

If the working tree above is not clean, stop and say so: a fault seeded on
top of uncommitted work cannot be cleanly restored.

1. **Predict.** In one sentence, name the test you expect to go red, or say
   you expect the suite to stay green. Write the prediction down before
   running anything. A wrong prediction is the interesting result.

2. **Seed.** Make the smallest edit that introduces exactly this fault,
   with the Edit tool (so the PostToolUse hook sees it). Never edit
   `data/raw/`; for a raw-data fault, work on a copy outside the repo.

3. **Record, verbatim.** Paste, do not summarise:
   - `git diff -- src/ tests/`
   - `.venv/bin/python -m pytest tests/ -q --tb=line` (last 15 lines)
   - the hook's stderr and exit code, by piping the payload it receives:
     `echo '{"tool_name":"Edit","tool_input":{"file_path":"'$PWD'/<file>"}}' | CLAUDE_PROJECT_DIR=$PWD bash .claude/hooks/check_leakage.sh`

4. **Commit the fault** as `Seeded fault N: <what>`, stating whether the
   suite went red and the hook's exit code.

5. **If the suite stayed green**, the fault is invisible. Write a test that
   fails *because of this fault*, commit it separately while the fault is
   still in place, and paste its red output.

6. **Restore** with `git checkout <last good commit> -- <file>`, run
   `make test`, and commit `Fix seeded fault N: <what> (<k> agent turns)`,
   counting each tool call you needed to get back to green.

7. **Append** the diff, outputs, prediction vs result and turn count as a
   section of `docs/SEEDED_FAULTS.md`.

Report in three lines: what was seeded, what caught it (or that nothing
did), and the new test if one was needed.
