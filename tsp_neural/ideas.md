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

## Appended (research: modern-learned — cycle 35 tick)

Sources surveyed: DACT (Ma et al., NeurIPS 2021, arXiv:2110.02544),
EAS (Hottung et al., ICLR 2022, arXiv:2106.05126), Sym-NCO (Kim et al.,
NeurIPS 2022, arXiv:2205.13209), POMO (Kwon et al., NeurIPS 2020,
arXiv:2010.16011), GLOP (Ye et al., AAAI 2024, arXiv:2312.08224).
All ideas avoid new dependencies; partition step uses scipy.

- M8. Add two tour-position cyclic features to the existing MLP input — sin(2π·rank_i/N) and cos(2π·rank_i/N) where rank_i is city i's position index in the current tour — so the ranker distinguishes moves that cross the tour's "seam" (high positional distance) from local moves; retrain on existing T7 data with the expanded 11-feature input — addresses the plateau by giving the ranker information DACT showed is load-bearing for improvement models. [src: DACT cyclic positional encoding, arXiv:2110.02544]

- E7. Insert a single bottleneck adapter layer (Linear 32→8→32 with ReLU, ~320 params) between the two existing hidden layers of the frozen MLP and fine-tune only that adapter for ~50 SGD steps on the accepted moves from the most recent ILS restart before each subsequent restart; this is the EAS-Lay principle applied to our ranker — the base model stays fixed (no OOD risk), the adapter shifts the scoring boundary toward the current tour's local geometry; targets the 5-10x speed goal by keeping the forward pass tiny while gaining per-restart adaptivity. [src: EAS Hottung et al. ICLR 2022, arXiv:2106.05126]

- T9. For each (features, label) row in the existing moves/ harvest, generate 7 symmetric copies via coordinate transforms (4 rotations × 2 reflections of the x/y fields in the feature vector) before training; costs zero extra solver runs and 8x's effective training set size — directly addresses training data volume without a new harvest, and Sym-NCO showed this alone cuts optimality gap by ~0.2% for similarly-sized models. [src: Sym-NCO Kim et al. NeurIPS 2022, arXiv:2205.13209]

- I8. Replace the single NN-greedy construction seed with a best-of-8 multi-start: build 8 greedy tours from 8 random distinct starting cities (numpy vectorizable; adds ~0.5s), keep the lowest-cost tour as VND input — POMO showed that exploiting rotational symmetry via multiple starts consistently finds lower-cost initial solutions, giving VND a higher floor without any model change; costs no training and fits within the 300s budget. [src: POMO Kwon et al. NeurIPS 2020, arXiv:2010.16011]

- C13. Geographic k-means subtour reoptimization: use scipy.cluster.vq.kmeans2 to partition all 197K cities into ~1000 clusters of ~200 cities each, extract each cluster's contiguous subtour segment from the current best tour, run the full learned-VND (2-opt+Or-opt) locally on those ~200 cities treating them as a standalone TSP, then splice the improved subtour back in; this is a large-neighborhood destroy-and-repair that bypasses the 200-outer-round ILS cap by working in small independent neighborhoods — GLOP's partition concept without its GNN, implementable with scipy alone. [src: GLOP Ye et al. AAAI 2024, arXiv:2312.08224; scipy.cluster.vq]

- R7. Replace the immediate-gain binary label with a deferred-reward label: for each accepted move during a VND sweep, record whether the move survives to the *converged* local optimum (i.e., is it still in the tour at VND termination?); label = 1 only if it survives, else 0; this filters out moves that appear improving but get undone by later moves — higher-quality labels than the current "positive gain = 1" scheme without needing an external oracle like LKH; adds a post-sweep label-pass over the existing harvest pipeline. [src: EAS/DACT training philosophy on solution-level vs step-level credit; Costa et al. 2020 learning-2-opt DRL arXiv:2004.01608]

## Appended (permute: cross-class combinations after PILS-tuning plateau, cycle 43)

5 PILS-knob discards in a row (workers, budget, mix, lns200, lns50) confirm the 8w/25s/2xDB sweet spot. Permutations target *combinations* of kept ideas with the new PILS substrate — model × parallel, integration × parallel, engineering × parallel.

- C14. **PILS + C8 distilled H=16 ranker** (use existing `f6d5ff9.pt`, holdout AUC 0.9993): touch checkpoint mtime so workers load the smaller MLP; 2.7x faster scoring per worker → deeper VND in the same 25s budget → better per-batch local opt. Cycle 35 C8 failed solo because sequential ILS budget wasn't model-bound; in PILS each worker's depth IS bounded by inference cost — the speed lever applies where it didn't before. [permute: C8 + PILS]

