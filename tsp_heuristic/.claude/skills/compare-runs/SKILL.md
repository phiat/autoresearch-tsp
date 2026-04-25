---
name: compare-runs
description: Diff solve.py between two commits and pair with their val_cost / solve_seconds rows from results.tsv. Use when an experiment regressed unexpectedly, when two ideas in the same class produced very different deltas, or when planning to combine two prior keeps.
---

# compare-runs

Side-by-side diff of two solve.py versions plus their measured deltas.

## Inputs

Two commit short hashes — call them `A` and `B`. If only one is given,
compare it against `HEAD`. If none are given, compare the two most
recent rows in `results.tsv`.

## Procedure

1. From `results.tsv`, fetch the rows for `A` and `B`. Capture
   `val_cost`, `solve_seconds`, and `description`.
2. Run `git diff <A> <B> -- solve.py` and read the patch.
3. Read both versions of `solve.py` in full *only if* the diff is
   trivially small or you need control-flow context.
4. Produce a structured comparison.

## Output template

```
A: <hash> — <description>  (val_cost=<X>, solve_seconds=<S>)
B: <hash> — <description>  (val_cost=<Y>, solve_seconds=<S>)

Δ val_cost: <Y-X>  (B is <better/worse> by <pct>%)
Δ solve_seconds: <SB-SA>

Code changes (summary, not full diff):
  - <bullet 1>
  - <bullet 2>

Likely cause of the delta:
  <one-paragraph hypothesis tying code changes to the metric move>

Implication for next experiment:
  <single recommendation: e.g. "the cKDTree query in B added 8s of
  overhead per ILS iter — try caching once outside the loop (D1)">
```

## When NOT to use this

- For pulling raw diffs. Use plain `git diff` for that.
- For deciding keep/revert — the loop already does that mechanically.
- For comparing more than 2 runs. Use a recap update instead.

## Caveats

- `val_cost` is stochastic when ILS uses random perturbations. A
  difference of <0.01% across two runs of the *same* code is noise,
  not signal.
