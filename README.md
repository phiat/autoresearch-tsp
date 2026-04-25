# autoresearch-tsp

An [autoresearch](https://github.com/karpathy/autoresearch)-style autonomous
research loop pointed at the [Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/overview)
TSP. An LLM agent edits a single solver file, runs it within a fixed 5-minute
budget, scores the result against the official metric, keeps or reverts based
on the delta, and repeats — indefinitely.

> *"Give an AI agent a small but real research setup and let it experiment
> autonomously overnight. It modifies the code, runs for 5 minutes, checks
> if the result improved, keeps or discards, and repeats."*
> — adapted from karpathy/autoresearch

The original autoresearch targets LLM pretraining (the metric is `val_bpb`).
This repo keeps the *philosophy* — fixed budget, single-file edits, single
scalar metric, append-only ledger — but swaps the substrate: combinatorial
optimisation over a 197,769-city Euclidean graph with a prime-step penalty,
metric is total tour cost (lower is better).

## Important — what's *not* being trained

**There is no neural network training in this project.** Unlike the
upstream autoresearch (which trains a small GPT every cycle and reports
`val_bpb`), `tsp_research/solve.py` runs **classical heuristic search** —
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
tsp_research/         classical heuristic-search loop
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

Each loop wants its own branch (`tsp/<tag>` for classical,
`neural/<tag>` for neural-guided). A single working tree only has one
`HEAD` at a time, so to run them simultaneously, use **git
worktrees** — each loop gets a sibling working directory with its own
checked-out branch.

```bash
# tsp_research — runs in this working tree on its experiment branch
cd /home/phiat/lab/apr/auto-rez
git checkout -b tsp/<tag> main         # one-time
cd tsp_research/
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

## Quick start

```bash
# 1. Unzip the Kaggle archive into tsp_research/data/ so cities.csv exists
# 2. Sync deps and smoke-test the classical loop
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

For the neural loop, do the worktree setup above and run
`tsp_neural/`'s equivalent: `uv sync` (one-time PyTorch download),
`just data`, `just run` for the baseline (NN + 2-opt only — intentionally
weak; the agent's first 3 cycles introduce learning).

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

## Status

The first session's run-by-run progress is captured in
`tsp_research/recap-1.md` and `recap-2.md`. The loop is on a credible
trajectory toward the public-leaderboard scores; the algorithm has matured
into: fast cKDTree-walked NN seed → 2-opt + Or-opt(1,2,3) local search with
candidate lists → ILS with adaptive double-bridge / segment-shift
perturbation → prime-aware swap polish.

## Provenance

- **Inspiration & template**: [karpathy/autoresearch](https://github.com/karpathy/autoresearch).
- **Task**: [Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/).

## License

MIT.
