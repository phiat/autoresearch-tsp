#!/usr/bin/env bash
# PostToolUse hook: every 4 logged cycles, write .recap-pending so the
# next loop iteration knows to invoke /recap.
# Always exits 0 — non-blocking. Internal errors are silent.
set -u

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

results="results.tsv"
pending=".recap-pending"

[ -f "$results" ] || exit 0

# Row count excluding header.
total_lines=$(wc -l < "$results" 2>/dev/null || echo 0)
n=$((total_lines - 1))
[ "$n" -gt 0 ] || exit 0

# Trigger every 4 cycles.
[ $((n % 4)) -eq 0 ] || exit 0

# Idempotency: don't re-write if we already flagged this n.
last="$(cat "$pending" 2>/dev/null || echo 0)"
[ "$last" = "$n" ] && exit 0

printf '%s\n' "$n" > "$pending"

# Stderr from PostToolUse hooks is shown back to the model in newer
# Claude Code versions; harmless if not.
echo "📒 Recap due: $n logged cycles. Run /recap (delegates to recap-writer subagent)." >&2

exit 0
