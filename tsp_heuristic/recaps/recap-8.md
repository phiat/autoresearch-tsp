# Recap 8 — `heuristic/apr25` continued

Covers results.tsv rows #54–#59 (commits `c70e0ea` through `ec46552`),
plus one in-flight experiment (`b781574`, PILSb15) not yet in the ledger.
This recap opens from a 19-run discard streak and documents the parallel-ILS
exploration arc: 6 new rows, all discards. Best val_cost remains 1,547,351.05
(X8, `8a1c432`, row #34). Streak extends to 25 consecutive discards (rows
35–59).

## Summary of recap-7

- Opened from best 1,547,351.05 (X8, `8a1c432`, row #34); streak at 19.
- All 10 new rows (#44–#53) were discards.
- OrL67 (+676): L=6,7 sweeps eat ILS budget; L=1..5 is the bandwidth optimum.
- C6 (+2,642): multi-start NN costs ~25s construction; ILS budget loss dominates.
- OrRev (+1,554): reversed Or-opt order (5..1) lands in a structurally worse basin.
- GLS vein fully exhausted: Z5b (lam=0.1, exact tie), Z5d (lam=0.5, +70), Z5
  (lam=1.0, +70) — no lambda value improves over X8 in 300s budget.
- Reg2p (+577): regret-2 repair fails regardless of destroy method.
- LNSdual (+519): 4-arm split dilutes prime-bias arm; 3-arm balance is optimal.
- PrimePeriodic (+880): Z1 inside ILS loop is always too heavy; post-pass only.
- AdaptiveRestart (+88): closest near-miss, but restart timing luck is not
  reproducible; restart-timing vein now exhausted.
- ForcedLateRestart (+181): 20s is too late for post-restart convergence.
- **Best at end of recap-7: 1,547,351.05.** 36 total discards through row 53.

## New results

| # | commit | val_cost | delta best | status | description |
|---|---|---|---|---|---|
| 54 | c70e0ea | 1,548,329.75 | +979 | **discard** | RngCafe: rng seed 0xBEEF→0xCAFE — 3 restarts, 6 improvements; confirms X8=1,547,351 is rng-luck-dependent |
| 55 | 892f041 | 1,548,269.98 | +919 | **discard** | PILS-defaults: 8 workers × 25s — 528 iters in 274s; within-batch best feedback lost |
| 56 | 8f2746d | 1,547,573.57 | +222 | **discard** | PILSw4: 4 workers × 25s — 420 iters in 275s; best parallel result to date |
| 57 | 4a52e21 | 1,548,256.65 | +906 | **discard** | PILSx8: worker 0 dedicated to NN-restart every batch — slowest worker blocks batch, iters 420→92 |
| 58 | ec46552 | 1,548,511.55 | +1,160 | **discard** | PILSx8r: rare NN-restart at no-improve=10 batches — only 1 restart fired; parallel can't replicate sequential X8 mechanism |
| *(in flight)* | b781574 | *(in flight)* | — | *(pending)* | PILSb15: ILS_WORKER_BUDGET 25→15s; ~17 batches × 8 workers = 136 restarts; faster turnover, shallower per-restart |

**Best: 1,547,351.05** (X8, commit `8a1c432`) — −14.63% from baseline
(`dd8df32`, 1,812,602.19). 42 total discards through row 59.
Discard streak: 25 consecutive (rows 35–59). PILSb15 is in-flight; run.log
for the previous run (PILSx8r) shows 77 batches × 4 workers = 308 iters,
16 accepted batches, 1 NN-restart injected, final 1,548,511.55.

## What worked / didn't

- **RngCafe (#54, discard, +979).** Changing the ILS seed from 0xBEEF to
  0xCAFE produced a materially different trajectory: 3 restarts, only 6
  improvements, landing at 1,548,329.75. This confirms that X8's score of
  1,547,351.05 is rng-luck-dependent and not a robust property of the
  algorithm. Any experiment that happens to align with the 0xBEEF basin gets
  the benefit; most seeds do not. This underscores that the true ceiling for
  the sequential solver may be above or below 1,547,351.05 depending on
  random initialization. Structural improvements must beat the lucky seed, not
  just match it.

- **PILS-defaults (#55, discard, +919).** The initial parallel-ILS scaffold
  (commit `892f041`, user-authored) ran 8 workers × 25s worker-budget, achieving
  528 iterations across 274s. Despite many more iterations than sequential X8
  (~226 iters in 300s), the final result was worse. Root cause: within each
  25s batch, the coordinator only sees the best result of each batch, not the
  improvement trajectory inside each worker. The best-global-so-far is not fed
  back to workers mid-batch, so workers diversify independently but cannot
  exploit each other's finds in real time. More iterations at lower quality per
  batch is not better than fewer deep sequential iterations.

- **PILSw4 (#56, discard, +222).** Reducing to 4 workers × 25s = 420 iters in
  275s, the best parallel result in this arc. Smaller batches mean the global
  best is updated more frequently (shorter feedback lag), which partially
  addresses the coordination gap. Still +222 vs X8. This is the closest parallel
  has come, and the directional trend (fewer workers = better) suggests the
  benefit of parallelism for this problem structure is negative at all tested
  worker counts.

- **PILSx8: NN-restart dedicated worker (#57, discard, +906).** Allocating
  worker 0 to fire an NN-restart every batch (mirroring X8's P4 mechanism)
  caused the slowest worker to block the entire batch from completing. Iteration
  count collapsed from 420 to 92. The sequential X8 mechanism (restart only
  after RESTART_AFTER idle iters) is fundamentally incompatible with the
  synchronous batch-wait coordination model; forcing it in costs 4.5× the
  iterations.

- **PILSx8r: rare NN-restart at no-improve=10 batches (#58, discard, +1,160).**
  Softening the restart condition — only inject if 10 consecutive batches showed
  no improvement — fired only once in the entire run. A single restart in 77
  batches is insufficient to replicate the benefit of X8's well-timed restart.
  The parallel scaffold's batch granularity (25s each) is too coarse to
  reproduce the sequential solver's restart timing at the iteration level. This
  closes the "port X8 mechanism to parallel" approach: it is architecturally
  mismatched.

- **PILSb15 (in-flight, b781574).** Shrinking worker budget 25s→15s targets
  ~17 batches × 8 workers = 136 restarts in ~255s — faster coordination
  turnover but shallower per-restart convergence. Direction is counter to the
  PILSw4 trend (fewer workers/shorter budget = higher quality per batch). If
  this is worse than PILSw4, it will confirm that deeper per-worker convergence
  is more valuable than restart diversity, and the parallel scaffold should be
  retired.

## Updated trial directions

1. **Retire parallel ILS scaffold.** All parallel variants (PILSw2, PILSw4,
   PILSw14, PILSx8, PILSx8r) are worse than sequential X8. The batch-
   coordination model loses within-batch best feedback that sequential ILS
   gets for free. Unless PILSb15 surprises, the parallel arc is closed.
   Return to sequential solver for remaining experiments.

2. **Z2e — penalty-aware 2-opt accept scoring.** Still the highest-EV untried
   mechanism. Track primes at k%10==0 positions during 2-opt; apply real
   penalty delta only at boundary moves. Zero per-iteration overhead when
   boundary check is O(1). The RngCafe result confirms structural improvements
   must beat the lucky seed; Z2e is the most likely candidate to do that by
   changing the move-acceptance landscape rather than just timing restarts.

3. **X11 — GLS-biased LNS destroy.** Bias LNS city selection toward cities
   incident to high-frequency (high-GLS-penalty) edges rather than only
   penalty-origin positions. Sidesteps Z5's failed accept-scoring approach;
   uses GLS history only in the destroy selector. Mechanistically fresh.

4. **X6 — Or-opt segment repair inside LNS-prime.** Group originally-adjacent
   removed cities as segments and apply O4r-style forward-vs-reversed insertion
   test during LNS repair. Targets the structural seam left by cheapest-insert.
   Distinct from X5 (which added prime-swap inside repair — failed row 33).

5. **X10 — prime_swap_pass per accepted ILS improvement.** At ~1ms per call
   and ~18 accept events per X8 run, total overhead is ~18ms — negligible vs
   300s. Post-pass Z1 is confirmed productive; per-accept application has not
   been tried cleanly (PrimePeriodic, row 51, ran every 50 iters and was too
   heavy — per-accept is 50× lighter-touch).

6. **L3-restart — wider k=10 candidate list for first post-restart VND only.**
   Better post-restart basin convergence to reduce dependence on restart-timing
   luck confirmed by RngCafe. Could narrow the gap between lucky and unlucky
   seeds structurally.

7. **X13 — path relinking between elite ILS solutions.** Maintain top-3 tours
   across restarts; generate intermediate tours by swapping edges from one
   elite toward another; accept the best 2-opt-converged intermediate.
   Diversification orthogonal to single-tour perturbations. Higher complexity
   but targets the basin-diversity gap.

## Ideas library

- ~62 items total (last grep confirmed, cycle-35 append was the most recent).
  Last appended: research-sourced additions from cycle-35 research tick
  (includes L10, X13, P6, X12, H7, O5, L8, L9 from classical/LKH veins).
- From new batch (rows 54-59): RngCafe was a diagnostic, not an idea; all
  parallel ILS variants (PILS-defaults, PILSw4, PILSx8, PILSx8r, PILSb15)
  are a single idea branch now exhausted.
- Confirmed exhausted veins: GLS-accept (Z5/Z5b/Z5d), restart-timing
  (AdaptiveRestart/ForcedLateRestart/P4t), regret-repair (Reg2/Reg2p),
  Or-opt bandwidth (OrL67/OrRev), parallel-ILS scaffold (5+ variants).
- Recommended next additions:
  - **Z2e-fast variant**: restrict penalty-aware scoring to pairs where one
    endpoint is within 2 positions of a k%10==0 boundary (reduces overhead
    further).
  - **D5+Z2e combo**: use position-index array (D5) to enable Z2e without
    positional scanning overhead — two ideas in one commit.
  - **X11-lite**: GLS-biased destroy with a small history window (e.g., last
    10 accepted improvements), avoiding global edge-frequency bookkeeping cost.

## State

- Branch: `main`; HEAD is `f8c3fc8` (revert of PILSx8r).
- `b781574` (PILSb15) is at HEAD-1 — still active in tree, not yet reverted.
- Last kept experiment commit: `8a1c432` (X8, val 1,547,351.05, row #34).
- In-flight: `b781574` (PILSb15) — result not yet in results.tsv.
- 59 logged rows in `results.tsv` (17 keeps, 42 discards).
- `ideas.md`: ~62 items.
- Submission: `submissions/submission.csv` at val 1,547,351.05.

Loop is in a 25-run discard streak (rows 35–59). Best val_cost has not moved
since row 34 (X8, `8a1c432`). Total improvement is −265,251.13 cost units
(−14.63%) from baseline. The parallel-ILS arc is conclusively worse than
sequential X8 at every worker count tested. The clearest remaining angles are
Z2e (penalty-aware 2-opt accept), X11 (GLS-biased LNS destroy), and X6
(segment-oriented LNS repair) — all mechanistically distinct from anything
in the current streak.
