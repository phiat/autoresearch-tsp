#!/usr/bin/env bash
# PreToolUse hook: hard-block edits to frozen files.
# Reads JSON from stdin: { tool_name, tool_input: { file_path, ... }, ... }
# Exit 0 = allow. Exit 2 = block (stderr is shown to the model).
set -u

payload="$(cat)"

path="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("file_path", ""))
except Exception:
    print("")
' 2>/dev/null || true)"

[ -z "$path" ] && exit 0

# Normalize: strip trailing slash, get basename
base="$(basename "$path")"

case "$base" in
    prepare.py)
        echo "BLOCKED: prepare.py is frozen by program.md (defines TIME_BUDGET, score_tour, data loader). Edit solve.py instead." >&2
        exit 2
        ;;
esac

# Block edits to files that program.md says belong to recap-writer / paper-researcher
case "$base" in
    recap-*.md)
        echo "BLOCKED: recap files are owned by the recap-writer subagent. Use /recap to update." >&2
        exit 2
        ;;
esac

exit 0
