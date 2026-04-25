# Recap 6 — `heuristic/apr25` continued

Covers results.tsv rows #37–#43 (commits `a06faaf` through `f2c74eb`).
Recap-5 closed at row #36 / commit `80ccd53` (X8c, 1,547,420.96) after
two consecutive discards that confirmed X8's restart-frequency and
smoothing-depth are both at their optima. Rows 37-43 extended a discard
streak: all seven new experiments failed, spanning candidate-split widths
(X9), regret-2 LNS repair (Reg2), compound kicks (P5), adaptive bandit
arm weights (H6), GLS edge-penalty augmentation (Z5), restart LNS frac
enlargement (X8d), and SS-heavy arm mixing (SShv). Best val_cost is
unchanged at 1,547,351.05 (X8, row #34). No in-flight experiment as of
this recap.

## Summary of recap-5

- Opened from best 1,547,643.99 (LNSt, row #26).
- LNS-prime bias=4 (#27, -170, keep) — destroy biased 4x toward
  penalty-origin cities; first demonstration that penalty targeting
  directly improves LNS quality. New best 1,547,473.52.
- LNS-prime8 bias=8 (#28, -53, keep) — doubled bias narrowed but
  still productive. New best 1,547,420.96. Vein narrowing visible.
- LNSttt/LNSp/LNS-prime16/LNS-prime8+frac15 (#29-32, all discard) —
  4-for-4 streak confirmed frac=1%, bias=8, arm-prob=1/3 as joint
  optima; vein closed.
- X5: prime_swap in LNS repair (#33, +1,543, discard) — Z1-integrated
  failure mode repeated; inner-loop overhead never free.
- X8: P4 restart + single LNS-prime smoothing (#34, -70, keep) —
  priming fresh NN tour toward penalty-aware structure before ILS
  resumes. New best 1,547,351.05.
- X8b RESTART_AFTER=25, X8c 3x smoothing (#35-36, both +70, discard) —
  restart frequency and smoothing depth confirmed at optima.
- **Best at end of recap-5: 1,547,351.05** (X8, commit `8a1c432`).
  19 total discards through row 36.

## New results

| # | commit | val_cost | delta best | status | description |
|---|---|---|---|---|---|
| 37 | a06faaf | 1,547,893.20 | +542 | **discard** | X9: candidate split K=7/K=4 — wider 2-opt finds 39 shallow moves vs 18 deep (k=4 right for whole stack) |
| 38 | 2110647 | 1,547,928.49 | +577 | **discard** | Reg2: regret-2 LNS repair — too-coherent insertion, only 9 improvements vs 18 (random order is feature) |
| 39 | da50613 | 1,548,197.18 | +846 | **discard** | P5: k=2 stacked double-bridge — over-disrupts (9 improvements vs 18 in X8) |
| 40 | da616d1 | 1,548,096.14 | +745 | **discard** | H6: bandit arm weights — uniform success rates (3-7%), softmax stayed near 1/3 each (rng drift effect) |
| 41 | 7d54fae | 1,547,420.96 | +70 | **discard** | Z5: GLS lam=1.0 — accumulated edge penalties dilute X8 post-restart improvement |
| 42 | 033e74e | 1,547,420.96 | +70 | **discard** | X8d: restart-only LNS frac 4% — bigger destroy hurts post-restart basin (frac=1% optimal even at restart) |
| 43 | f2c74eb | 1,547,793.02 | +442 | **discard** | SShv: SS-heavy mix 0.5/0.25/0.25 — 12 improvements vs 18 in X8 (per-call success rate != per-budget productivity) |

**Best: 1,547,351.05** (X8, commit `8a1c432`) — -14.63% from baseline
(`dd8df32`, 1,812,602.19). 26 total discards through row 43.
All 7 new rows are discards; 9-run discard streak extends from row 35.

## What worked / didn't

- **X9: candidate split K=7/K=4 (#37, discard, +542).** The hypothesis
  was that 2-opt benefits from a wider candidate window (K=7, as H1k7 was
  a prior keep) while LNS repair should stay tight (K=4). In practice,
  wider 2-opt found 39 moves vs 18 in X8 but those extra moves were
  shallow. The K=4 candidate list is calibrated to the current VND
  structure; splitting by operator breaks coherence between 2-opt and
  Or-opt passes that share the same neighbor set. H1k7 was a stand-alone
  win before Or-opt was as developed; optimal k is architecture-dependent
  and the current stack wants k=4 throughout.

- **Reg2: regret-2 LNS repair ordering (#38, discard, +577).** Replacing
  random cheapest-insert order with regret-2 ordering made reinsertion too
  coherent (9 improvements vs 18). The LNS-prime destroy step already picks
  cities with structure (penalty-origin bias); the repair step benefits from
  randomness to avoid re-creating the same local optima. Random insertion
  order is a feature, not a bug, when the destroy step is already
  structured.

- **P5: k=2 stacked double-bridge (#39, discard, +846).** Compound kick
  over-disrupts: only 9 ILS improvements vs 18 in X8. Single double-bridge
  is the right perturbation magnitude for the current tour quality; stacking
  makes the perturbation too large for the 300s budget to recover. This
  confirms the single-DB finding: the current tour is in a deep enough basin
  that stronger kicks land outside the recovery envelope.

- **H6: adaptive bandit arm weights (#40, discard, +745).** Success rates
  were nearly uniform across all three arms (3-7%), so the softmax stayed
  close to uniform throughout the run. The bandit never had enough signal to
  differentiate arms — the 300s budget produces too few samples for a
  meaningful softmax shift. The fixed 1/3 split is as good as any learned
  policy at this time scale.

- **Z5: GLS edge-penalty lam=1.0 (#41, discard, +70).** Accumulated edge
  penalties augmented the 2-opt cost function but conflicted with the
  post-restart state: the X8 LNS-prime smoothing step operates on a fresh
  NN tour where old penalty history is irrelevant. GLS global edge state
  conflicts with local-search quality after a restart. Result tied exactly
  to X8c discard (+70), indicating GLS adds no net signal over the current
  ILS structure.

- **X8d: restart-only LNS frac 4% (#42, discard, +70).** Enlarging the
  LNS destroy fraction at restart from 1% to 4% hurt post-restart basin
  quality just as it did in the mid-run LNS frac experiment (row #27).
  frac=1% is the global optimum regardless of whether applied mid-run or
  at restart. Result again tied to +70, confirming this is the local floor
  for easy perturbation-strength changes around the current stack.

- **SShv: SS-heavy arm mix 0.5/0.25/0.25 (#43, discard, +442).** Routing
  half the arm budget to segment-shift produced 12 improvements vs 18 in
  X8 with uniform arms. The H6 bandit measured per-call success rate; SShv
  acted on that signal. But per-call success rate != improvements per wall-
  clock second: LNS-prime calls are slower but each call moves the tour
  more than SS calls. The uniform arm split is the effective budget
  allocation; per-call success is a misleading proxy.

## Updated trial directions

1. **Z2e — penalty-aware 2-opt scoring**: Highest-EV untried idea.
   Track positions k%10==0 during 2-opt, apply real penalty delta only
   at boundary moves, pure-euclidean elsewhere. LNS-prime wins show
   penalty-origin targeting is productive; Z2e brings that awareness
   directly into move-acceptance without destroy-repair overhead. The
   D5 pos[] idea enables O(1) boundary detection to keep this cheap.

2. **C6 multi-start NN construction**: Basin-diversity lever. Build
   5-10 NN tours from random starts (~5-10s each at E1 speed), keep
   the best as seed, then full ILS. X8 LNS-prime smoothing shows basin
   quality at ILS entry matters; C6 improves the very first basin.
   Lower risk than LNS variants since it only affects construction.

3. **X11 — GLS-penalty-biased LNS destroy**: Bias LNS city selection
   toward cities incident to high-penalty edges (GLS-style edge memory)
   rather than only penalty-origin positions. Z5 (global GLS) failed
   because it conflicted with post-restart state; X11 sidesteps this by
   using the GLS history only in LNS destroy selection, not in 2-opt
   accept scoring. Merges two proven penalty-aware signals without
   inner-loop overhead.

4. **Or-opt L=4,5 reversed (O4r45)**: Combine O4r (reversed insertion,
   L=2,3, row #9) with the L=4,5 extension (row #12). Both were
   independent keeps; no new mechanism required. Low-risk composition.

5. **X7 — local Or-opt sweep around reinserted regions**: After each
   LNS reinsertion batch, run a short Or-opt(L=4,5) sweep restricted
   to just-reinserted cities and their immediate neighbours. Lower
   overhead than X5/X6 since geographically scoped. Targets the rough
   seam cheapest-insert leaves.

6. **X10 — prime_swap_pass after each accepted ILS improvement**: Invoke
   Z1 once per ILS accept rather than once at end. Cheap (~1ms per call),
   targets boundary moves while geometric context is still hot. Pure-Z1
   cadence escalation, low risk.

7. **X6 — Or-opt-segment repair inside LNS-prime**: When reinserting,
   group 2-3 originally-adjacent removed cities as a segment and apply
   O4r-style forward-vs-reversed insertion test rather than per-city
   cheapest-insert. Combines O4r (reversed-segment keep) with LNS-prime
   path. Distinct from X5 (which added prime-swap, not segment-orientation).

## Ideas library

- 46 items total: 30 seed + 3 cycle-1 (E1, L7, Z4) + 4 cycle-3
  (P4t, O4r45, Z2e, LNS) + 5 research-append (Z5, P5, D5, X11, H6)
  + additional permute-append (X5-X10).
  Last appended: research cycle (Z5/P5/D5/X11/H6 block).
- 43 logged rows now. From the research-append batch: P5 (#39, discard),
  H6 (#40, discard), Z5 (#41, discard) are all exhausted. D5 and X11
  remain untried from that batch.
- Recommended next additions after next ~3 cycles:
  - **Z2e-fast**: restrict penalty-aware scoring only to pairs where one
    endpoint is within 2 positions of a k%10==0 boundary.
  - **X11-lite**: D5 pos[] array for O(1) boundary detection combined
    with Z2e — enables both ideas cheaply in a single commit.
  - **C6-budget**: multi-start NN with a fixed 20s construction budget,
    then full ILS on the best tour found.

## State

- Branch: `main`; HEAD is `35d327f` (revert of SShv).
- Last kept experiment commit: `8a1c432` (X8, val 1,547,351.05).
- In-flight: none. `35d327f` revert is the current HEAD.
- 43 logged rows in `results.tsv` (17 keeps, 26 discards).
- `ideas.md`: 46 items; Z5, P5, H6 from research-append now logged and
  exhausted. D5 and X11 remain untried from that batch.
- Submission: `submissions/submission.csv` at val 1,547,351.05.

Loop is in a deep discard streak (rows 35-43, 9 consecutive). Best
val_cost has not moved since row 34 (X8, commit `8a1c432`). Total
improvement is -265,251.13 cost units from baseline. The perturbation-
tuning (P5, H6, SShv, X8d), GLS-augmentation (Z5), and repair-ordering
(Reg2, X9) veins are all exhausted. The clearest remaining angles are
Z2e (penalty-aware 2-opt accept scoring, never tried cleanly) and C6
(multi-start construction), both targeting mechanisms untouched so far.
X11 (GLS-biased LNS destroy) is the only penalty-hybrid not yet tried.
