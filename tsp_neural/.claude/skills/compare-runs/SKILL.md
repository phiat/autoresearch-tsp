---
name: compare-runs
description: Diff solve.py across 2-N commits and pair with their val_cost / solve_seconds rows from results.tsv. Use when an experiment regressed unexpectedly, when ideas in the same class produced very different deltas, when reviewing a hyperparam sweep across many commits, or when planning to combine multiple prior keeps.
---

# compare-runs

Side-by-side diff of N solve.py versions plus their measured deltas.

## Inputs

One or more commit short hashes — call them `A`, `B`, `C`, …. Modes:

- **2 commits**: classic A vs B diff.
- **3+ commits**: hyperparam-sweep style — show a results table
  spanning all N, then pairwise diffs for adjacent pairs (A→B,
  B→C, …) so you can see the trajectory of the changes.
- **No args**: compare the two most recent rows in `results.tsv`
  (legacy default).
- **`HEAD~N..HEAD`** range: expand to all commits in the range.

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

## Output template (3+ commits — sweep mode)

```
Sweep across N commits:

| commit  | description                              | val_cost | solve_s |
|---------|------------------------------------------|----------|---------|
| <Ah>    | …                                        | …        | …       |
| <Bh>    | …                                        | …        | …       |
| <Ch>    | …                                        | …        | …       |

Pairwise solve.py diffs (size only — full diff via `git diff`):
  A → B: +X / −Y lines
  B → C: +X / −Y lines

Pattern across the sweep:
  <one-paragraph: trend, sweet spot, regime change>

Implication for next experiment:
  <single recommendation>
```

## When NOT to use this

- For pulling raw diffs. Use plain `git diff` for that.
- For deciding keep/revert — the loop already does that mechanically.
- For comparing more than ~10 runs at once. Use a recap update or
  scripted analysis instead — readable diff dies past that scale.

## Caveats

- `val_cost` is stochastic when ILS uses random perturbations. A
  difference of <0.01% across two runs of the *same* code is noise,
  not signal.
