# tsp_heuristic

Autoresearch-style harness for the [Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/overview) challenge.

Same philosophy as [karpathy/autoresearch](https://github.com/karpathy/autoresearch):
fixed time budget, the agent edits a single file, one scalar metric,
autonomous loop. Different domain — combinatorial optimisation instead of
LLM training. Wraps the loop in a small `.claude/` toolset so the agent has
mechanical helpers (subagents, skills, slash commands, hooks) and a
`justfile` for ergonomic shell access.

## Files

```
prepare.py        — frozen: data loader, prime sieve, score_tour() metric
solve.py          — the file the agent edits each cycle
program.md        — agent operating rules
AGENTS.md         — tooling inventory + decision table
ideas.md          — seeded idea library + sample/grow protocol
recaps/recap-N.md        — running summaries (managed by recap-writer subagent)
justfile          — common shell recipes (run, metrics, ledger, exp, …)
pyproject.toml    — deps: numpy, pandas, sympy, scipy, numba

.claude/
  agents/         — recap-writer, paper-researcher
  commands/       — /recap
  skills/         — postmortem, profile-solver, compare-runs,
                    algo-blueprint, permute-ideas, evolve-tooling
  hooks/          — block-frozen-edits, block-dep-install, recap-tick
  settings.json   — wires the hooks

data/             — Kaggle CSVs (gitignored)
submissions/      — solver output (gitignored)
results.tsv       — local experiment ledger (gitignored)
run.log           — last solve.py output (gitignored)
```

## Quick start

```bash
# 1. Unzip the Kaggle archive into ./data/ so cities.csv exists
# 2. Set up the venv
uv sync

# 3. Smoke test the harness (loads data, scores identity tour)
just data

# 4. Run the baseline solver (~5 min wall clock)
just run
just metrics
```

## Common commands

```bash
just                  # list all recipes
just status           # branch, head commit, last result, recap-pending
just run              # run one experiment (5-min budget)
just metrics          # extract val_cost / solve_seconds from run.log
just ledger           # pretty-print results.tsv
just exp "<desc>"     # commit a new experiment with exp: prefix
just log <args>       # append a row to results.tsv
just revert           # discard the last commit
just diff [A] [B]     # diff solve.py between two commits
just tools            # list the project's subagents/skills/commands/hooks
just clean            # remove run.log, profile.log, .recap-pending
```

## Metric

`score_tour(tour)` returns the official Santa cost: euclidean tour length
with a 1.1× multiplier on every 10th step whose **origin** city is not
prime. Validation is strict — the tour must be a permutation of all
CityIds, starting and ending at City 0.

`prepare.py` is the frozen substrate (data loader, score, time budget,
prime mask). The `block-frozen-edits.sh` hook prevents accidental
modification.

## How the autonomous loop works

1. Pick an idea from `ideas.md` (sampling protocol in `program.md`).
2. Edit `solve.py` minimally to implement it.
3. `just exp "<desc>"` to commit, `just run` to execute.
4. `just metrics` to extract `val_cost`, `just log` to append to ledger.
5. Keep if improved; `just revert` if not. (`just revert` uses
   `git revert HEAD --no-edit` — safe when sharing `main` with the
   `tsp_neural` loop.)
6. Every 4 logged cycles, the `recap-tick` hook flags `.recap-pending`;
   the agent runs `/recap` to invoke the `recap-writer` subagent.
7. Every 5 cycles, the agent grows `ideas.md`. Self-generated ticks
   alternate with mandatory `paper-researcher` invocations on a
   rotating era schedule (classical → hybrid → domain-specific).
8. Loop forever.

See `AGENTS.md` for the full tooling inventory and "when to invoke what"
table.

## Provenance

The harness here is a sibling to (not a fork of) karpathy's autoresearch.
The vendored upstream lives at `../autoresearch/` for reference.
