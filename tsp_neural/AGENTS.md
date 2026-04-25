# Agent guide — `tsp_neural/`

Tooling index for the neural-guided local search loop. For operating
rules, see `program.md`. For the neural-vs-classical contrast, see
`README.md`.

## You share `main` with the `tsp_heuristic` loop

Both loops commit to `main` from the same working tree (the natural
file-level isolation comes from the separate `tsp_heuristic/` and
`tsp_neural/` subdirs — neither loop touches the other's `solve.py`).

Implications:

- You're on `main`. Don't switch off it. No per-loop branches.
- The other loop's commits will appear interleaved with yours in
  `git log`. That's fine — they touch different paths.
- `just revert` uses `git revert HEAD --no-edit` (creates a revert
  commit on top, doesn't rewrite history). This is what makes the
  shared-branch setup safe — your discards won't wipe the other
  loop's commits.
- If you see `HEAD` on a branch other than `main`, stop and
  investigate. Something external changed state; not safe to
  continue blindly.

## Quick orientation

```bash
just                  # list all recipes
just tools            # list subagents / skills / commands / hooks
just status           # branch, last run, results count, recap-pending
just run              # run one experiment (5-min budget)
just train            # training-only run (no solve)
just harvest          # solve.py with move-logging enabled
just metrics          # pull val_cost / training_seconds from run.log
```

## Operating discipline

- **Frozen substrate**: `prepare.py`, `score_tour`, `TIME_BUDGET=300`,
  the dep allow-list (`numpy`, `pandas`, `sympy`, `scipy`, `numba`,
  `torch`). Hooks enforce.
- **Single primary file edited**: `solve.py`. Helpers (e.g. `model.py`,
  `harvest.py`, `train.py`) are allowed but `solve.py` stays the
  entry point.
- **Append-only history**: `ideas.md`, `recap-*.md`. Never rewrite.
- **Commit prefixes**: `exp:` for experiment commits, `meta:` for
  tooling/harness changes (managed by the `evolve-tooling` skill).
- **Differentiator discipline**: every `keep` should advance the
  *learning component* in some way. Pure-classical-improvement
  experiments belong in `tsp_heuristic/`, not here.

## Tooling inventory

### Slash commands

- `/recap` — refresh the recap series via the `recap-writer` subagent.

### Subagents (isolated context — invoke via Agent tool)

- **`recap-writer`** — manages `recap-*.md`. Same shape as
  `tsp_heuristic/`'s but reads from this project's `results.tsv` and
  git log.
- **`paper-researcher`** — sources literature ideas into `ideas.md`.
  For this project, useful queries: "learned 2-opt move ranker",
  "GNN candidate edges TSP", "neural large-neighbourhood search",
  "Kool POMO attention TSP".

### Skills (model-invoked via Skill tool)

Inherited from `tsp_heuristic/` (same shape, different context):

- **`postmortem`** — read-only analysis of recent runs; classifies
  bottleneck.
- **`profile-solver`** — hotspot analysis. Especially useful here
  because model inference is called millions of times per solve;
  unexpected Python overhead in the inner loop kills budgets fast.
- **`compare-runs`** — diff two commits + their measured deltas.
- **`algo-blueprint`** — paper → patch plan. Useful before
  implementing a new model architecture.
- **`permute-ideas`** — read kept ideas from `results.tsv`, propose
  cross-class combinations as `C` (combination/pipeline) experiments.
  Highest-EV here is M × I × E crosses (model × integration ×
  engineering). Use after every 3+ kept ideas across different
  classes, when stuck, or after `paper-researcher` adds building
  blocks.
- **`chart-progress`** — regenerate `<repo-root>/progress.png`
  (best `val_cost` over cycle index for both loops, with SOTA
  reference line). Use after every recap-tick, after a notable new
  best, or whenever the README chart looks stale.
- **`evolve-tooling`** — modify `.claude/` itself.

Project-specific:

- **`train-policy`** — wraps the harvest → train → integrate workflow:
  collects move data from a recent solve.py run (or accumulated logs),
  trains a small model, evaluates against held-out moves, and
  integrates into `solve.py`. The agent's go-to skill for the
  early cycles.

### Hooks

- **`block-frozen-edits.sh`** — guards `prepare.py` and `recap-*.md`.
- **`block-dep-install.sh`** — gates new dep installation.
- **`recap-tick.sh`** — writes `.recap-pending` every 4 logged cycles.

## When to invoke what

- **Cycle 1-3** (priority): introduce learning. `train-policy` skill.
  Don't skip ahead to ILS / Or-opt; that's the wrong project.
- **Stuck on plateau**: invoke `postmortem`, then `paper-researcher`
  with a specific neural-TSP query.
- **Inference too slow**: `profile-solver`. Common fix: ship the model
  inputs in numpy batches, call `torch.compile`, or distill into a
  numba-friendly form (lookup table, decision tree).
- **Comparing classical vs learned ranking**: `compare-runs` between
  the latest learned commit and the baseline.
- **Process friction**: `evolve-tooling`, commit with `meta:` prefix.

## Idea library classes

| Prefix | Class                | Examples                                        |
|--------|----------------------|-------------------------------------------------|
| M      | model architecture   | M1 2-layer MLP, M2 small attention head, M3 GNN |
| T      | training data        | T1 supervised on accept/reject, T2 regress on gain |
| R      | reward / loss        | R1 BCE, R2 weighted by gain magnitude, R3 RL    |
| I      | integration          | I1 top-k re-rank, I2 threshold filter, I3 sample|
| E      | engineering          | E1 batched inference, E2 torch.compile, E3 distill |
| C      | combination          | C1 learned ranker + classical fallback, C2 hierarchy|

Sample uniformly from untried items, append 2-3 fresh per 5 cycles.

## Not your job

- Pushing to remote.
- Choosing the run tag (human handshake).
- Reproducing classical Or-opt / ILS / prime-aware moves — those live
  in `tsp_heuristic/`. Cross-pollinate ideas, but the val_cost lift
  here must come from learning.
