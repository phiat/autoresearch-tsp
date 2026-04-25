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

|                  | [`tsp_heuristic/`](tsp_heuristic/)        | [`tsp_neural/`](tsp_neural/)                  |
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

## Important — what's *not* being trained

**There is no neural network training in this project.** Unlike the
upstream autoresearch (which trains a small GPT every cycle and reports
`val_bpb`), `tsp_heuristic/solve.py` runs **classical heuristic search** —
nearest-neighbor construction, 2-opt with cKDTree candidate lists,
Or-opt, iterated local search with adaptive perturbation, prime-aware
swap polish. The "thing being optimised" is a **permutation of 197,769
integers** (the tour), not a tensor of weights. Zero learnable parameters.
No `torch`, no backprop, no `nn.Module`.

The interesting "research" here is the **agent designing the algorithm**,
not training a model. Each cycle the agent picks an idea (from
`ideas.md`), edits `solve.py`, runs it, measures the delta, and keeps or
reverts. Over many cycles a real solver pipeline emerges from the
sequence of small, verified changes. The model doing the *driving* is
Claude (Opus 4.7); nothing inside the loop has trainable weights.

(If you want a neural-TSP variant — a pointer network or attention model
that emits tours autoregressively — that's a different project; this one
is "agent vs. combinatorial optimisation," not "agent training a neural
solver.")

## Layout — two parallel loops, same metric

```
tsp_heuristic/         classical heuristic-search loop
                      (NN → 2-opt → Or-opt → ILS → prime polish)

tsp_neural/           neural-guided local search loop
                      (small PyTorch model trained per cycle to score
                       candidate moves; classical pipeline keeps the
                       glue together)

autoresearch/         vendored upstream (karpathy's repo, reference)
.beads/               beads issue tracker (project memory)
AGENTS.md             agent guidance for the outer repo
```

Both loops share `prepare.py` semantics (the metric is identical) and
the same harness shape. They differ in the *lever* the agent pulls:
algorithm design vs. model design + integration. Each subdir has its
own `README.md`, `AGENTS.md`, `program.md`, `ideas.md`, and `.claude/`
toolset.

## Running both loops in parallel

Each loop wants its own branch (`heuristic/<tag>` for classical,
`neural/<tag>` for neural-guided). A single working tree only has one
`HEAD` at a time, so to run them simultaneously, use **git
worktrees** — each loop gets a sibling working directory with its own
checked-out branch.

```bash
# tsp_heuristic — runs in this working tree on its experiment branch
cd /home/phiat/lab/apr/auto-rez
git checkout -b heuristic/<tag> main         # one-time
cd tsp_heuristic/
# ...point a Claude Code session here, follow program.md

# tsp_neural — runs in a sibling worktree on its own branch
git -C /home/phiat/lab/apr/auto-rez worktree add -b neural/<tag> ../auto-rez-neural main
cd /home/phiat/lab/apr/auto-rez-neural/tsp_neural
uv sync                                # one-time (downloads PyTorch)
# ...point a *separate* Claude Code session here
```

The two sessions never collide on `HEAD`. They share the underlying
`.git/` so branches are mutually visible (handy for `compare-runs`
across paradigms once both have data).

A single working tree only has one `HEAD`, so simultaneous loops need
**git worktrees** — each loop gets a sibling working directory with
its own checked-out branch and independent file state, sharing the
underlying `.git/`.

```bash
# 1. Unzip the Kaggle archive into tsp_heuristic/data/ so cities.csv exists
# 2. Sync deps and smoke-test the classical loop
cd tsp_heuristic
uv sync
just data         # smoke test: loads cities, scores identity tour
just run          # baseline solver (~5 min)
just metrics      # pull val_cost / solve_seconds from run.log
```

Then point a fresh Claude Code session at `tsp_heuristic/` and prompt it
with: *"read AGENTS.md and program.md, then start the loop on branch
`heuristic/<tag>`."* The agent will sample ideas from `ideas.md`, edit
`solve.py`, run experiments, log results, and iterate. Every 4 cycles a
hook flags a recap-pending sentinel; the agent runs `/recap` to update
the running `recap-N.md` series.

For the neural loop, do the worktree setup above and run
`tsp_neural/`'s equivalent: `uv sync` (one-time PyTorch download),
`just data`, `just run` for the baseline (NN + 2-opt only — intentionally
weak; the agent's first 3 cycles introduce learning).

## What's in the toolset

`tsp_heuristic/.claude/` ships:

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

## Status

The first session's run-by-run progress is captured in
`tsp_heuristic/recap-1.md` and `recap-2.md`. The loop is on a credible
trajectory toward the public-leaderboard scores; the algorithm has matured
into: fast cKDTree-walked NN seed → 2-opt + Or-opt(1,2,3) local search with
candidate lists → ILS with adaptive double-bridge / segment-shift
perturbation → prime-aware swap polish.

## Provenance

- **Inspiration & template**: [karpathy/autoresearch](https://github.com/karpathy/autoresearch).
- **Task**: [Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/).
- **Inspired by this video**: [marimo: autoresearch on the Santa 2018 TSP](https://www.youtube.com/watch?v=bMoNOb0iXpA).

## License

MIT.
