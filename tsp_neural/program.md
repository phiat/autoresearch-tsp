# tsp_neural

Sibling to `tsp_heuristic/`. Same Santa 2018 TSP, same metric, same
5-min budget, same keep-or-revert loop. **Different lever**: instead
of hand-designing better classical heuristics, the agent trains a
small neural network whose job is to *guide the local-search inner
loops*.

This is Option B2 from the original options menu: **neural-guided
local search**. Not a pure neural solver. The classical pipeline
(NN seed → 2-opt → maybe Or-opt → submission) stays intact; the
network's role is to score candidate moves better than the
geographic k-NN heuristic does.

If you find yourself implementing the same purely-classical ideas
that `tsp_heuristic/` already explored, **stop** — that's a different
project. The differentiator here is *learning*.

## Setup

You commit to `main` (no per-loop branches). The `tsp_heuristic` loop
also commits to `main`; the `revert` recipe uses `git revert` so the
two loops don't wipe each other's commits when discarding experiments.

1. **Confirm you're on `main`**: `git branch --show-current`. If not,
   `git checkout main`.
2. **Read the in-scope files**:
   - `README.md`, `AGENTS.md` — project context + tooling inventory.
   - `prepare.py` — frozen data loader + `score_tour` (same as
     `tsp_heuristic/`). Do not modify.
   - `solve.py` — the file you modify. Baseline = NN + 2-opt with
     k-NN candidates. **No learning yet.**
3. **Verify env**: `uv sync` (downloads PyTorch — several GB;
   one-time).