- C15. **PILS + Z1 prime-aware Or-opt boundary check**: extend Z1 (cycle 22, prime-aware accept-test for 2-opt boundary 10th-step edges) to `or_opt_sweep`. Or-opt currently uses pure Euclidean gain; on tours where 90% of accepts ≤500 wide, a non-trivial fraction touch a 10th-step boundary. Prime-aware Or-opt should mirror the gain that `score_tour` rewards — same logic Z1 applied to 2-opt and got -105. With PILS workers each running Or-opt deeply, even per-worker -50 lift compounds across 80 restarts. [permute: Z1 + Or-opt + PILS]

- C16. **PILS + multi-best parent rotation**: maintain top-3 best tours; each batch's 8 workers split 3/3/2 across the parents (round-robin). Diversifies ILS exploration without losing depth — parent-2 and parent-3 likely live in *different basins* than the global best, so workers from them probe different neighborhoods. Avoids the single-parent monoculture failure mode where all 8 workers explore the same local region. [permute: PILS + ILS-2x + diversification]

- C17. **PILS + I2 threshold sweep across workers**: workers 0-3 use τ=0 (current), 4-5 use τ=-2 (more permissive — accepts marginal moves the ranker is unsure about), 6-7 use τ=+2 (stricter — only confidently-good moves). Each tau-bin probes a different "good move" boundary. PILSmix's strength-mix failed because all strengths attacked same problem; tau-mix attacks different problems (acceptance criterion, not perturbation). [permute: I2 (C11) + PILS]

- C18. **PILS + Or-opt-2 chain in worker VND**: add 2-city segment relocation as a third inner move type after 2-opt and Or-opt-1 in `_vnd_local`. Cycle 20 sequential Or-opt-2 chain regressed (+254) because it ate budget without restarts. With PILS each worker has a focused 25s VND from a perturbed seed — Or-opt-2 can find moves Or-opt-1 misses; the third move type compounds the C1 (cycle 14) breakthrough mechanism. [permute: C1 + Or-opt-2 + PILS]

- C19. **PILS + parallelized initial converge** (skip sequential converge): replace the ~30s sequential `_vnd_local(NN_tour, ...)` with a special first PILS batch where each worker takes the raw NN tour, applies a single small perturbation (1× double-bridge), and runs full 30s VND. Take best of 8 as initial best. Saves the sequential bottleneck and adds 8-way starting-point diversity; sequential converge is currently the single biggest non-parallel chunk of the budget. [permute: I8 + PILS + initial-converge]


## Appended (manual injection — bigger-model directive, post-cycle-47)

User-requested injection: the loop has been moving SMALLER (H=32 →
H=16, 449 params) because inference latency dominates inner loops.
This collapses the model-capacity axis. Inject ideas that try
BIGGER models paired with engineering tricks to keep inference
cheap. Source: general transfer-from-NCO-literature, no Santa-specific
material consulted.

- M9. **H=64 / H=128 MLP with mandatory paired E-class speedup**:
      train a 4-9k-param MLP (vs current 449), distill to numba inline
      forward, use only if the paired E-class change keeps per-call
      latency within 2× of H=16. Test variants H=64+E3 (numba distill),
      H=128+E3+fp16. The current H=16 win was empirical proof that the
      speed lever pays in parallel — bigger model + same speed lever
      may move the AUC ceiling further.
      [src: own cycle-46 C14 finding (speed lever applies in parallel)]

- M10. **Distill bigger teacher into smaller student**: train an H=128
      teacher on the full harvested dataset (offline, slow), use it to
      label a much bigger augmented dataset (e.g. negative samples per
      candidate position), then train an H=16 student on those labels.
      Student stays fast at inference; teacher's capacity flows in via
      label quality. Classical knowledge distillation.
      [src: Hinton et al. 2015, arXiv:1503.02531; widely used in NCO
       (e.g. Sun et al. DIFUSCO student variants)]

- M11. **Wider+shallower instead of deeper**: H=64 with ONE hidden
      layer (vs current 2 layers of H=16). Same param count budget but
      different inductive bias — wider single-layer MLPs have been shown
      to compete with deeper variants on simple-feature regression
      tasks; Or-opt features are exactly that. Tests whether the
      depth=2 in the current MLP is load-bearing.

- M12. **Edge-feature transformer head (~5k params)**: replace the
      MLP's tail with a single transformer-attention layer over the
      8-16 nearest neighbors of the candidate move's endpoints; pooled
      output → score. Kool 2019 attention model in micro form. GPU
      training is essentially free given current cycle budget; inference
      cost is the open question — pair with E2 (torch.compile).
      [src: Kool, van Hoof, Welling 2019 ICLR; transformer microheads
       are well-studied for edge-scoring]

- E8. **CUDA graph capture for batched inference**: replace per-call
      torch dispatch with a captured graph of the entire VND-batch
      forward pass. Eliminates per-call kernel launch overhead, the
      thing that killed naive E1. Pairs naturally with bigger models
      (M9-M12) where per-call overhead would otherwise dominate.
      [src: PyTorch CUDAGraph, torch.cuda.graph context manager]
