# autoresearch-tsp

Two autonomous LLM research loops attacking the same problem — the
[Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/overview)
TSP (197,769 cities, with a 1.1× penalty on every 10th step from a
non-prime origin). Same metric (`val_cost`), same 5-min wall-clock
budget per cycle, same keep-or-revert mechanic. Different *levers*
the agent can pull.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
and the [marimo walkthrough video](https://www.youtube.com/watch?v=bMoNOb0iXpA).

## The two projects

<<<<<<< Updated upstream
## Layout

```
tsp_research/         the active loop (harness + agent tooling)
autoresearch/         vendored upstream (karpathy's repo, reference only)
.beads/               beads issue tracker (project memory)
AGENTS.md, CLAUDE.md  agent guidance for the outer repo
```

The interesting work happens in `tsp_research/` — see
[`tsp_research/README.md`](tsp_research/README.md) for setup,
[`tsp_research/AGENTS.md`](tsp_research/AGENTS.md) for the agent tooling
inventory, and [`tsp_research/program.md`](tsp_research/program.md) for the
autonomous loop's operating rules.

## Quick start

```bash
# 1. Unzip the Kaggle archive into tsp_research/data/ so cities.csv exists
# 2. Sync deps and smoke-test
cd tsp_research
uv sync
just data         # smoke test: loads cities, scores identity tour
just run          # baseline solver (~5 min)
just metrics      # pull val_cost / solve_seconds from run.log
```

Then point a fresh Claude Code session at `tsp_research/` and prompt it
with: *"read AGENTS.md and program.md, then start the loop on branch
`tsp/<tag>`."* The agent will sample ideas from `ideas.md`, edit
`solve.py`, run experiments, log results, and iterate. Every 4 cycles a
hook flags a recap-pending sentinel; the agent runs `/recap` to update
the running `recap-N.md` series.

## What's in the toolset

`tsp_research/.claude/` ships:

- **Subagents**: `recap-writer` (maintains `recap-*.md`), `paper-researcher`
  (sources fresh ideas from literature into `ideas.md`).
- **Skills**: `postmortem` (bottleneck classification), `profile-solver`
  (cProfile hotspot analysis), `compare-runs` (diff two experiment commits +
  their deltas), `algo-blueprint` (paper → patch plan), `evolve-tooling`
  (the meta-skill for extending `.claude/` itself).
- **Slash command**: `/recap`.
- **Hooks**: `block-frozen-edits` (PreToolUse — guards `prepare.py` and
  `recap-*.md`), `block-dep-install` (PreToolUse on Bash — gates dep
  additions), `recap-tick` (PostToolUse — writes `.recap-pending` every 4
  ledger rows).
- **Justfile**: 17 recipes wrapping the loop's common shell operations
  (`run`, `metrics`, `ledger`, `exp`, `log`, `revert`, `status`, `tools`,
  `score`, `clean`, …).
=======
|                  | [`tsp_research/`](tsp_research/)        | [`tsp_neural/`](tsp_neural/)                  |
|------------------|------------------------------------------|------------------------------------------------|
| **Approach**     | classical heuristic search               | neural-guided local search                     |
| **Lever**        | algorithm design                         | model design + integration                     |
| **Trains a model?** | **no** — pure numpy/numba/scipy       | **yes** — small PyTorch model per cycle        |
| **What's optimised** | a permutation of 197,769 ints (the tour) | a tour, *plus* the move-scorer that helps build it |
| **Deps**         | numpy, pandas, sympy, scipy, numba       | + `torch`                                      |
| **Pipeline today** | NN seed → 2-opt → Or-opt → ILS → prime polish | NN seed → 2-opt (baseline; agent adds learning from cycle 1) |
| **Risk**         | low; classical literature is deep        | high; learned/classical glue is fiddly         |

Both share `prepare.py` (the metric is bit-identical) and the same
harness shape: agent edits one file (`solve.py`), runs under a
fixed 5-min budget, scores against `val_cost`, keeps or reverts,
appends to `results.tsv`, repeats.

Each subdir is self-contained. See its `README.md` for setup, its
`AGENTS.md` for the tooling inventory, and its `program.md` for the
loop's operating rules.

## Layout

```
tsp_research/      classical loop (live; producing real results)
tsp_neural/        neural-guided loop (scaffolded; first cycle TBD)
autoresearch/      vendored upstream (karpathy's repo, reference only)
.beads/            beads issue tracker (project memory; gitignored)
AGENTS.md         agent guidance for the outer repo
```

## Running both loops in parallel

A single working tree only has one `HEAD`, so simultaneous loops need
**git worktrees** — each loop gets a sibling working directory with
its own checked-out branch and independent file state, sharing the
underlying `.git/`.

```bash
# tsp_research — runs in this working tree
cd /home/phiat/lab/apr/auto-rez
git checkout -b tsp/<tag> main          # one-time
cd tsp_research/
uv sync && just data && just run        # smoke test
# point a Claude Code session here, follow program.md

# tsp_neural — runs in a sibling worktree on its own branch
git -C /home/phiat/lab/apr/auto-rez worktree add -b neural/<tag> ../auto-rez-neural main
cd /home/phiat/lab/apr/auto-rez-neural/tsp_neural
uv sync && just data && just run        # smoke test (downloads PyTorch first time)
# point a *separate* Claude Code session here, follow its program.md
```

The two sessions never collide on `HEAD`. Branches are mutually
visible (handy for `compare-runs` across paradigms once both have
data); `results.tsv` and other artefacts are per-worktree-local.
>>>>>>> Stashed changes

## Status

- **`tsp_research/`** — actively iterating on branch `tsp/apr25`.
  The pipeline has matured into NN → 2-opt + Or-opt(1,2,3) → ILS with
  adaptive double-bridge / segment-shift → prime-aware swap polish.
  Best `val_cost` so far is in the **~1.548M** range (~14.6% off the
  identity-tour baseline). Recap series in `tsp_research/recap-*.md`.
- **`tsp_neural/`** — scaffolded, no cycles run yet. Baseline
  (NN + 2-opt only, no learning) will land in the 1.55-1.6M range
  once first run; the agent's job from cycle 1 is to introduce
  learning per `tsp_neural/program.md`.

For reference, top public-leaderboard scores for Santa 2018 were in
the 1.514M range.

## Provenance

- **Inspiration & template**: [karpathy/autoresearch](https://github.com/karpathy/autoresearch).
- **Task**: [Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/).
- **Inspired by this video**: [marimo: autoresearch on the Santa 2018 TSP](https://www.youtube.com/watch?v=bMoNOb0iXpA).

## License

MIT.
