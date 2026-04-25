---
name: train-policy
description: Wrap the harvest → train → integrate workflow for the neural move-scorer. Use in early cycles to introduce learning to the loop, and any time the integration boundary between learned scorer and classical 2-opt needs reshaping. Produces a small PyTorch model trained on logged moves and integrates it into solve.py's candidate-ranking step.
---

# train-policy

The end-to-end "make learning happen this cycle" skill for `tsp_neural/`.

## When to use

- **Early cycles (1-3)**: this is the first thing the loop should do.
  Don't pick `M2` from `ideas.md` and freestyle the integration —
  invoke this skill so the harvest, train, and integration steps
  stay coordinated.
- **After a model architecture change** (any new M-class idea): rerun
  to re-train and re-integrate.
- **After harvest format changes** (T-class ideas): rerun so the
  model's input features match what the solver actually computes.

## Inputs

- The current `solve.py`.
- The chosen `ideas.md` item (e.g. M1 + R1 + I1 combination, or just
  the next single-class change).
- Existing `moves/` data (if any) and `checkpoints/` (if any).

## Procedure

### 1. Harvest move data (if needed)

If `moves/` is empty, or the last harvest is stale (older than
`solve.py`'s last edit affecting move features), run:

```bash
just harvest        # MODE=harvest uv run solve.py > run.log
```

`solve.py` should write `moves/<commit>.npz` with arrays:
- `features` — (N_moves, F) float32 per-move feature vectors
- `gain` — (N_moves,) float32 measured gain (positive = improvement)
- `accepted` — (N_moves,) bool whether the move was applied

If the harvest path doesn't exist yet, **make adding it the first
sub-step** — `solve.py` needs an env-gated logging branch.

### 2. Train

Add or update `train.py`:

```python
# minimal example shape; agent fills in details per ideas.md choice
import numpy as np, torch, torch.nn as nn
data = np.load(f"moves/{latest_commit}.npz")
X = torch.from_numpy(data["features"])
y = torch.from_numpy(data["accepted"]).float()
model = nn.Sequential(nn.Linear(X.shape[1], 64), nn.ReLU(), nn.Linear(64, 1))
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
for epoch in range(EPOCHS):
    logits = model(X).squeeze(-1)
    loss = nn.functional.binary_cross_entropy_with_logits(logits, y)
    opt.zero_grad(); loss.backward(); opt.step()
torch.save(model.state_dict(), f"checkpoints/{latest_commit}.pt")
```

Print to `run.log`:

```
training_seconds: <float>
model_params:     <int>
val_auc:          <float>      # held-out improving-move AUC
```

The val_auc line is critical. **If val_auc <= 0.55** (i.e. the model
is barely better than the geographic heuristic), do not integrate;
log "discard" with reason "model didn't learn — auc=0.X" and revert.

### 3. Integrate

Modify `solve.py` so the 2-opt sweep:
- Loads the latest checkpoint at startup.
- For each city `a`, computes features for its candidates, runs a
  batched `model(...)` call once per sweep (E1 — batched inference),
  reorders/filters the candidate list per the chosen integration
  idea (I1/I2/I3/etc.).
- Records `inference_calls` count for the run.log summary.

Critical perf note: model inference is in the inner loop of the
inner loop. If naive per-candidate calls dominate, the solver will
miss budget. Batch by city or by sweep.

### 4. Run + measure

`just run` and `just metrics`. Compare val_cost to the prior best
(`just last` shows it). The headline:

```
val_cost:         <new>
solve_seconds:    <float>
training_seconds: <float>      (fits within solve_seconds budget)
inference_calls:  <int>
val_auc:          <float>
```

## Output for the parent session

```
train-policy summary:

Idea(s) implemented: <ids from ideas.md>
Harvest:   <fresh / reused>, <N moves> samples
Training:  <N epochs>, <T seconds>, val_auc=<X>
Model:     <P params>, saved to checkpoints/<commit>.pt
Integration: <I-class id>, <strategy>
Result:    val_cost <new> vs prior <old> (Δ=<delta>)
Recommend: <keep / discard / debug>
```

## What you must NOT do

- Do not edit `prepare.py`. Frozen.
- Do not skip the val_auc gate. If the model didn't learn, integrating
  it is just adding overhead. Discard early.
- Do not implement Or-opt, ILS, double-bridge, or prime-aware moves
  here. Those belong in `tsp_research/` or in a *later* combination
  cycle (C-class) once learning works.
- Do not bundle multiple M/T/R/I ideas into one experiment. Pick one
  axis at a time so you can attribute the val_cost delta.
- Do not let `training_seconds` exceed half the budget. If a run is
  300s and training takes 200s, only 100s is left for the actual
  solve — the model can be perfect and still produce a worse tour.
