---
name: multi-seed-eval
description: Re-run the most recent experiment (or a specified solve.py state) with 2-3 different rng seeds, report median val_cost. Use BEFORE declaring a discard whose |delta vs best| < 750 (1.5× the empirical noise floor). Catches false discards where a single-seed result happened to land in a worse basin.
---

# multi-seed-eval

The single-seed solver is rng-luck-dependent (cycles 39-45 PILS knob-sweep proved
this empirically: noise variance across PILS workers around ~250). The
**noise floor for the neural loop is ~250-500 cost units**. Discards
within ±750 of the prior best may be false negatives — same algorithm,
different basin under that seed.

This skill protects against accepting a "worse" result that is in
fact statistically equivalent.

## When to use

- A candidate experiment just produced |val_cost − best| < 750 and
  you're about to mark it `discard`. Run multi-seed FIRST.
- Anytime a "near-miss" (within 1.5× noise floor) appears in
  results.tsv that you suspect was real.
- After a structural change (architectural, not hyperparam) where
  the single-seed result is hard to interpret.

## Procedure

1. **Verify the candidate's solve.py is still HEAD** (or revert
   target). If the agent already moved on, `git checkout` the
   candidate's commit first.

2. **Run 3 seeds**:
   ```bash
   for s in 1 2 3; do
     ILS_SEED=$s uv run solve.py > run.log.seed$s 2>&1
   done
   ```
   `solve.py` reads `ILS_SEED` env var to seed its rng (this hookup
   landed in the same meta commit as this skill). Default is the
   committed seed (0xCAFE for parallel ILS).

3. **Aggregate**:
   ```bash
   for s in 1 2 3; do
     printf "seed=%d  " $s
     grep "^val_cost:" run.log.seed$s
   done
   ```
   Compute median (sort, pick middle).

4. **Decision rule**:
   - **Median < prior best**: keep the candidate. Note in results.tsv
     description: `multi-seed median X.XX (seeds {1,2,3}: A, B, C)`.
   - **Median ≥ prior best AND any single-seed run < prior best**:
     mark as `tentative` — the candidate sometimes wins; needs
     larger N seeds to confirm. Discard for now but log this clearly.
   - **All 3 seeds ≥ prior best**: discard with confidence. Note
     `confirmed via multi-seed`.

5. **Cleanup**: `rm run.log.seed*` after recording.

## Output

```
multi-seed-eval summary:
  candidate:   <commit short>
  prior best:  <val>
  seed=1:      <val>  (Δ <signed>)
  seed=2:      <val>  (Δ <signed>)
  seed=3:      <val>  (Δ <signed>)
  median:      <val>
  decision:    <keep | discard | tentative>
```

## What you must NOT do

- Do not skip multi-seed for "borderline" cases that happen to fall
  on the right side of the threshold — the threshold is the rule.
- Do not adjust the `ILS_SEED` value in committed code to match a
  lucky seed. The whole point is robustness across seeds.
- Do not run more than 5 seeds without explicit human approval —
  the budget cost is real (5× the per-cycle wall-clock).
- Do not invoke this when the |delta| is large enough that the
  decision is obvious (|delta| > 1500).
