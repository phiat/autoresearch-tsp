#!/usr/bin/env bash
# PreToolUse hook on Bash: hard-block any command that adds a dependency
# beyond the pre-approved set (numpy, pandas, sympy, scipy, numba).
# Exit 2 blocks; stderr is shown to the model.
set -u

payload="$(cat)"

cmd="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null || true)"

[ -z "$cmd" ] && exit 0

# Patterns that introduce or modify deps. Conservative — match the action,
# not just the word "install" (so `apt-get install -y nvidia-docker` style
# system commands aren't accidentally caught by an unrelated word).
forbidden_patterns=(
    'uv add '
    'uv pip install'
    'pip install'
    'pip3 install'
    'pipx install'
    'poetry add '
    'conda install'
    'mamba install'
)

for pat in "${forbidden_patterns[@]}"; do
    if printf '%s' "$cmd" | grep -qF -- "$pat"; then
        echo "BLOCKED: dependency installation is gated. Allowed deps: numpy, pandas, sympy, scipy, numba. New deps require explicit human approval — stop the loop and ask." >&2
        echo "Matched pattern: $pat" >&2
        exit 2
    fi
done

exit 0
