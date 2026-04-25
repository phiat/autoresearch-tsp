---
name: postmortem
description: Structured analysis of the loop's recent state — reads results.tsv, recent commits, and the latest recap to identify the current bottleneck and the highest-EV next direction. Use every ~5-10 cycles, when stuck on a plateau, or before triggering paper-researcher.
---

# postmortem

Pause the loop, look at what's happening, identify the bottleneck.

## When to use

- Several recent runs in a row have produced near-zero deltas (loop
  is on a plateau).
- A class of ideas has produced a string of discards.
- About to invoke `paper-researcher` and want a sharper query than
  "TSP heuristics, please."
- The recap-writer is about to fire and would benefit from your
  conclusions.

## Inputs

None required. The skill reads:
- `results.tsv` (last 8-12 rows)
- `git log --oneline -15`
- `ideas.md`
- the latest `recap-*.md`

## Procedure

1. **Tabulate recent state**: last 8 logged rows of `results.tsv`,
   their commit, val_cost, status, description.
2. **Detect patterns**:
   - Class distribution of recent keeps vs discards (which classes
     are paying off, which are dead).
   - Magnitude of recent deltas (are they decreasing toward zero — a
     plateau — or oscillating?).
   - Time spent: is solve_seconds always 300.0 (capped) or are some
     experiments terminating early?
3. **Diagnose the bottleneck** — pick exactly one of:
   - **Algorithmic**: current move set is saturated, need a new one.
   - **Engineering**: algorithms have headroom but can't fit in budget;
     speed-up ideas (D-class) are the unlock.
   - **Diversification**: stuck in a basin; need stronger perturbation
     (P-class) or multi-start (C-class).
   - **Metric mismatch**: improving euclidean tour but the prime
     penalty is the residual cost; need Z-class moves.
4. **Recommend** exactly one next idea and one fallback. Pull from
   `ideas.md` if a fitting item exists; otherwise propose a new
   1-line entry in the right class and suggest invoking
   `paper-researcher` with a specific query.

## Output template

```
Postmortem on cycles <a>..<b>:

Recent results (last 8):
  <#>  <hash>  <val_cost>  <status>  <one-line desc>
  ...

Patterns:
  - <pattern 1>
  - <pattern 2>

Bottleneck: <one of the four categories above>
  Why: <one-paragraph evidence-based justification>

Next: <single specific idea, with idea-class tag>
Fallback: <one alternative if first fails>

Suggested paper-researcher query (if neither fits): "<query>"
```

## What you must NOT do

- Do not edit `solve.py`, `results.tsv`, or `ideas.md`. This skill is
  read-only analysis. Idea additions should go through the normal
  growth protocol or `paper-researcher`.
- Do not write a recap. That's `recap-writer`'s job.
- Do not declare "the loop is done." There is no done; only longer
  plateaus.
