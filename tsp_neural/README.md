# tsp_neural

Sibling to `tsp_heuristic/` — same Santa 2018 TSP, same metric, same
5-min budget, but the agent's lever is **training a small neural
network to guide the local-search inner loops**, not hand-designing
classical heuristics.

This is **Option B2** ("neural-guided local search") from the project's
options menu. Not a pure neural solver: classical pipeline (NN seed →
2-opt → submission) stays intact, the network's role is to *score
candidate moves* better than the geographic k-NN heuristic does.

## Files

```
prepare.py        — frozen: same as tsp_heuristic/ (load_cities, score_tour)
solve.py          — the file the agent edits each cycle (loads a learned
                    scorer if available; falls back to geographic baseline)
program.md        — agent operating rules, neural-augmentation focus
ideas.md          — seeded ideas in M/T/R/I/E/C classes
AGENTS.md         — tooling inventory + decision table
justfile          — common shell recipes (run, train, harvest, …)
pyproject.toml    — deps: numpy, pandas, sympy, scipy, numba, torch

.claude/
  agents/         — recap-writer, paper-researcher
  commands/       — /recap
  skills/         — postmortem, profile-solver, compare-runs,
                    algo-blueprint, train-policy, permute-ideas,
                    evolve-tooling
  hooks/          — block-frozen-edits, block-dep-install, recap-tick
  settings.json   — wires the hooks

data/             — symlink to ../tsp_heuristic/data/ (shared)
moves/            — harvested move logs (gitignored)
checkpoints/      — saved model weights (gitignored)
submissions/      — solver output (gitignored)
results.tsv       — local experiment ledger (gitignored)
```

## Quick start

```bash
# 1. ../tsp_heuristic/data/cities.csv must exist (the symlink resolves there)
# 2. Sync deps (this downloads PyTorch — several GB, one-time)
uv sync && just data && just run     # smoke test
```

The starting baseline (no learning) lands ~1.55–1.6M `val_cost`. The
agent's job is to add learning on top — see `program.md` and the
`train-policy` skill for the harvest → train → integrate workflow.

## Common commands

```bash
just                  # list all recipes
just status           # head, last result, recap-pending
just run              # one experiment (5-min budget)
just metrics          # extract val_cost from run.log
just ledger           # pretty-print results.tsv
just exp "<desc>"     # commit experiment
just revert           # undo last commit (creates revert commit; safe
                      # for shared-main with the tsp_heuristic loop)
just harvest          # solve.py with move-logging enabled
just train            # training-only run (no solve)
just checkpoints      # list saved model weights
just moves            # list harvested move logs
just tools            # list .claude/ inventory
```

## How this differs from tsp_heuristic/

|                  | `tsp_heuristic/`              | `tsp_neural/`                 |
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

Inspired by the same lineage as `tsp_heuristic/` —
[karpathy/autoresearch](https://github.com/karpathy/autoresearch),
the [Kaggle Santa 2018](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/),
and the marimo walkthrough video.
