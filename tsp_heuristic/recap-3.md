# Recap 3 — `heuristic/apr25` continued

Covers cycles #13–#16 (results.tsv rows 13-16 inclusive). Recap-2 had
row #13 in-flight; this recap resolves it and adds three more completed
experiments. The loop now stands at 16 logged rows and a new overall
best of **1,548,496.21**.

## Summary of recap-2

- Started from best 1,553,408.50 (Z1 prime post-pass, row #7).
- Or-opt with reversed-segment insertion (O4r, row #9) was the
  standout: −3,590, unlocking segment orientations plain Or-opt cannot
  reach.
- Tail-search (#10, −115) and L=4,5 segments (#12, −101) extended the
  Or-opt vein with diminishing but real returns.
- Two reverts: H1 (k=20 candidates hurt, not helped) and D5 (don't-look
  bits got more ILS iters but worse local optima).
- **Best at end of recap-2: 1,549,603.33** (row #12, ee01598).
- Row #13 (Z1-integrated prime-swap in the inner loop) was in-flight.

## New results

| # | commit | val_cost | Δ best | status | description |
|---|---|---|---|---|---|
| 13 | 823017c | 1,549,826.01 | +223 | **discard** | Z1-integrated: prime-swap in inner loop — halves ILS iters |
| 14 | f1b0070 | 1,548,976.80 | −627 | keep | L3: best-improvement 2-opt k=10 (built on P5 base) |
| 15 | 525350c | 1,548,951.38 | −25 | keep | P3: alternate double-bridge / segment-shift perturbation |
| 16 | 035729e | **1,548,496.21** | −455 | keep | P4: random NN restart from random city after 40 idle ILS iters |

Note on row #14: commit `537f43e` (P5: adaptive perturbation escalation
after 30 idle iters) appears in the git log between rows #13 and #14 but
was not separately logged in results.tsv. It was kept as a silent base
layer; row #14's val_cost reflects the combined L3+P5 state.

**Best: 1,548,496.21** — −14.57% from baseline (dd8df32 at 1,812,602.19).
**3 total reverts** (H1, D5, Z1-integrated). All three new keeps produced
improvements. The run.log for row #16 shows the restart mechanism firing
at ILS iter 84, followed by 10+ new bests over the next 70+ ILS iters —
strong evidence that restart-on-stuck is unlocking new basins.

## What worked / didn't

- **Z1-integrated prime-swap (#13, discard).** Putting prime-swap inside
  the local-search inner loop halved ILS iteration count and produced a
  net regression (+223). Mirrors the D5 finding: any move taxing the
  inner loop more than its gain pays for itself in fewer escape
  perturbations. In-loop Z variants are closed; Z2 (penalty-aware 2-opt
  gain formula) remains open but must be implemented efficiently.

- **L3 best-improvement 2-opt (#14, keep, −627).** Switching 2-opt from
  first-improvement to best-improvement within the k=10 candidate list
  finds deeper local optima per sweep. The gain also incorporates P5
  (adaptive perturbation escalation after 30 idle iters), which was
  folded in as a base layer. First new-2-opt-variant win in several
  cycles.

- **P3 segment-shift perturbation (#15, keep, −25).** Alternating
  double-bridge with a random segment-shift (cut + re-insert at random
  position) added a thin but real gain. The two perturbation types
  explore different tour topologies; the combination keeps ILS from
  over-specialising on double-bridge escape paths.

- **P4 random NN restart on stuck (#16, keep, −455).** After 40 idle ILS
  iters, re-seed the tour from a random city via the fast cKDTree NN and
  restart local search from scratch. The run.log is the clearest evidence
  yet: one restart at iter 84, then 10+ consecutive new bests through iter
  161. Key enabler: E1's fast NN (4s, not 175s) makes restarts essentially
  free. The escape works because a different NN starting city produces a
  tour in a different basin; the accumulated local-search stack then finds
  a lower minimum within that basin.

## Updated trial directions

1. **P4 extension — lower idle threshold or unconditional multi-restart**:
   P4 proved the mechanism; the threshold of 40 idle iters is arbitrary.
   Trying 20 iters or restarting unconditionally every 40 iters (not just
   once) could surface even more basin escapes within the 300s budget.

2. **Z2 — penalty-aware 2-opt gain formula**: Still the highest-EV
   untried prime-aware move. The #13 failure narrows the design: the
   penalty delta per move must be evaluated locally (track modulo-10
   positions per edge pair, not full rescore). Cheap if implemented
   correctly.

3. **Or-opt L=4,5 reversed (O4r × extended lengths cross)**: Both O4r
   and the length extension produced independent wins. Combining reversed
   insertion at L=4,5 is an obvious compound experiment with low
   implementation risk.

4. **LNS destroy-and-repair**: Remove k%=3-5% of cities, cheapest-insert
   repair. More systematic than restart; targets the flat-ridge diagnosis
   by destroying structure rather than just re-seeding. Pairs well with
   the prime structure (prime positions can bias which cities are removed
   or re-inserted first).

5. **Z3 prime-aligned construction**: Bias the initial NN tour to put
   primes at positions 9, 19, 29… Untried and structurally sound. More
   useful now that P4 makes multiple construction seeds cheap.

6. **H1 retry k=5 or k=7**: k=20 regressed (#8). The smaller-k direction
   is still open and fast to test.

7. **Scoped don't-look bits (Or-opt only)**: D5's full don't-look bits
   hurt. A narrower version restricted to Or-opt (not 2-opt) has not been
   tested and may recover throughput without degrading 2-opt quality.

## Ideas library

- 33 items (30 seed + cycle-1 append of 3: E1, L7, Z4).
- **No cycle-2 or cycle-3 growth tick has fired.** The agent has been
  chaining perturbation and local-search experiments without returning to
  the grow step. The "every 5 cycles" rule should have triggered at cycle
  10 and again at cycle 15 — both missed.
- Recommended next additions (to be appended as cycle-2 + cycle-3):
  - **P4-extended**: lower idle threshold to 20 iters or restart
    unconditionally every 40 iters.
  - **Or-opt L=4,5 reversed**: direct O4r × length cross.
  - **Z2-efficient**: penalty-aware 2-opt with modulo-10 position
    tracking for cheap per-move delta evaluation.
  - **LNS cheapest-insert repair**: k%=4 removal + greedy re-insertion.

## State

- Branch: `heuristic/apr25` @ `10e5fcd` (merge commit on top of `035729e`).
- Last kept experiment commit: `035729e` (P4 random NN restart,
  val 1,548,496.21).
- 16 logged rows in `results.tsv` (13 keeps, 3 discards).
- `ideas.md`: 33 items; cycle-2 and cycle-3 growth ticks both overdue.
- `run.log`: shows the completed P4 run; no in-flight experiment.

Loop is healthy. Total improvement **−264,105.97** cost units from baseline
across 16 cycles. Perturbation class (P3+P4) is now the most recent source
of gains, supplanting Or-opt. The random-restart mechanism (P4) is the
most important new capability added this recap — it demonstrably escapes
local optima and should be the foundation of the next round of experiments.
Next recap will be `recap-4.md`.
