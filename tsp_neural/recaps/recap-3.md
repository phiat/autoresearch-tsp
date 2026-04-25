# Recap 3 — `tsp_neural/` rows 39–45

This recap covers cycles 39–45: the PILS knob-sweep plateau (rows 39–44) and
the C14 PILS+H=16 distill breakthrough (row 45). A sixth cross-class permutation
block (C14–C19) was seeded into ideas.md at `69f8fc7`; C14 is now confirmed, five
remain untested. HEAD at recap time is `51a0807` (PILSens2: workers 4→2), which is
NOT yet in results.tsv and is treated as in-flight.

---

## Summary of recap-2

- recap-2 covered cycles 35–38, the first experiments under the parallel-ILS
  substrate (`dd64693`, ~80 restart attempts per 300s run vs the old ~8–15).
- All 4 rows discarded. C8 MLP H=32→16 (+401, noise), I4 ε-greedy (+113, noise),
  E1 GPU-batched (+3,062 — staleness multiplied sweep count 4x, killed restart room).
- **Comparability break: cycles 35+ are not directly comparable to cycles 1–34.**
  The exploration budget increased roughly 5–8x.
- Best on exit from recap-2: **1,551,635.94** (cycle 28, `56fd812`), unchanged.
- Pending direction: exploit the 80-restart capacity rather than add overhead.
  Top recommendations were C13 k-means subtour LNS and I8 multi-start construction.

---

## New results

| # | commit | val_cost | Δ best | status | description |
|---|--------|----------|--------|--------|-------------|
| 39 | dd64693 | 1,551,348.26 | **−287** | keep | PILS baseline (workers=8, budget=25s): meta substrate; 10x more restarts (80 vs 8); NEW BEST |
| 40 | 9469212 | 1,551,699.49 | +351 | discard | PILSw14: 14 workers on 14-core box; 140 restarts but smaller per-batch gains |
| 41 | b781574 | 1,551,723.67 | +375 | discard | PILSb15: 15s budget too short; only 2 accepted batches vs 5 baseline |
| 42 | aed774b | 1,551,468.83 | +121 | discard | PILSb40: deeper restarts; batch 1 −975 fast but only 3 NEW BESTs total; sweet spot is 25s |
| 43 | 0348272 | 1,551,728.19 | +380 | discard | PILSmix {2,2,2,2,1,1,3,3}: 1x too small, 3x too large in 25s; 4 accepts vs 5 baseline |
| 44 | 91a246a | 1,551,912.28 | +564 | discard | PILSlns win=200: scramble too destructive; VND can't heal+improve in 25s |
| 45 | 30d88f0 | 1,551,910.96 | +563 | discard | PILSlns50: 50-city scramble same pattern as win=200 (+563); LNS workers contribute nothing |
| 46 | 0d1a8c9 | **1,551,305.60** | **−43** | keep | C14 PILS+H=16 distill: NEW BEST; 6 accept batches (vs 5); inference 12.3B vs 10.7B; speed lever applies in parallel |

**Best: 1,551,305.60** — −25,993 (−1.65%) from baseline. 2 keeps, 6 discards,
0 crashes, multiple reverts executed cleanly by the loop.
*(Row 38 E1 GPU is also in recap-2; included here for continuity. New rows this
recap: 39–46.)*

**In-flight:** HEAD `51a0807` — PILSens2 (workers 4→2, more CPU per trajectory).
run.log shows the *C14 run* output (val_cost 1,551,305.60, 10 batches, 6 accepted);
PILSens2 result is not yet in results.tsv.

---

## What worked / didn't

- **PILS baseline (cycle 39, −287):** Simply parallelising ILS across 8 workers
  with a 25s per-worker budget broke the 7-cycle plateau. 80 restart attempts vs
  the old ~8 gave enough sampling diversity to find a better basin. The prior best
  (cycle 28) had exhausted what sequential ILS could reach.

- **PILSw14 (cycle 40, +351):** Filling all 14 physical cores contended on shared
  memory and CPU scheduler; each worker got less effective throughput. 140 restart
  samples did not compensate — per-sample quality degraded faster than quantity
  grew. The 8-worker sweet spot is below the core count.

- **PILSb15 (cycle 41, +375):** 15s worker budget was too short for VND to fully
  converge from a perturbed state. Only 2 accepted batches vs 5 at baseline. Workers
  found fewer distinct local optima and the pool quality dropped.

- **PILSb40 (cycle 42, +121):** Deeper 40s workers found a strong batch 1 (−975)
  but with fewer total batches (3 vs 5 accepted) the tail of improvements was cut
  off. 25s balances depth vs breadth — 40s is above the knee.

- **PILSmix perturbation strengths (cycle 43, +380):** Mixing 1x/2x/3x per-worker
  perturbation recycled the sequential ILS lesson: 1x too weak to escape, 3x too
  far to recover in 25s. The result reproduced cycle 20's sequential finding
  (variable perturbation < fixed 2x) in the parallel setting. The 2x sweet spot is
  a property of the tour geometry, not the parallelism level.

