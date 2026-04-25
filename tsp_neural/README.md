# tsp_neural

Sibling to `tsp_research/` — same Santa 2018 TSP, same metric, same
5-min budget, but the agent's lever is **training a small neural
network to guide the local-search inner loops**, not hand-designing
classical heuristics.

This is **Option B2** ("neural-guided local search") from the project's
options menu. Not a pure neural solver: classical pipeline (NN seed →
2-opt → submission) stays intact, the network's role is to *score
candidate moves* better than the geographic k-NN heuristic does.

## Files

```
prepare.py        — frozen: same as tsp_research/ (load_cities, score_tour)
solve.py          — agent's playground; baseline = NN + 2-opt(k=10), no learning
program.md        — agent operating rules, neural-augmentation focus
ideas.md          — seeded ideas in M/T/R/I/E/C classes
AGENTS.md         — tooling inventory + decision table
justfile          — common shell recipes (run, train, harvest, …)
pyproject.toml    — deps: numpy, pandas, sympy, scipy, numba, torch

data/             — symlink to ../tsp_research/data/ (shared)
moves/            — harvested move logs (gitignored)
checkpoints/      — saved model weights (gitignored)
submissions/      — solver output (gitignored)
results.tsv       — local experiment ledger (gitignored)
.claude/          — subagents, skills, slash commands, hooks
```

## Quick start

```bash
# 1. Make sure ../tsp_research/data/cities.csv exists (the symlink resolves there)
# 2. Sync deps (this downloads PyTorch — several GB, one-time)
uv sync

# 3. Smoke test
just data
just run
just metrics
```

Baseline `val_cost` will be roughly **1.55-1.6M** — worse than
`tsp_research/`'s current best because the baseline here intentionally
*lacks* Or-opt / ILS / prime-aware moves. Those are not the
differentiator. The agent's job is to introduce learning, not to
re-build the classical pipeline.

## Common commands

```bash
just                  # list all recipes
just status           # branch, head, last result, recap-pending
just run              # one experiment (5-min budget)
just metrics          # extract val_cost from run.log
just ledger           # pretty-print results.tsv
just exp "<desc>"     # commit experiment with exp: prefix
just log <args>       # append a row to results.tsv
just revert           # discard last commit
just train            # convenience: launch a training-only run (see justfile)
just harvest          # run solve.py with move-logging enabled
just tools            # list .claude/ subagents/skills/commands/hooks
```

## How this differs from tsp_research/

|                  | `tsp_research/`              | `tsp_neural/`                 |
|------------------|------------------------------|-------------------------------|
| Approach         | classical heuristic search   | neural-guided local search    |
| Has a model?     | no                           | yes (small, trained per cycle)|
| Lever for the agent | algorithm design          | model design + integration    |
| Deps             | numpy/scipy/numba            | + PyTorch                     |
| Idea library     | C/L/O/P/Z/D/H/X classes      | M/T/R/I/E/C classes           |
| GPU?             | no                           | yes (4070, ~16GB)             |
| Risk             | low; classical literature deep | high; learned + classical glue is fiddly |

Both projects share `prepare.py` (the metric is identical) and the
same harness shape. They live as siblings so you can compare scores
on the same submission.

## Provenance

Inspired by the same lineage as `tsp_research/` —
[karpathy/autoresearch](https://github.com/karpathy/autoresearch),
the [Kaggle Santa 2018](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/),
and the marimo walkthrough video.
