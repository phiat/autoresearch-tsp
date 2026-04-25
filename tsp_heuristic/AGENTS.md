# Agent guide — `tsp_heuristic/`

This file is the index of tooling available to the autonomous loop.
For the experiment loop's operational rules, see `program.md`.

## Quick orientation

```bash
just                  # list all recipes
just tools            # list all subagents / skills / commands / hooks
just status           # branch, last run, results count, recap-pending flag
just run              # run one experiment (5-min budget)
just metrics          # pull val_cost / solve_seconds from last run.log
```

## Operating discipline

- **Frozen substrate** (do not modify): `prepare.py`, the `score_tour`
  metric, `TIME_BUDGET=300`, the dep allow-list (numpy, pandas,
  sympy, scipy, numba), the keep/revert mechanic, the `results.tsv`
  schema. The `block-frozen-edits.sh` and `block-dep-install.sh`
  hooks enforce the first two structurally — hitting them means
  pause and rethink, never argue with the hook.
- **Single-file edits**: each experiment changes only `solve.py`.
  Bundled changes are an anti-pattern and obscure which idea moved
  the score.
- **Append-only history**: `ideas.md` and `recaps/recap-*.md` are
  append-only. Older entries are evidence; never rewrite them.
- **Commit prefixes**: `exp:` for experiment commits, `meta:` for
  tooling / harness commits (managed by the `evolve-tooling` skill).

## Tooling inventory

### Slash commands

- `/recap` — refresh the recap series. Delegates to the `recap-writer`
  subagent. Use whenever `.recap-pending` exists (the
  `recap-tick.sh` hook writes it every 4 logged cycles), or when the
  user explicitly asks.

### Subagents (isolated context — invoke via the Agent tool)

- **`recap-writer`** — updates or creates the next `recaps/recap-<N>.md`. Reads
  `results.tsv`, git log, `ideas.md`, the latest recap. Decides
  in-place update vs new file. Only touches recap files.
- **`paper-researcher`** — expands the idea pool by searching papers,
  Kaggle Santa 2018 writeups, and adjacent algorithm literature.
  Output is **only** an append to `ideas.md`. Use when the pool is
  stale (`postmortem` flagging stagnation, or a class with no recent
  keep).

### Skills (model-invoked procedures — invoke via the Skill tool)

- **`postmortem`** — read-only analysis: detects plateaus, classifies
  the bottleneck (algorithmic / engineering / diversification /
  metric-mismatch), recommends the next idea. Use every ~5-10
  cycles or when stuck.
- **`profile-solver`** — cProfile-driven hotspot analysis of
  `solve.py`. Use when an experiment ran inside budget but barely
  moved val_cost.
- **`compare-runs`** — diff `solve.py` between two commits, paired
  with their measured deltas. Use when an experiment regressed
  unexpectedly or before combining two prior keeps.
- **`algo-blueprint`** — given an algorithm name, produce a focused
  implementation plan in this codebase's idiom. Use after picking
  an idea but before writing code, especially for algos with
  multiple variants in the literature.
- **`permute-ideas`** — read kept ideas from `results.tsv`, propose
  cross-class combinations as `X` (pipeline) experiments. Use any
  time the log shows ≥3 kept ideas across different classes (per the
  permute trigger in `program.md`), when stuck on a plateau, or
  after a `paper-researcher` run added building blocks.
- **`chart-progress`** — regenerate `<repo-root>/progress.png`
  (best `val_cost` over cycle index for both loops, with SOTA
  reference line). Use after every recap-tick, after a notable new
  best, or whenever the README chart looks stale.
- **`evolve-tooling`** — modify `.claude/` itself (skills, subagents,
  hooks, slash commands) based on observed friction. Append-only on
  evidence. Use when a recurring chore could be automated, when an
  existing skill produces the wrong shape, or when a hook misfires.

### Hooks (deterministic, harness-fired)

- **`block-frozen-edits.sh`** (PreToolUse on Edit/Write/MultiEdit) —
  hard-block edits to `prepare.py` and `recaps/recap-*.md`. The latter
  belong to `recap-writer`; route through `/recap` instead.
- **`block-dep-install.sh`** (PreToolUse on Bash) — hard-block
  `uv add` / `pip install` / `poetry add` / `conda install` /
  `mamba install`. New deps require human approval.
- **`recap-tick.sh`** (PostToolUse on Edit/Write/Bash) — every 4 rows
  in `results.tsv`, write `.recap-pending` (idempotent per cycle
  count). Loop should poll this between cycles.

## When to invoke what

- **Every cycle** (in this order): pick idea → edit `solve.py` →
  `just exp "<desc>"` → `just run` → `just metrics` → `just log <args>` →
  keep or `just revert`. Then check `.recap-pending` — if present,
  run `/recap` and the file is auto-cleared by `recap-writer`.
- **Every ~5 cycles**: invoke `postmortem` skill before sampling the
  next idea. Append 2-3 fresh ideas to `ideas.md` per the growth
  protocol in `program.md`.
- **When stuck** (3+ near-zero deltas in a row): invoke `postmortem`,
  then `paper-researcher` with the bottleneck topic.
- **When a regression is mysterious**: invoke `compare-runs`.
- **When wall-clock dominates over algorithm**: invoke
  `profile-solver`.
- **Before implementing a literature-heavy algo**: invoke
  `algo-blueprint`.
- **When the loop's *process* (not the code) is friction**: invoke
  `evolve-tooling` and commit with `meta:` prefix.

## Not your job

- Pushing to remote (no remote configured for this branch).
- Choosing the run tag — that's a human handshake at session start.
- Maintaining `recaps/recap-*.md` by hand — `recap-writer` owns those.
- Filing beads issues for in-loop experiments — the `results.tsv`
  ledger and git history are sufficient.
