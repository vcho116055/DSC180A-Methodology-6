#!/usr/bin/env bash
# PostToolUse hook: re-run the leakage tests whenever src/ changes.
#
# This runs AFTER the edit has landed, so it cannot prevent the write. What
# exit 2 does is send stderr back to Claude as a system message, so the
# failure is in front of the agent immediately and it cannot carry on as if
# the edit were fine. To make "done" itself conditional on green tests, add
# a Stop hook that runs `make test` and exits 2 on failure (check
# stop_hook_active in the payload to avoid looping).
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
PY=""
for c in .venv/bin/python .venv/Scripts/python.exe; do
  [ -x "$c" ] && PY=$c && break
done
[ -n "$PY" ] || PY=$(command -v python3 || command -v python)

payload=$(cat)
path=$(printf '%s' "$payload" | "$PY" -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
path=${path//\\//}

case "$path" in
  *src/*.py) ;;
  *) exit 0 ;;
esac

if ! out=$("$PY" -m pytest tests/test_leakage.py -q 2>&1); then
  echo "Leakage tests failed after editing $path:" >&2
  echo "$out" | tail -20 >&2
  exit 2
fi
exit 0
