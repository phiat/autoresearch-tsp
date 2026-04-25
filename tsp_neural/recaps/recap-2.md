# Recap 2 — `tsp_neural/` rows 35–37

This recap covers cycles 35–37, the first three experiments run after
the `dd64693` parallel-ILS infrastructure commit. All three cycles were
discards landing at or above the best (1,551,635.94). A second meta
event — the cycle-35 research tick at `1495c60` — added 6 new ideas
(M8/E7/T9/I8/C13/R7) to ideas.md.

**IMPORTANT — comparability break after row 34.** Commit `dd64693`
(not itself a scored experiment) ported the heuristic loop's
multiprocessing-fork parallel-ILS pattern into neural's `solve.py`.
With `ILS_WORKERS=8` and `ILS_WORKER_BUDGET=25s` the solver now
dispatches ~80 restart attempts per 300s run (vs ~8–15 previously).
Val_cost numbers from cycle 35 onward ARE NOT comparable to cycles 1–34
on an apples-to-apples basis; the exploration budget changed roughly 5–8x.

---

## Summary of recap-1

- Bootstrap cycles 1–3: 25M-row harvest, 2-layer MLP (1409 params), AUC
  0.9992 on K=10 candidates.
- Key integration wins: I5 first-improving-in-score-order (cycle 9,
  −4,597 from baseline), then C1 VND learned-2opt + Or-opt + ILS (cycle
  14, −17,718, the single biggest gain of the project).
- ILS tuning confirmed 2x double-bridge as the sweet spot; 1x/3x/variable
  all regressed.
- Z1 prime-aware boundary acceptance (cycle 22) gave −105; MAX_VND_OUTER=10
  cap (cycle 28) gave −822 by restoring ILS room that deep initial-converge
  had been eating.
- Prior best on exit from recap-1: **1,551,635.94** (cycle 28, `56fd812`),
  −25,663 vs baseline (−1.63%).
- Cycles 29–34 were a tuning plateau: all bit-identical or sub-noise. Every
  knob within the current pipeline structure had been swept.

---

## New results

| # | commit | val_cost | Δ best | status | description |
|---|--------|----------|--------|--------|-------------|
| 35 | 33aec7a | 1,551,635.94 | 0 | discard | ILS adaptive strength: no stalls long enough to trigger; bit-identical to cycle 28 |
| 36 | de838e6 | 1,552,036.93 | +401 | discard | C8 distill MLP H=32→16 (449 params, AUC 0.9993): only +1 ILS restart gained; +401 within noise |
| 37 | 31cbdf4 | 1,551,748.95 | +113 | discard | I4 ε=0.10 ILS-only sampling: bigger per-restart lifts but +113 from best; within noise |
| 38 | fb49128 | 1,554,697.62 | +3,062 | discard | E1 GPU-batched: works but score staleness 4x'd sweep count (438 vs 110); only 2 restarts fit; +3,062 |

**Best: 1,551,635.94** — −25,663 (−1.63%) from baseline, unchanged since
cycle 28. 4 new rows all discarded; 0 crashes; 0 reverts in this window
(all reverted cleanly by the loop).

Note: row 35 (`33aec7a`) was already in results.tsv before the parallel-ILS
meta commit; it ran under the old sequential solver. Rows 36–38 ran under
parallel-ILS. The val_cost improvement signal from the parallel upgrade has
not yet shown up — the three experiments tested changes that added overhead
(half-sized model, epsilon noise, GPU batch), each eating the ILS throughput
that the parallel upgrade was supposed to unlock.

---

## What worked / didn't

- **C8 MLP distill H=32→16 (cycle 36, +401):** Reducing hidden width from 32
  to 16 halved scoring cost but only freed room for one extra ILS restart.
  The net result was within the ~500 noise floor. The MLP is not the dominant
  cost at this point; the VND convergence body is. Speedup must be much larger
  (C9-style dot-product or C12-style cached pre-rank) to materially shift the
  restart count.

- **I4 ε-greedy ILS sampling (cycle 37, +113):** Per-restart lifts were larger
  in absolute terms (+517, +192) but the initial-converge quality was unchanged
  (1,552,458), so the epsilon random picks added variance without a better
  starting floor. Net +113 is within noise. Randomisation in candidate selection
  is not a useful diversification lever here — double-bridge perturbation already
  provides tour-level diversity; the exploit phase should stay deterministic.

- **E1 GPU-batched inference (cycle 38, +3,062):** The GPU path itself works
  (no crashes, GPU confirmed active). The failure mode: precomputing all K=10
  candidate scores for a full sweep creates score staleness — by the time the
  sweep reaches city i, the tour has changed since those scores were computed
  for earlier cities. This multiplied sweep count by 4x (438 sweeps vs 110
  sequential), consumed 158s of the 300s budget in initial-converge, and left
  room for only 2 ILS restarts (vs 8+ in cycle 28). The E1 approach is correct
  in principle but needs (a) a bigger / GPU-native model to justify the batching
  overhead, and (b) a GPU-side feature build so the pipeline is entirely on-device.
  E1 alone against the current tiny 1409-param MLP is a net loss.

