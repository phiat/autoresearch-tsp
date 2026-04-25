# Idea Library — tsp_neural

Pool of experiment ideas for the **neural-guided** loop. Same sample
& grow protocol as `tsp_research/ideas.md`.

## Sampling protocol

1. Read this file.
2. Build the list of items not yet appearing in `results.tsv`'s
   `description` column. If empty, allow re-tries of low-scoring
   prior ideas with a tweak.
3. **First 3 cycles must be M/T/R or I-class** — introduce learning
   before anything else.
4. After cycle 3, sample uniformly from untried; bias toward
   underrepresented classes.
5. Implement as one focused `solve.py` (+ helpers) change. Don't
   bundle.

## Growth protocol

After every 5 logged experiments, append 2-3 new ideas to the bottom
under `## Appended (cycle N)`. Append-only.

---

## Seed ideas (cycle 0)

### M — Model architecture
- M1. **2-layer MLP scorer**: input = features of a candidate 2-opt
      move (4 edges' lengths + endpoint coords + tour-position deltas),
      hidden=64, output=scalar (predicted gain). Sigmoid head if
      classifying improving / not, linear if regressing gain.
- M2. **Edge embedding + dot-product**: learn a 32-dim embedding per
      city; score a candidate edge as ⟨emb[a], emb[b]⟩ + bias.
- M3. **Tiny attention over local context**: 1-2 transformer encoder
      layers over the 5-10 nodes near a candidate move; pooled output
      → score.
- M4. **Shallow GNN (1-2 message passes)** on the candidate-edge
      neighbourhood; node features = (x, y, prime?), edge features =
      length.
- M5. **Lookup table baseline**: discretise the move feature space
      into ~10K bins, learn a per-bin acceptance probability from
      harvested data. No NN; tests whether learning helps at all
      before investing in architectures.

### T — Training data
- T1. **Harvest from one baseline run**: log every candidate 2-opt
      move with (features, gain, accepted). Use as supervised set.
- T2. **Cumulative across runs**: keep `moves/` data growing each
      cycle; train on the union. Trade-off: dataset quality drifts
      as solver improves.
- T3. **Negative sampling**: for each accepted move, sample k random
      non-accepted moves at the same step as negatives.
- T4. **Per-position normalisation**: features scaled by local edge
      lengths so learned signal is geometry-relative, not absolute.
- T5. **Held-out validation split**: last 10% of harvested moves
      reserved for evaluating "does the model rank improving moves
      higher than the geographic heuristic does?"

### R — Reward / loss
- R1. **BCE on accept/reject** binary label.
- R2. **Regress on signed gain** (MSE), heavier weighting on |gain|.
- R3. **Pairwise ranking loss** (margin) between accepted and
      non-accepted moves at the same step.
- R4. **Reinforcement signal**: post-solve val_cost delta vs
      baseline used as global reward; per-move credit assignment via
      eligibility traces. (Riskier — high variance.)

### I — Integration
- I1. **Top-k re-rank**: keep candidate set the same (k=10 NN),
      reorder by model score before iterating.
- I2. **Threshold filter**: skip candidates with model score below
      threshold τ; tune τ to balance speed vs missed-improvement.
- I3. **Expand candidate pool**: use model to pick top-k from a
      larger pool (k=30 NN), test whether expanded reach beats k=10.
- I4. **Sampling**: temperature-softmax over candidate scores; trades
      determinism for diversity (good for ILS later).
- I5. **Hybrid fallback**: try model's top choices first; if no
      improvement found in N candidates, fall back to full geographic
      sweep.

### E — Engineering / inference speed
- E1. **Batched inference**: collect all candidate features for one
      sweep, single `model(...)` call rather than per-candidate.
- E2. **`torch.compile` the model**: amortise dispatch overhead.
- E3. **Distill MLP into numba-friendly form**: extract weights, do
      inference with `@njit` matmul. Drops Python overhead entirely.
- E4. **Half-precision inference**: fp16 / bf16 for the hot path on
      4070's tensor cores.
- E5. **Cache scores per (a, c) pair**: only re-score when the move
      neighbourhood changes.

### C — Combination / pipeline
- C1. **Learned ranker + Or-opt classical**: use model only for 2-opt;
      Or-opt stays geographic-NN.
- C2. **Two-stage**: model proposes top-3 candidates per node, then a
      classical 2-opt sweep restricts itself to those 3.
- C3. **Curriculum**: train cycle k's model on data from cycle k-1's
      run; each cycle bootstraps the next.
- C4. **Mix learned + geographic candidates**: 5 from each, dedup,
      iterate union.
