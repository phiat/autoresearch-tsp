# Idea Library — tsp_neural

Pool of experiment ideas for the **neural-guided** loop. Same sample
& grow protocol as `tsp_heuristic/ideas.md`.

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

---

## Appended (research: modern-learned — cycle 15 tick)

Sources surveyed: NeuroLKH (NeurIPS 2021, arXiv:2110.07983), DIFUSCO (NeurIPS 2023, arXiv:2302.08224), GLOP (AAAI 2024, arXiv:2312.08224), EAS (ICLR 2022, arXiv:2106.05126), T2T (NeurIPS 2023, Thinklab-SJTU/T2TCO), GNN-GLS (arXiv:2110.05291).

- M6. Train a tiny sparse-GNN (2-layer, 20-dim node embedding, k=10 neighbour edges) to output per-edge inclusion scores matching NeuroLKH's SGN, then distill weights into a numba-compatible forward pass so the resulting edge-priority array replaces the current geographic NN candidate set — [src: NeuroLKH, arXiv:2110.07983]

- T6. Harvest edge-level binary labels (edge in current best tour = 1, else 0) each cycle and train the M6 sparse-GNN with BCE loss on those labels, accumulating across cycles so the model self-improves as the tour quality rises — [src: NeuroLKH supervised edge training, arXiv:2110.07983]

- I6. Use the trained edge-score array as a learned candidate-edge filter: at 2-opt sweep time, only evaluate (i, j) pairs where the M6 score exceeds a threshold tau (tune tau so ~15 candidates/node survive), replacing the current NN lookup — cuts quadratic sweep cost while concentrating moves where the model says an edge is tour-worthy — [src: GNN-GLS heat-map guided local search, arXiv:2110.05291]

- R5. Add a prime-position auxiliary loss during M6 training: up-weight BCE loss by factor 1.1 on every 10th-position edge that originates from a non-prime city (mirroring the competition penalty), so the learned candidate set is prime-cost-aware rather than geometry-only — [src: competition-specific adaptation of NeuroLKH penalty node features, Santa 2018 prime constraint]

- E6. Implement a one-shot inference pass: after Or-opt converges each cycle, run a single batched forward pass of the numba-distilled M6 model over all N*k candidate pairs (N=197769, k=10) to pre-rank edges, then store the ranked index array; 2-opt in the next ILS restart reads from this cached array instead of recomputing NN distances — amortises model cost over all subsequent restarts within the 5-min budget — [src: EAS inference-time adaptation idea adapted to cache-based deployment, arXiv:2106.05126]

## Appended (cycle 20 self-generated tick)

Lessons from rows 1-19: pool-K>10 always regresses; one-accept-per-ai beats multi-accept; classical Or-opt + learned 2-opt is the +17k breakthrough; AUC≈1.0 ceiling means single-cycle retrains do not move val_cost; ILS gains are sub-1k per attempt. Open frontier = move-type breadth and data refresh, not architecture tweaks.

- C6. **VND-data harvest + retrain**: log 2-opt candidates *during* the C1 pipeline (not baseline NN-2opt); train.py loads union and produces a model trained on tours the deployed solver actually sees — [self: post-cycle-15 plateau, model never saw post-Or-opt move distributions]
- I7. **Sound don't-look bits**: on swap, clear dont_look for *all cities in the reversed segment* (linear cost, but segments are short at steady state); fixes cycle-12/13 regressions where cycle 9 quality was lost — [self: lessons from cycles 12-13]
- C7. **Or-opt-2 / Or-opt-3 chains under MLP guidance**: 2-opt-trained MLP pre-scores chain insertions; iterate top by score; combines new move types with learning instead of layering classical-only — [self: Or-opt-1 was +17k; chain length 2-3 typically +0.1–0.5% on TSPLIB]
