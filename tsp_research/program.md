# tsp_research

Autonomous LLM research loop for the Kaggle Traveling Santa 2018 Prime Paths
problem. Same shape as karpathy/autoresearch, different task: combinatorial
optimisation instead of language modelling.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr25`).
   The branch `tsp/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b tsp/<tag>` from current main.
3. **Read the in-scope files**:
   - `README.md` — repo context.
   - `prepare.py` — frozen data loader, `score_tour()` metric, time budget.
     **Do not modify.**
   - `solve.py` — the file you modify. Solver lives here.
4. **Verify data exists**: `data/cities.csv` should be present (197,769 rows).
   If not, ask the human to unzip the Kaggle archive into `data/`.
5. **Smoke test**: `uv run prepare.py` — should print N=197769 and a baseline
   identity-tour cost without errors.
6. **Initialize results.tsv**: create with header row only. Baseline goes in
   after the first real run.
7. **Confirm and go.**

## Experimentation

Each experiment runs a single solver attempt with a **fixed wall-clock
budget of 5 minutes** for the solver itself (excluding data load + final
scoring). Launch as: `uv run solve.py`.

**What you CAN do:**
- Modify `solve.py` — algorithm, data structures, neighbourhood moves,
  meta-heuristics, ML-guided steps, anything. You may add new helper
  files/modules in `tsp_research/` if the architecture demands it, but
  `solve.py` remains the entry point.

**What you CANNOT do:**
- Modify `prepare.py`. Read-only. It defines the metric (`score_tour`),
  the time budget, the data loader, and the prime mask.
- Add dependencies beyond what's already in `pyproject.toml` without
  asking the human first. The pre-approved set is: `numpy`, `pandas`,
  `sympy`, `scipy`, `numba`. Anything else needs sign-off.
- Rewrite the scoring function or change tour validation.

## The idea library (`ideas.md`)

`ideas.md` is the seeded pool of experiment ideas (construction, local
search, perturbation, prime-aware tweaks, data-structure work,
hyperparam sweeps, pipelines). Treat it as your catalogue.

**Each cycle:**

1. Read `ideas.md`. Build the set of items NOT already present in the
   `description` column of `results.tsv`.
2. Pick uniformly at random from that untried set. (If the untried set
   is empty, pick the lowest-scoring previous idea and try a tweaked
   variant.) Bias toward whichever item-class — construction /
   local-search / perturbation / prime / engineering / hyperparam /
   pipeline — is currently underrepresented in the log.
3. Implement that one idea as a focused `solve.py` change. Do not
   bundle ideas. The picked idea is what the description in
   `results.tsv` will say.

**Every 5 logged experiments:** append 2-3 NEW ideas to `ideas.md`
under a new `## Appended (cycle N)` heading. Base them on what the log
has shown — variants of what worked, removals of what failed, adjacent
techniques the literature suggests. Append-only; never delete or
rewrite older entries.

**The goal: minimise val_cost.** The metric is the official Kaggle Santa
2018 cost — euclidean tour length with a 1.1× multiplier on every 10th step
whose origin city is not prime. Lower is better.

**Memory** is a soft constraint. The 4070 has 16 GB VRAM and the host has
ample RAM; don't blow either out.

**Simplicity criterion**: same as autoresearch. Big complexity for tiny
gains is not worth it. Removing code to get equal or better results is a
strong positive signal.

**The first run**: baseline. Run `solve.py` unmodified (nearest neighbor
from city 0). Record the val_cost in results.tsv.

## Output format

`solve.py` prints a summary block:

```
---
val_cost:         1533421.7654
solve_seconds:    298.4
total_seconds:    312.8
n_cities:         197769
submission:       submissions/submission.csv
```

Extract the metric:
```
grep "^val_cost:" run.log
```

## Logging results

After each experiment, append a row to `results.tsv` (TAB-separated):

```
commit	val_cost	solve_seconds	status	description
```

1. short git commit hash (7 chars)
2. `val_cost` from the run (e.g. 1533421.7654) — use `0` for crashes
3. solver wall-clock seconds (e.g. 298.4) — use `0` for crashes
4. status: `keep`, `discard`, or `crash`
5. one-line description of what this experiment tried

Example:

```
commit	val_cost	solve_seconds	status	description
a1b2c3d	1733204.0510	297.1	keep	baseline (nearest neighbor from city 0)
b2c3d4e	1612889.1922	299.3	keep	+ 2-opt sweep until budget exhausted
c3d4e5f	1640102.7740	298.0	discard	tried christofides scaffold, no improvement
d4e5f6g	0	0	crash	scipy KDTree call with bad k argument
```

`results.tsv` is gitignored — local-only ledger.

## The experiment loop

LOOP FOREVER:

1. Inspect git state (current branch/commit).
2. Edit `solve.py` with the next experimental idea.
3. `git commit -am "exp: <short description>"`
4. `uv run solve.py > run.log 2>&1`
   (redirect everything; do NOT use `tee` — it will flood your context)
5. `grep "^val_cost:\|^solve_seconds:" run.log`
6. If grep is empty the run crashed. `tail -n 50 run.log` for the
   traceback. Fix obvious bugs and retry once; if it's a fundamentally
   broken idea, log "crash" and move on.
7. Append to `results.tsv`. Do NOT commit it.
8. If `val_cost` improved, advance the branch (keep the commit).
9. If equal or worse, `git reset --hard HEAD~1` to drop the experiment.

**Timeout**: each run should take ~5 min solver + a few seconds for load
and scoring. If a run exceeds 10 minutes wall-clock total, kill it and
treat as a crash.

**NEVER STOP**: once the loop is running, do not pause to check in. The
human may be asleep or away. Iterate until interrupted. Out of ideas?
Re-read `ideas.md` (your library — sample from it), then `prepare.py`,
`solve.py`, this file. Append fresh ideas to `ideas.md` per the growth
protocol. Look up: 2-opt, Or-opt, Lin-Kernighan, LKH-3, segment
reversal, candidate lists, k-d tree neighbour pruning, simulated
annealing, large-neighbourhood search, guided local search,
Concorde-style cuts. The prime-step penalty is small (~10% of every
10th step) so most generic TSP moves transfer. Try combining
near-misses. Try more radical changes. The loop runs until the human
stops you.