- **PILSlns win=200 + win=50 (cycles 44–45, +563/+564):** Windowed scramble LNS
  is too destructive for a 25s worker budget. The VND cannot heal a 50–200-city
  scramble and improve further within the time limit. Both variants produced nearly
  identical regression, suggesting the failure mode is budget exhaustion in repair,
  not window size — pure 2x double-bridge is the right perturbation mechanism.

- **C14 PILS+H=16 distill (cycle 46, −43):** The H=16 MLP (449 params, AUC 0.9992)
  runs 2.7x faster per inference than H=32. In the parallel regime each worker's
  25s VND IS bounded by inference cost (80 restarts × depth), so the speed-up
  directly translates to deeper VND per worker. The solver got 6 accepted batches
  vs 5 at baseline and 12.3B inference calls vs 10.7B. Cycle 36 sequential C8
  failed (+401) precisely because sequential ILS wasn't inference-bound; the lever
  only works where inference is the bottleneck, which is in the parallel arm.

---

## Updated trial directions

Ranked by estimated probability of clearing the ~500 noise floor under the PILS
regime:

1. **C15 — PILS + Z1 prime-aware Or-opt boundary check** (untested, fresh from
   `69f8fc7`): extend the cycle 22 prime-aware accept test to `or_opt_sweep`. Or-opt
   currently uses pure Euclidean gain; at steady state many Or-opt accepts touch a
   10th-step boundary. Z1 on 2-opt alone gave −105 sequential; with 80 PILS workers
   each running Or-opt deeply, per-worker −50 compounds across batches.
   [ideas.md C15]

2. **C19 — PILS + parallelized initial converge** (untested): replace the ~30s
   sequential `_vnd_local(NN_tour)` with a first PILS batch of 8 workers each
   perturbing the raw NN tour. Saves the sequential bottleneck and adds starting
   diversity. The initial converge is currently the single largest non-parallel
   chunk of the budget.
   [ideas.md C19]

3. **C16 — PILS + multi-best parent rotation** (untested): maintain top-3 tours;
   workers split 3/3/2 across parents. Probes different basins than single-parent
   monoculture. Low implementation cost; diversification without touching the
   per-worker mechanism.
   [ideas.md C16]

4. **C18 — PILS + Or-opt-2 chain** (untested): add 2-city segment relocation as
   a third VND move type. Cycle 20 sequential Or-opt-2 regressed because it ate
   budget without restarts; with 25s focused PILS workers the dynamic is different.
   Compounds the cycle 14 (C1) breakthrough mechanism.
   [ideas.md C18]

5. **C17 — PILS + I2 threshold sweep across workers** (untested): workers 0–3 use
   τ=0, 4–5 τ=−2 (permissive), 6–7 τ=+2 (strict). Unlike PILSmix (perturbation
   strength mix), this attacks the acceptance criterion not the perturbation — a
   genuinely different diversification axis.
   [ideas.md C17]

6. **C13 — k-means subtour LNS** (carry-forward from recap-2): partition 197K
   cities into ~1000 clusters of ~200, run full VND locally, splice back. The
   GLOP-style partition approach is still the largest untried architectural change.
   May pair well with PILS: run one PILS arm that applies k-means LNS instead of
   double-bridge.

7. **M8 — Tour-position cyclic features** (carry-forward): add sin/cos of rank/N
   to MLP input, retrain on T7 data. Low risk single retrain; DACT showed
   positional encoding is load-bearing for improvement models.

---

## Ideas library

- Seed ideas (cycle 0): 25 items.
- Appended (research: modern-learned — cycle 15 tick): 5 items (M6/T6/I6/R5/E6).
- Appended (cycle 20 self-generated tick): 3 items (C6/I7/C7).
- Appended (permute: cross-class combinations — cycle 28 tick): 5 items (C8–C12).
- Appended (research: manual injection at cycle ~31): 3 items (M7/T8/R6).
- Appended (research: modern-learned — cycle 35 tick, `1495c60`): 6 items (M8/E7/T9/I8/C13/R7).
- Appended (permute: cross-class combinations after PILS-tuning plateau, cycle 43, `69f8fc7`): 6 items (C14–C19).
- **Total: 53 items.** C14 confirmed working. C15–C19 fresh and untested.
  Next growth tick due at approximately cycle 48.

---

## State

- Branch: `main`
- Last kept commit: `0d1a8c9` — "C14 PILS+H=16 distill" (val_cost 1,551,305.60)
- In-flight commit: `51a0807` — PILSens2 (workers 4→2); NOT yet in results.tsv;
  run.log shows the preceding C14 run's output (1,551,305.60)
- `results.tsv`: 45 data rows + 1 header = 46 lines (row 46 = C14 at `0d1a8c9`)
- `ideas.md`: 53 items, last appended cycle 43 (`69f8fc7`)
- Submission: `submissions/submission.csv` (C14 best, val_cost 1,551,305.60)
- `.recap-pending`: 44 (to be deleted after this recap)
- Health: **positive momentum — two consecutive NEWBESTs (PILS baseline −287,
  C14 −43); PILS 8w/25s/2xDB/H=16 is the confirmed champion; five fresh C-class
  cross-permutations (C15–C19) are the next untried vector; in-flight PILSens2
  will confirm or refute the workers=2 direction.**