4. **Smoke test**: `just data` and `just run`. Baseline `val_cost`
   should be in the ~1.55-1.6M range (worse than `tsp_heuristic/`'s
   current best because no Or-opt / no ILS yet — that's intentional).
5. **Initialize `results.tsv`** if missing: header row only.
6. **Confirm setup looks good**, then start the loop.

## What the agent must do

The first ~3 cycles should be **adding learning to the loop**, not
tuning the classical baseline. Concretely, the early experiments
should look like:

- Cycle 1: harvest move data from one baseline run (log every 2-opt
  candidate considered, gain, accept/reject). Save to `moves/`.
- Cycle 2: train a tiny model (MLP or shallow GNN) on those harvested
  moves; validate on held-out moves; check it predicts "improving"
  better than chance.
- Cycle 3: integrate the trained model into the 2-opt sweep — replace
  the "iterate candidates in geographic order" with "iterate
  candidates in model-predicted-improvement order." Measure delta.

After that, the agent samples from `ideas.md` per the standard loop.

## What you CAN do

- Modify `solve.py` (the only file you edit per cycle).
- Add helper modules under `tsp_neural/` if architecture demands —
  `model.py`, `harvest.py`, `train.py` are reasonable. `solve.py`
  remains the entry point.
- Train models inside the 5-min budget. The 4070 has 16GB VRAM —
  enough for small (~100K-1M param) models trained from scratch
  per cycle, OR loaded from `checkpoints/` if a prior cycle saved
  one.
- Cache harvested move data in `moves/` (gitignored) — accumulating
  data across cycles is encouraged.

## What you CANNOT do

- Modify `prepare.py`. Frozen by hook.
- Add deps beyond the allow-list: `numpy`, `pandas`, `sympy`, `scipy`,
  `numba`, `torch`. Hook enforces. PyTorch ecosystem (`torchvision`,
  `torch_geometric`, etc.) is **not** pre-approved — ask first.
- Train for hours. The 5-min budget is wall-clock total per cycle;
  if the model takes 4 min to train, you have 1 min to apply it and
  measure. Plan accordingly.
- Try to beat `tsp_heuristic/` by re-implementing classical Or-opt /
  ILS without any learned component. That's the wrong project.

## The metric

Same as `tsp_heuristic/`: `val_cost` from `prepare.score_tour(tour)`.
**The official Santa 2018 cost.** Lower is better. The 1.1× prime
penalty applies. The model is a *means*; the tour is the artefact;
val_cost is the truth.

## Output format

```
---
val_cost:         1554321.5678
solve_seconds:    298.4
total_seconds:    312.8
n_cities:         197769
submission:       submissions/submission.csv
```

Optional extra lines for the neural variant — recommended:
```
model_params:     127394
training_seconds: 184.2
moves_logged:     412573
inference_calls:  1842110
```

## Logging results

Append to `results.tsv` (TAB-separated):

```
commit	val_cost	solve_seconds	status	description
```

Status: `keep` / `discard` / `crash`. Description should make the
*learning aspect* explicit (e.g. "M3: train 2-layer MLP on harvested
move features, integrate as candidate ranker").

## Parallel ILS — known limit: within-batch staleness

The PILS scaffold (commit `dd64693`) dispatches K workers per batch
sharing a single `best_tour` snapshot for the full `ILS_WORKER_BUDGET`
seconds. Within a batch, worker improvements do NOT propagate — all K
workers see the same stale seed for the entire 25 s.

**Empirical finding from neural cycles 39-45**: K=8 with budget=25s
is the current sweet spot. K=14 over-contended (recap-3 row 40);
K=15s budget too short (row 41); K=40s budget too long (row 42).

**When tuning `ILS_WORKERS`**: think "how often does the shared best
need to update?", not "how many cores can I fill?". Small K + frequent
batch turnover beats large K + long batches.

If you want true within-batch broadcast (workers reseed mid-batch
when global best improves), it requires a `Manager.Value` shared
state + poll points in `_vnd_local` between sweeps. Not currently
implemented; budget the work explicitly if proposing it.

## RNG noise floor and multi-seed evaluation

The solver is rng-seed-dependent. The neural loop's empirical noise
floor is **~250-500 cost units** (smaller than heuristic's because
PILS averages across batch members, but still real). A discard with
|delta| < 500 is *not necessarily a regression*.

**Rule**: before declaring a discard for any |delta| < 750, invoke
`multi-seed-eval` on the candidate. It re-runs solve.py with 2-3
different `ILS_SEED` values and reports the median val_cost. If the
median beats the prior best, *keep*; if not, *then* discard.

## Stuck protocol — break long discard streaks

The keep/revert mechanic is honest per-experiment but does not escape
exhausted veins. The recaps document multiple streaks (recap-2 had
4-for-4 discards on PILS knob-sweeps) where the agent kept tuning
the same axis instead of trying a structurally-new idea.

**Hard rules** (on top of the standard sampling protocol):

- **After 5 consecutive discards**: STOP. Invoke the `postmortem`
  skill. Read its bottleneck classification.
- **If `postmortem` flags "saturated move-set"** or "saturated
  hyperparam"**: next experiment MUST come from the
  *untried-research-injected* pool — invoke `untried-ideas`. No
  more adjacent micro-tweaks in the saturated vein.
- **After 10 consecutive discards**: invoke `paper-researcher` with
  an explicit era directive (`hybrid` or `modern-learned`) to inject
  fresh ideas, then sample one of those next.
- **After 15 consecutive discards in the same vein**: declare the
  vein closed in `ideas.md` (annotate items as
  `[exhausted: rows X-Y]`).

The recap-writer subagent's "Tooling observations" section flags
whether these triggers fired when they should have.

## The loop

Same shape as `tsp_heuristic/program.md`:

1. `just status` — head commit, last result row, recap-pending. You should always be on `main`.
2. Pick an idea from `ideas.md` (sampling protocol below).
3. Edit `solve.py` (and helpers).
4. `just exp "<desc>"` to commit.
5. `just run` to execute.
6. `just metrics`, `just log <args>`.
7. Keep, or `just revert` to undo. Note: `just revert` creates a
   *revert commit* on top (does not rewrite history) so it's safe even
   when the `tsp_heuristic` loop is committing to the same branch
   concurrently.
8. **Hard prerequisite — recap check.** Before picking the next
   idea, **stat `.recap-pending`**. If it exists, **stop the cycle
   here**, run `/recap` (the `recap-writer` subagent writes
   `recaps/recap-<N>.md`, commits + pushes it, and deletes the
   sentinel), and only resume after it completes. Not optional —
   the recap is the loop's audit trail.

## Idea library (`ideas.md`)

Idea classes specific to this project:

- **M** (model): architecture choices — MLP, attention, GNN, scoring head.
- **T** (training data): what to log, how much, normalisation, splits.
- **R** (reward / loss): supervised on accept/reject, regression on
  gain, contrastive, RL.
- **I** (integration): how the model plugs into the 2-opt / Or-opt
  inner loop — top-k re-rank, threshold filter, sampling, etc.
- **E** (engineering): inference speed (the model is called millions
  of times per solve — latency matters).
- **C** (combination): pipelines that combine learned and classical.

Use these prefixes when adding ideas. Sample uniformly from untried.

**Every 5 logged experiments**, the growth tick alternates between:

- **Self-generated ticks** (cycles 10, 20, 30, …): append under
  `## Appended (cycle N)` based on what the log has shown.
- **Research ticks** (cycles 5, 15, 25, …): MANDATORY invocation of
  the `paper-researcher` subagent with an era directive, rotating:
  - cycle 5  → era=`hybrid`         (NeuroLKH, neural-LNS, learned edges)
  - cycle 15 → era=`modern-learned` (Kool, POMO, DACT, GLOP, DIFUSCO)
  - cycle 25 → era=`hybrid`         (drill deeper)
  - cycle 35 → era=`modern-learned`
  - cycle 45 → era=`classical`      (move-space inspiration)
  - …rotate (`hybrid`/`modern-learned`/`classical`).
  The subagent appends under `## Appended (research: <era> — <topic>)`
  with `[src: <ref>]` citations on each idea.

Append-only; never delete or rewrite older entries.

**Permuting kept ideas:** any time the log shows ≥3 kept ideas across
different classes, invoke the `permute-ideas` skill to propose
cross-class combinations (e.g. "I5 ranker + LNS destroy targets",
"don't-look bits + ILS double-bridge"). Combinations are tagged `C`
(combination/pipeline) when appended.

## NEVER STOP

Same rule as `tsp_heuristic/`. Once the loop starts, iterate until the
human interrupts. Out of ideas? Re-read `ideas.md`, invoke the
`postmortem` skill, invoke `paper-researcher` with a topic like
"learned 2-opt move ranker" or "graph neural network candidate edge
scorer for TSP." See `AGENTS.md` for the full tooling inventory.
