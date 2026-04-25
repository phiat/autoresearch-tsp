---
name: chart-progress
description: Regenerate <repo-root>/progress.png — the README's chart of best val_cost over cycle index for both loops, with SOTA reference line. Use after every recap-tick (every 4 cycles), after a notable new best, or any time the chart looks stale relative to results.tsv.
---

# chart-progress

Regenerates the cross-loop progress chart used in the outer
`README.md`. Reads both `tsp_heuristic/results.tsv` and
`tsp_neural/results.tsv`, plots cumulative-best `val_cost` over
cycle index with a horizontal SOTA reference line, writes
`<repo-root>/progress.png`.

## When to use

- After every recap-tick (every 4 logged cycles) — so the chart and
  the recap stay in sync.
- After landing a new best `val_cost` — so the README chart reflects
  the latest progress immediately.
- When the chart's mtime is older than the latest `results.tsv` row.

## Procedure

1. From your subdir (`tsp_neural/`), run:

   ```bash
   (cd .. && uv run --with matplotlib --with pandas python scripts/chart_progress.py)
   ```

   `uv run --with` uses an ephemeral venv with matplotlib + pandas
   so we don't pollute either loop's `pyproject.toml`. First run
   downloads ~10 MB of wheels; subsequent runs are cached.

2. The script writes `../progress.png` (~50–80 KB) and prints a
   short summary to stdout — number of cycles + best val_cost +
   `% SOTA` per loop.

3. Decide whether to commit:

   ```bash
   (cd .. && git diff --quiet progress.png) && echo "(unchanged)" || echo "changed"
   ```

   If changed, commit from the repo root:

   ```bash
   (cd .. && git add progress.png && \
     git commit -m "meta: chart progress (neural cycle <N>)")
   ```

   Push if you're maintaining the README's freshness; otherwise the
   chart commit lands on `main` next time something else pushes.

## Output

A 3-4 line confirmation in the format:

```
chart-progress: wrote progress.png (<size> KB)
  tsp_heuristic   <N> cycles  best=<...>  (<pct>% SOTA)
  tsp_neural      <M> cycles  best=<...>  (<pct>% SOTA)
status: <committed | unchanged>
```

## What you must NOT do

- Do not add matplotlib or pandas to `pyproject.toml`. The
  `--with` flag keeps them out of the loop's locked deps.
- Do not change the SOTA reference (1,514,000) without explicit
  approval — it's the public-LB anchor for the badges.
- Do not commit `progress.png` if it's bit-identical to the prior
  version (the diff check above prevents binary churn).
- Do not edit `scripts/chart_progress.py` from this skill — that
  belongs to the `evolve-tooling` skill if the chart's shape needs
  to change.
