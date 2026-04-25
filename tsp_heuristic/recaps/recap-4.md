# Recap 4 — `heuristic/apr25` continued

Covers cycles #17–#26 (results.tsv rows 17-26 inclusive). Recap-3 closed
at row #16 / commit `035729e` with the P4 random-restart mechanism as the
headline win. Rows 17-21 resolved two quick discards and three consecutive
k-shrink wins (new best 1,547,900.81). Rows 22-25 were a 4-for-4 discard
streak. Row 26 (LNSt) broke the streak with a new best: **1,547,643.99**.

## Summary of recap-3

- Opened from best 1,549,603.33 (Or-opt L=4,5, row #12).
- Z1-integrated prime-swap (#13, +223, discard) — moving prime-swap into
  the inner loop halved ILS iteration count; mirrors the D5 lesson that
  inner-loop overhead is never free.
- L3 best-improvement 2-opt (#14, −627) combined with silent P5 base
  (adaptive perturbation escalation) — largest single gain this recap.
- P3 segment-shift alternated with double-bridge (#15, −25) — thin but
  real; diversifies escape topology.
- P4 random-NN-restart-on-stuck (#16, −455) — the most important new
  capability: after 40 idle ILS iters, re-seed from a random city via
  fast cKDTree NN. Run.log confirmed one restart at iter 84 then 10+
  consecutive new bests. Essentially free thanks to E1 (NN now 4s not 175s).
- **Best at end of recap-3: 1,548,496.21** (row #16, 035729e).
- 3 total reverts through row 16 (H1 k=20, D5 don't-look bits,
  Z1-integrated).

## New results

| # | commit | val_cost | Δ best | status | description |
|---|---|---|---|---|---|
| 17 | 2c1003c | 1,548,884.28 | +388 | **discard** | P4t: RESTART_AFTER=20 — too-frequent restarts dilute local-search depth |
| 18 | 7462c07 | 1,550,420.63 | +1,924 | **discard** | Z3: prime-aligned NN — warps geometry, ILS recovers most but net regression |
| 19 | 29d0256 | 1,548,122.80 | −373 | keep | H1k7: K_NEIGHBORS=7 — faster sweeps, +20 ILS iters, net win |
| 20 | c076566 | 1,548,025.66 | −97 | keep | H1k5: K_NEIGHBORS=5 — deeper local optima despite fewer ILS iters |
| 21 | 5393897 | 1,547,900.81 | −125 | keep | H1k4: K_NEIGHBORS=4 — third k-knob win in a row |
| 22 | 2dca1a9 | 1,566,880.06 | +18,979 | **discard** | C5: Hilbert SFC seed — inferior basin, huge regression |
| 23 | 453cc41 | 1,555,021.50 | +7,121 | **discard** | H1k3: K_NEIGHBORS=3 — candidates too thin, +7,121 vs k=4 despite 275 ILS iters |
| 24 | d14eb87 | 1,547,900.81 | 0 | **discard** | H3: RESTART_AFTER 40→60 — no behavioral diff under seed 0xBEEF, Δ=0 |
| 25 | 2d19134 | 1,548,584.33 | +683 | **discard** | LNS: 4% destroy + cheapest-insert repair as 3rd ILS arm — +683 (repair too aggressive) |
| 26 | b2b92e2 | **1,547,643.99** | −257 | keep | LNSt: LNS destroy 1.5% + cheapest-insert — 2 restarts, 11 improvements, NEW BEST |

**Best: 1,547,643.99** (LNSt, commit `b2b92e2`) — −14.61% from baseline (dd8df32, 1,812,602.19).
9 total discards in the run overall. Rows 22-25 were a 4-for-4 discard streak, broken by row 26.

## What worked / didn't

- **P4t tighter restart threshold (#17, discard, +388).** Dropping
  RESTART_AFTER from 40 to 20 idle iters caused 5 restarts within budget
  vs. 0 in the H1k4 run. Each restart discards accumulated local-search
  depth; when restarts fire too often, the algorithm spends most of its
  budget on shallow post-restart local search rather than deep ILS iteration.
  Lesson: the restart mechanism is most valuable as a single escape from a
  deep rut, not as a periodic diversification pulse.

- **Z3 prime-aligned NN construction (#18, discard, +1,924).** Reordering
  the NN tour to place primes at positions 9, 19, 29 ... warps tour geometry.
  ILS recovers most of the cost within 300s, but cannot fully repair a biased
  starting structure. Z-class construction-phase experiments are effectively
  closed; Z2 (penalty-aware move scoring) remains the only open Z with
  positive EV.

- **H1k7/k5/k4 k-shrink vein (#19-21, all keep, −373/−97/−125).** Three
  consecutive wins from shrinking the candidate list. Smaller k means faster
  sweeps and more ILS iterations per budget. The empirical optimum is k=4
  for the current ILS architecture.

- **C5 Hilbert SFC seed (#22, discard, +18,979).** Largest absolute regression
  in the entire run. The Hilbert tour lands in a qualitatively different basin
  that 300s of ILS cannot recover. Confirms NN seed lands in a favorable region.

- **H1k3 (#23, discard, +7,121).** k=3 is too thin. The candidate list misses
  too many improving moves; 275 ILS iters at k=3 cannot compensate for the
  weaker per-iter move quality. k=4 is confirmed as the empirical floor.

- **H3 RESTART_AFTER 40→60 (#24, discard, Δ=0).** The no_improve counter never
  reached 40 under seed 0xBEEF in 300s, so the threshold change was a no-op.
  Confirms P4 restart is a rare-event mechanism; the current basin rarely
  triggers it at the original 40-iter threshold.

- **LNS 4% destroy-repair (#25, discard, +683).** The 4% destroy fraction is
  too large: cheapest-insertion repair of 4% of N≈200k cities (≈8k removed)
  creates long edges that local search cannot fully remove within budget.
  The mechanism itself is sound but the perturbation size was wrong.

- **LNSt 1.5% destroy-repair (#26, keep, −257).** Tightening the destroy
  fraction from 4% to 1.5% (≈3k cities) kept the perturbation structural but
  tractable for the repair step. Result: 2 restarts fired, 11 improvements
  found, new best 1,547,643.99. The smaller perturbation keeps tour structure
  mostly intact, so cheapest-insert repair lands closer to a good local
  optimum. This is a win-by-calibration: the mechanism was correct in LNS,
  the fraction just needed halving. Further LNS tuning (1%, 2% fractions) is
  now the highest-value next probe.

## Updated trial directions

1. **LNS fraction sweep (1%, 2%)**: LNSt at 1.5% just won by −257. Probing
   1% and 2% brackets whether 1.5% is optimal or whether finer destroy gives
   even better repair quality. Cheapest experiment class currently available.

2. **Z2e — penalty-aware 2-opt with modulo-10 boundary tracking**: Still the
   only remaining Z-class idea with positive EV. Track which moves cross a
   position k%10==0 boundary and apply the real penalty delta only there;
   pure-euclidean elsewhere. The H1k4/LNSt inner loop is cheap (k=4); limited
   overhead headroom remains but Z2e is designed to be fast.

3. **C6 multi-start NN (X4 variant)**: k-shrink vein exhausted at k=4, H3 a
   no-op — new basin diversity requires better construction. Run 10-20 NN
   starts (each ~5s at E1 speed), keep the best initial tour, then full ILS.
   Trades ~80-100s of construction for a better starting basin.

4. **Or-opt L=4,5 reversed (O4r45):** Both O4r (reversed insertion, L=2,3) and
   the L=4,5 extension were independent keeps. Combining them is a low-risk
   compound experiment with no new mechanisms.

5. **Adaptive k — reduce k dynamically as tour matures**: Start at k=7 for
   early ILS phases, reduce to k=4 once improvements per iter fall below a
   threshold. Attempts to combine early-phase breadth with late-phase speed.

6. **D5-Or-opt only (scoped don't-look bits):** D5 full bits hurt; a version
   restricted to Or-opt (not 2-opt) has not been tested and may recover
   throughput without degrading 2-opt quality.

## Ideas library

- 37 items total: 30 seed + 3 cycle-1 appended (E1, L7, Z4) + 4 cycle-3
  appended (P4t, O4r45, Z2e, LNS).
- Cycle-3 growth tick fired at `008746e`. Next tick due at cycle 25 —
  threshold now passed (row 26 logged); growth append is overdue.
- Recommended next additions (cycle-4 append):
  - **LNS-frac**: systematic destroy-fraction variants (1%, 2%) to bracket
    the optimal LNS regime around the 1.5% winner.
  - **C6-multistart**: run N NN constructions before ILS, keep the best;
    N calibrated to consume ~25% of the 300s budget.
  - **Z2e**: penalty-aware 2-opt move scoring with cheap modulo-10 filter.

## State

- Branch: `main` (both loops commit to main; heuristic loop at head `b2b92e2`).
- Last kept experiment commit: `b2b92e2` (LNSt, val 1,547,643.99).
- In-flight: none. results.tsv is current through row 26.
- 26 logged rows in `results.tsv` (17 keeps, 9 discards).
- `ideas.md`: 37 items; cycle-4 growth tick is now overdue.
- Submissions file: `submissions/submission.csv` at val 1,547,643.99
  (updated to LNSt result).

Loop is healthy. Total improvement −264,958.20 cost units from baseline across
26 cycles. The 4-for-4 discard streak (rows 22-25) ended with LNSt winning by
−257, showing that LNS destroy-repair is viable at the right fraction. Best
alive seams: LNS fraction sweep (immediate), Z2e (penalty-aware scoring,
untried), C6 multi-start construction (basin diversity). Inner-loop overhead
remains the binding constraint.
