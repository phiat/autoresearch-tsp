# tsp_neural

Sibling to `tsp_research/`. Same Santa 2018 TSP, same metric, same
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
that `tsp_research/` already explored, **stop** — that's a different
project. The differentiator here is *learning*.

## Setup

This loop is designed to **run in parallel with `tsp_research/`** in
a separate **git worktree** so the two loops don't fight over `HEAD`.

1. **Agree on a run tag**: `neural/<tag>` (e.g. `neural/apr25-b2`).
   The branch must not already exist.
2. **Create a worktree** (run this from the *parent* repo root, one
   time, before starting the loop):

   ```bash
   git worktree add -b neural/<tag> ../auto-rez-neural main
   cd ../auto-rez-neural/tsp_neural
   ```

   This creates a sibling working tree at `../auto-rez-neural/`
   checked out to a brand-new `neural/<tag>` branch based on `main`.
   The original working tree (where `tsp_research/` runs on
   `tsp/<tag>`) is untouched. Both loops can now run simultaneously.
3. **Read the in-scope files**:
   - `README.md`, `AGENTS.md` — project context + tooling inventory.
   - `prepare.py` — frozen data loader + `score_tour` (same as
     `tsp_research/`). Do not modify.
   - `solve.py` — the file you modify. Baseline = NN + 2-opt with
     k-NN candidates. **No learning yet.**
4. **Verify env**: `uv sync` (downloads PyTorch — several GB; one-time).
5. **Smoke test**: `just data` and `just run`. Baseline val_cost should
   be in the ~1.55-1.6M range (worse than `tsp_research/`'s current
   best because no Or-opt / no ILS yet — that's intentional).
6. **Initialize `results.tsv`**: header row only.
7. **Confirm setup looks good**, then start the loop.

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
- Try to beat `tsp_research/` by re-implementing classical Or-opt /
  ILS without any learned component. That's the wrong project.

## The metric

Same as `tsp_research/`: `val_cost` from `prepare.score_tour(tour)`.
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

## The loop

Same shape as `tsp_research/program.md`:

1. `just status` — branch, head, last result, recap-pending.
2. Pick an idea from `ideas.md` (sampling protocol below).
3. Edit `solve.py` (and helpers).
4. `just exp "<desc>"` to commit.
5. `just run` to execute.
6. `just metrics`, `just log <args>`.
7. Keep or `just revert`.
8. Check `.recap-pending`; run `/recap` if present.

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

Use these prefixes when adding ideas. Same sample/grow protocol as
`tsp_research/` — sample uniformly from untried, append 2-3 fresh
ideas every 5 cycles, append-only.

## NEVER STOP

Same rule as `tsp_research/`. Once the loop starts, iterate until the
human interrupts. Out of ideas? Re-read `ideas.md`, invoke the
`postmortem` skill, invoke `paper-researcher` with a topic like
"learned 2-opt move ranker" or "graph neural network candidate edge
scorer for TSP." See `AGENTS.md` for the full tooling inventory.
