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
