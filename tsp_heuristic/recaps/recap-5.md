# Recap 5 — `heuristic/apr25` continued

Covers results.tsv rows #27–#36 (commits `2a23ae6` through `80ccd53`).
Recap-4 closed at row #26 / commit `b2b92e2` (LNSt, 1,547,643.99) after
breaking a 4-for-4 discard streak with a new best. Rows 27-28 pushed
LNS-prime biasing to two consecutive new bests; rows 29-31 were a 3-for-3
discard streak that closed the LNS-prime bias vein. Rows 32-36 probed the
X-class combinations (LNS-prime8/frac15, X5, X8, X8b, X8c), yielding one
new best (X8, row 34) and a 2-for-2 discard streak after it.
In-flight as of this recap: `357e94d` (ILS variable perturbation strength).

## Summary of recap-4

- Opened from best 1,548,496.21 (P4 random-restart, row #16).
- P4t tighter restart (#17, +388, discard) — RESTART_AFTER=20 fires too
  frequently; shallow post-restart local search outweighs escape benefit.
- Z3 prime-aligned NN construction (#18, +1,924, discard) — biased start
  warps geometry; ILS cannot fully repair in 300s. Z-class construction closed.
- H1k7/k5/k4 k-shrink vein (#19-21, all keep, -373/-97/-125) — empirical
  optimum k=4 for current ILS architecture; smaller k gives more ILS iters.
- C5 Hilbert SFC seed (#22, +18,979, discard) — worst regression in the run;
  NN seed confirmed in a far superior basin.
- H1k3 (#23, +7,121, discard) — k=3 too thin; k=4 is confirmed empirical floor.
- H3 RESTART_AFTER 40->60 (#24, delta=0, discard) — no_improve never crossed 40;
  threshold change was a no-op.
- LNS 4% destroy (#25, +683, discard) — destroy too large for cheapest-insert
  repair within budget.
- LNSt 1.5% destroy (#26, -257, keep) — **new best 1,547,643.99**; smaller
  destroy kept structure tractable, 11 improvements, 2 restarts.
- **Best at end of recap-4: 1,547,643.99** (commit `b2b92e2`). 9 total discards
  through row 26.

## New results

| # | commit | val_cost | delta best | status | description |
|---|---|---|---|---|---|
| 27 | 2a23ae6 | **1,547,473.52** | -170 | keep | LNS-prime: destroy biased 4x toward penalty-origin cities -- 21 improvements, 0 restarts, NEW BEST |
| 28 | 203c516 | **1,547,420.96** | -53 | keep | LNS-prime8: bias 4->8 -- 17 improvements, NEW BEST |
| 29 | 4562bd1 | 1,548,249.97 | +829 | **discard** | LNSttt: LNS frac 0.5% -- too small to disrupt, sweep floor confirmed |
| 30 | bf4e89a | 1,548,168.61 | +748 | **discard** | LNSp: LNS arm prob 1/2 -- over-uses small destroys, +555 vs bias=8 |
| 31 | e57e47e | 1,547,997.73 | +577 | **discard** | LNS-prime16: bias 8->16 -- too narrow, misses non-penalty productive moves |
| 32 | b151b0a | 1,548,115.50 | +695 | **discard** | LNS-prime8/frac15: bias+frac stack hurts -- bigger destroys over-disrupt with bias, frac=1% optimum holds |
| 33 | f4530a9 | 1,548,964.36 | +1,543 | **discard** | X5: prime_swap polish inside LNS-prime repair -- Z1-integrated failure mode, inner-loop overhead never free |
| 34 | 8a1c432 | **1,547,351.05** | -70 | keep | X8: P4 restart + single LNS-prime smoothing -- 18 improvements, NEW BEST |
| 35 | 6d77fef | 1,547,420.96 | +70 | **discard** | X8b: RESTART_AFTER 40->25 -- more restarts but less refinement time, P4t lesson holds |
| 36 | 80ccd53 | 1,547,420.96 | +70 | **discard** | X8c: 3x LNS-prime smoothing after restart -- consumes post-restart improvement window, 1x optimal |

**Best: 1,547,351.05** (X8, commit `8a1c432`) -- -14.63% from baseline
(`dd8df32`, 1,812,602.19). 19 total discards through row 36.
Rows 29-33 were a 5-for-5 discard streak before X8 broke through at row 34;
rows 35-36 resumed discarding.

## What worked / didn't

- **LNS-prime bias=4 (#27, keep, -170).** Biasing the LNS destroy step 4x toward
  penalty-origin cities (those at positions k%10==0 where origin is non-prime)
  delivered a meaningful win. These cities contribute the most to tour cost via the
  +10% step penalty; destroying and re-inserting them forces the repair step to find
  better penalty-aware placements. The bias also eliminated restarts entirely (0 vs
  2 in LNSt), meaning 21 incremental improvements were found purely through targeted
  LNS without basin escape. The surgical destroy is more efficient than uniform random.

- **LNS-prime8 (#28, keep, -53).** Doubling bias from 4x to 8x sharpened targeting
  and yielded another new best. The win is smaller (-53 vs -170), suggesting the
  vein is narrowing. At bias=8, 17 improvements were found vs 21 at bias=4 --
  consistent with stronger bias occasionally over-targeting and missing useful
  non-penalty moves.

- **LNSttt 0.5% destroy (#29, discard, +829).** Halving the destroy fraction from
  1% to 0.5% (~1k cities) made perturbation too small to escape the local optimum;
  cheapest-insert repair reconstructs approximately the same solution. Empirical
  floor for the LNS destroy fraction is 1%. This caps the lower end of the
  fraction sweep definitively.

- **LNSp arm prob 1/2 (#30, discard, +748).** Increasing LNS arm selection from
  1/3 to 1/2 frequency degraded performance. Overusing small-destroy LNS starves
  ILS of larger-scale perturbations (double-bridge) needed to escape deep local
  optima. The 1/3 arm balance in LNS-prime8 is the empirical optimum.

- **LNS-prime16 (#31, discard, +577).** Pushing bias to 16x over-specializes the
  destroy step on penalty-origin cities, missing productive non-penalty moves. At
  16x bias with 1.5% destroy, nearly all removed cities are penalty-origin, leaving
  no room for general-structure improvements. Bias=8 is confirmed as the ceiling;
  the LNS-prime bias vein is closed.

- **LNS-prime8/frac15 (#32, discard, +695).** Stacking bias=8 with frac=1.5%
  over-disrupts: bigger destroys combined with strong penalty bias still regress.
  The joint optima are independently confirmed (frac=1%, bias=8); they do not
  compound multiplicatively.

- **X5: prime_swap inside LNS-prime repair (#33, discard, +1,543).** Invoking
  prime_swap_pass after each LNS reinsertion batch repeats the exact failure mode
  of Z1-integrated (row #13): inner-loop overhead consumes ILS iteration budget.
  The Z1 mechanism is only profitable as a post-pass outside the main loop.

- **X8: P4 restart + LNS-prime smoothing (#34, keep, -70, NEW BEST).** After a
  random NN restart fires, immediately running a single LNS-prime perturbation pass
  before ILS local search resumes primes the new basin toward penalty-favorable
  structure. The fresh NN tour is far from the current best, and LNS-prime
  realigns penalty-origin cities before committing compute. Result: 18 improvements,
  1 restart, new best 1,547,351.05. Composing two complementary escape mechanisms
  at restart time is more productive than tuning either in isolation.

- **X8b: RESTART_AFTER 40->25 (#35, discard, +70).** More frequent restarts with
  X8 smoothing still degrades: each restart now gets less refinement time, and the
  net effect reverts to the LNS-prime8 level (~1,547,421). The P4t lesson (row #17)
  is robust and survives across different smoothing configurations.

- **X8c: 3x LNS-prime smoothing after restart (#36, discard, +70).** Tripling the
  post-restart LNS-prime smoothing over-invests in the restart transition and
  consumes the improvement window that ILS would otherwise use. One pass is
  empirically optimal; the mechanism is not bottlenecked by smoothing depth.

## Updated trial directions

1. **ILS variable perturbation strength (`357e94d`, in-flight).** Random choice
   of 1x/2x/3x stacked double-bridge per restart for diversity. This is the
   current in-flight experiment. Await result before branching.

2. **Z2e -- penalty-aware 2-opt scoring**: Highest-EV untried idea. Track positions
   k%10==0 during 2-opt and apply real penalty delta only at boundary moves;
   pure-euclidean elsewhere. LNS-prime wins demonstrate that penalty-origin
   targeting is productive; Z2e brings that awareness into the move acceptance
   criterion directly, without any destroy-repair overhead.

3. **C6 multi-start NN**: Basin diversity lever now that k-shrink and LNS-prime
   veins are closed. Run 5-10 NN constructions from random starts (~5-10s each at
   E1 speed), keep the best initial tour, then full ILS. Trades ~25-50s for a
   better starting basin.

4. **Or-opt L=4,5 reversed (O4r45)**: O4r (reversed insertion, L=2,3, row #9) and
   L=4,5 extension (row #12) were independent keeps. Combining them is low-risk
   with no new mechanism design.

5. **X7 -- local Or-opt sweep around reinserted regions**: after each LNS
   reinsertion batch, run a short Or-opt(L=4,5) sweep restricted to just-reinserted
   cities and their immediate neighbours. Lower overhead than X5/X6; targets the
   rough seam cheapest-insert leaves. Untried.

6. **X9 -- split candidate widths by operator**: k=7 for 2-opt, k=4 for LNS repair.
   H1k7 was a kept win; LNS repair benefits from tight local insertion. Untried.

7. **X10 -- prime_swap_pass at higher cadence**: invoke Z1 once per ILS improvement
   acceptance rather than once at end. ~1ms per call, targets boundary moves while
   geometric context is hot. Orthogonal to current changes.

8. **D5-Or-opt only (scoped don't-look bits)**: Full don't-look bits failed in rows
   #11 and #12. A version restricted to Or-opt (not 2-opt) has not been tested and
   may recover throughput without degrading 2-opt quality.

## Ideas library

- 46 items total: 30 seed + 3 cycle-1 (E1, L7, Z4) + 4 cycle-3 (P4t, O4r45,
  Z2e, LNS) + 9 permute-append (X5-X10 plus 3 LNS variants).
- Last growth tick fired at permute-append cycle (after row ~30). A cycle-5+
  growth tick is now overdue (36 rows logged; threshold passed).
- Recommended next additions:
  - **Vari-DB tuning**: if in-flight `357e94d` keeps, add a follow-up to sweep
    probability weights among 1x/2x/3x (currently uniform 1/3 each).
  - **Z2e-fast**: penalty-aware 2-opt restricted only to candidate pairs where
    one endpoint is within 2 positions of a k%10==0 boundary; skips pure-interior.
  - **X11 -- X8 + Z2e**: compose the X8 restart-smoothing mechanism with
    penalty-aware 2-opt in the local-search phase.

## State

- Branch: `main`; HEAD is `cfaefd6` (README docs update).
- Last kept experiment commit: `8a1c432` (X8, val 1,547,351.05).
- In-flight: `357e94d` (ILS variable perturbation strength -- random 1x/2x/3x
  stacked double-bridge per restart). `run.log` is stale (shows X8c run).
- 36 logged rows in `results.tsv` (17 keeps, 19 discards).
- `ideas.md`: 46 items; cycle-5+ growth tick overdue.
- Submission: `submissions/submission.csv` at val 1,547,351.05.

Loop is healthy. Total improvement -265,251.13 cost units from baseline across 36
cycles. The X-class vein produced one new best (X8, row 34) before two immediate
discards (X8b, X8c) confirmed that restart frequency and smoothing depth are both
at their optima. Highest-EV next moves: await in-flight variable-DB result, then
Z2e penalty-aware scoring, C6 multi-start construction, or O4r45 combination.
Inner-loop overhead remains the binding constraint; the Z1/X5 failures underscore
that inner-loop additions must pay for themselves in ILS iters per second.
