---
description: Update or create the next recap-N.md by delegating to the recap-writer subagent.
---

Invoke the `recap-writer` subagent to refresh the recap series.

Pass it whatever extra context the user supplied after `/recap` (e.g. a
specific cycle range, "focus on Or-opt", etc.). If nothing was passed,
just tell the subagent: "refresh the recap based on current state of
results.tsv, ideas.md, and git log; either update the latest
recap-N.md or start recap-(N+1).md per its own decision rules."

After the subagent returns, surface its one-line confirmation to the
user verbatim. Do not duplicate or expand it.
