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

## Appended (permute: cross-class combinations of cycle-1..28 keeps)

Catalogue: 9 keeps across M (1) / T (5) / R (2) / I (2) / Z (1) / C (1). Engineering class is empty — every E-class try has been rolled into another cycle. Best pipeline today: I5 + C1 (Or-opt-1) + ILS-2x + Z1 boundary prime-aware + R6 prime-aware retrain. 5 combinations below avoid duplicates with C1-C7 and with previously discarded shapes.

- C8. **M5 lookup-table distill + I5 + Z1**: M5 discretises the (4 edge-len, 4 prime, log_pos_delta) feature space into ~16-bin lookup, replaces inline-MLP scoring with O(1) table read; I5 first-improving + cycle-22 prime-aware accept stays. ~5x faster scoring → ILS room reopens (cycle 26 lost its restarts) — covers the "AUC≈1 model is overkill for the work it does" observation.
- C9. **M2 city-embedding + I5 + Z1**: per-city 32-dim embedding, score(a,c) = ⟨emb[a], emb[c]⟩ + bias; ~30 mults vs MLP's 1409 → ~50x faster. Loses edge-length info but signals "do these two cities co-occur in good tours?" which the MLP can't easily encode. If quality holds, even cycle-26's sweep budget could fit 10 ILS restarts on top.
- C10. **R5 prime-aware aux loss + retrain on existing T7 data**: weighted-BCE training with 1.1x weight on candidates whose ai+1 or cj+1 is a 10th-step. Same architecture, sharper learning signal at exactly the boundary cases Z1 already optimises. Single-cycle train + run; if AUC at 10th-step subsamples improves, the model picks better candidates there.
- C11. **I2 threshold τ + I5 + Z1**: skip ranked candidates with model logit < 0 entirely (model said "won't accept"). Saves the prime-aware boundary check on ~80% of K=10 candidates. Combined with cycle 26's prime-aware retrain (whose model now correctly predicts prime-aware accept), τ=0 is the natural cutoff. ILS room may reopen without losing accept rate.
- C12. **I6 learned candidate filter + cycle-22 Z1**: post-train-only — use cycle-26's ranker model in a batched forward pass over all N×k=10 candidate pairs once, build a static priority array, then 2-opt sweeps read from this array instead of cKDTree-NN. Avoids the K_in>K_use OOD trap of I3 (cycle 4/8) because the filter is trained on the actual move distribution, not just geometry.

## Appended (research: modern-learned/hybrid — manual injection, plateau break)

User-requested research injection at neural cycle ~31 (val_cost
plateau around 1,551,636). Sources: foundational neural-TSP
literature (Bello/Vinyals/Kool/Hottung lineage); no Santa-specific
writeups consulted.

- M7. **Tiny single-layer attention model for partial-tour
  construction**: replace the NN seed with a learned construction
  model. Single multi-head attention layer (4 heads, 32-dim) takes
  the partial tour's last 8 cities + the unvisited candidate set,
  outputs softmax over candidates. Train via REINFORCE on tour-cost
  reward (R6 below) or via imitation on LKH-derived tours. Even at
  ~50K params it can encode "global topology awareness" the greedy
  NN cannot. Replaces just the construction phase, not the local
  search — keeps the existing learned ranker intact.
  [src: Vinyals 2015 Pointer Networks NIPS; Kool, van Hoof, Welling
  2019 ICLR "Attention, Learn to Solve Routing Problems"]

- T8. **Imitation labels from short-LKH oracle on subtours**:
  current training data uses the solver's own accept/reject
  labels — these are quality-bounded by the solver itself. Instead,
  extract random 100-city subtours from the current best, run a
  short-budget LKH (off-the-shelf via PyConcorde or the C
  implementation; ~2s per subtour) to find their local optima, and
  label every move LKH considered as "accept if LKH took it, else
  reject." Higher-quality labels → tighter accept boundary → better
  ranker.
  [src: Joshi, Cappart, Rousseau, Laurent 2022 Constraints
  "Learning Heuristics for the TSP"; Helsgaun LKH-3]

- R6. **REINFORCE with val_cost reward (actor-critic)**: train the
  ranker end-to-end with policy gradient — at each 2-opt sweep, the
  model's output distribution over K=10 candidates is sampled, the
  resulting tour change yields a per-step reward (= -gain), and a
  rolling-average value baseline reduces variance. Bypasses the
  "what label is right?" question entirely; the loss is the actual
  metric. Risky (high variance, longer training) but the only
  approach where the model isn't bottlenecked by its label source.
  [src: Bello, Pham, Le, Norouzi, Bengio 2016 "Neural Combinatorial
  Optimization with RL"; Kool 2019 attention model with REINFORCE
  baseline]