---

## Updated trial directions

Ranked by estimated probability of clearing the ~500 noise floor under the new
parallel-ILS regime (80 restart attempts per run):

1. **C13 — Geographic k-means subtour reoptimization** (new, top recommendation):
   partition 197K cities into ~1000 clusters of ~200, run full VND locally per
   cluster, splice back. This is a large-neighbourhood destroy-and-repair that
   bypasses the 200-outer-round VND cap by working in small independent
   neighbourhoods — directly attacks the plateau in a way no knob-tuning can.
   scipy.cluster.vq.kmeans2 requires no new deps. Estimated lift: largest
   remaining vector, the GLOP paper showed partition-based local search on TSP
   breaks plateaus reliably. [src: ideas.md C13]

2. **I8 — Best-of-8 multi-start construction** (new from cycle-35 tick):
   build 8 greedy tours from distinct starting cities (~0.5s extra), keep the
   lowest-cost as VND input. POMO showed multi-start construction consistently
   gives a higher VND floor. Zero training changes, trivial to implement, and
   the parallel-ILS regime can absorb the 0.5s cost easily. [src: ideas.md I8]

3. **C9 — M2 city-embedding dot-product model** (~50x faster scoring than MLP):
   per-city 32-dim embedding, score(a,c) = ⟨emb[a], emb[c]⟩ + bias. If quality
   holds, the parallel worker pool gets more restarts per worker budget.
   Recommended over C8/C12 because it replaces the inference path entirely rather
   than shaving the existing path.

4. **M8 — Tour-position cyclic features for ranker** (new from cycle-35 tick):
   add sin/cos of rank/N to the MLP input (11 features vs 9), retrain on T7 data.
   DACT showed positional encoding is load-bearing for improvement models. Low
   risk, single retrain cycle.

5. **T9 — 8-fold symmetry augmentation on existing harvest** (new):
   4 rotations × 2 reflections of x/y fields in the feature vector, 8x effective
   training set, zero new solver runs. Could tighten the accept boundary in
   under-represented regions.

6. **E7 — EAS-Lay per-restart adapter fine-tune** (new from cycle-35 tick):
   small adapter layer (32→8→32) fine-tuned for ~50 SGD steps on the accepted
   moves from the previous ILS restart before the next restart; keeps base model
   frozen. Under the parallel worker regime, each worker could carry its own
   adapter — genuine per-trajectory adaptation.

7. **R7 — Deferred-reward (survival) labels** (new from cycle-35 tick):
   label a move 1 only if it survives to the converged local optimum (not just
   "positive gain at time of accept"). Filters out moves that look improving but
   get undone. Higher-quality labels without an external oracle.

---

## Ideas library

- Seed ideas (cycle 0): 25 items across M/T/R/I/E/C classes.
- Appended (research: modern-learned — cycle 15 tick): 5 items (M6/T6/I6/R5/E6).
- Appended (cycle 20 self-generated tick): 3 items (C6/I7/C7).
- Appended (permute: cross-class combinations — cycle 28 tick): 5 items (C8–C12).
- Appended (research: manual injection at cycle ~31): 3 items (M7/T8/R6).
- Appended (research: modern-learned — cycle 35 tick, `1495c60`): 6 items (M8/E7/T9/I8/C13/R7).
- **Total: 47 items.** Last appended: cycle 35 (4 cycles ago; next growth tick
  due at cycle 40).

---

## State

- Branch: `main` (single branch; neural + heuristic loops both commit here)
- Last kept commit: `56fd812` — "VND cap MAX_OUTER=10" (val_cost 1,551,635.94); unchanged since cycle 28
- Parallel-ILS infrastructure commit: `dd64693` (meta only — not a scored experiment)
- In-flight commit: none (run.log confirms cycle 38 = `fb49128` E1 GPU completed; reverted by `b894293`)
- `results.tsv`: 37 data rows + 1 header = 38 lines
- `ideas.md`: 47 items, last appended cycle 35 (`1495c60`)
- Submission: `submissions/submission.csv` (cycle 28 best, val_cost 1,551,635.94)
- `.recap-pending`: 36 (to be deleted after this recap)
- Health: **plateaued — parallel-ILS infra in place but yield not yet positive**.
  All three new-era experiments added overhead that ate the extra restart budget.
  Next cycle must exploit the 80-restart capacity rather than fight it.
  Priority: C13 k-means subtour LNS or I8 multi-start construction.
