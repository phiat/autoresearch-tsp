# Idea Library

Pool of experiment ideas for the autonomous loop. The agent samples from
this list each cycle (random pick, weighted toward "untried" items), tries
the idea, records the result in `results.tsv`, and **every ~5 cycles
appends 2-3 new ideas to the bottom of this file** based on what it has
learned so far.

## Sampling protocol

1. Read this file.
2. Build the list of items not yet appearing in the description column of
   `results.tsv`. If empty, allow re-tries of the lowest-scoring previous
   ideas with a tweaked variant.
3. Pick uniformly at random from the untried set (or biased toward the
   item-class — local-move / candidate-list / perturbation / hyperparam —
   that's recently underrepresented).
4. Implement it as the next `solve.py` change. Keep the change minimal and
   focused on the picked idea — do not bundle.
5. Commit, run, log, keep/discard per the standard loop.

## Growth protocol

After every 5 logged experiments:

1. Re-read `results.tsv`. What worked? What didn't? What surprised?
2. Append **2 or 3** new ideas to the bottom of this file under
   `## Appended (cycle N)`. Each idea: one line, action-oriented.
   Examples of good additions: variants on what worked ("tighten k from
   10 to 7"), removals of what failed ("revert to plain 2-opt and trim
   the candidate-list overhead"), adjacent ideas the literature suggests
   ("try Or-3 in addition to Or-1/Or-2").
3. Do **not** delete or rewrite older entries — append-only.

---

## Seed ideas (cycle 0)

### Construction (initial tour)
- C1. Nearest-neighbor from a *random* starting city (current baseline starts at 0).
- C2. Greedy edge insertion: sort all edges by length, add shortest non-crossing ones.
- C3. Cheapest insertion: grow tour by inserting each city at its cheapest position.
- C4. Christofides-lite: MST + odd-degree matching shortcut (no perfect matching, use greedy).
- C5. Space-filling curve seed (Hilbert order through the bounding box).
- C6. Multi-start NN: build k tours from k random starts, keep the best.

### Local search — 2-opt family
- L1. Plain 2-opt with first-improvement, full O(N²) sweep until no improving move (likely too slow — try with budget guard).
- L2. 2-opt with cKDTree candidate lists (k=10 nearest), first-improvement.
- L3. 2-opt with cKDTree candidate lists (k=20), best-improvement within candidates.
- L4. 2-opt with don't-look bits.
- L5. Numba-jit'd 2-opt inner loop with k=10 candidate list.
- L6. Segment-reverse vs node-swap variants — measure which dominates per cycle.

### Local search — Or-opt family
- O1. Or-1 (relocate single city) with k=10 candidate list.
- O2. Or-2 (relocate consecutive pair).
- O3. Or-3 (relocate consecutive triple).
- O4. Mixed Or-1/Or-2/Or-3 sweep, in that order, until no improvement.

### Perturbation / escape
- P1. Random 4-opt double-bridge perturbation, then re-run 2-opt (basic ILS).
- P2. Segment-reverse a random window of size [N/50, N/20].
- P3. Segment-shift: cut a random window and re-insert at a random position.
- P4. Restart with C1 seed + best-so-far retained.

### Prime-aware tweaks (the Santa-specific bit)
- Z1. Post-pass: for each step at position k where k%10==0 and origin is
      non-prime, look for a swap that places a prime at that position
      without lengthening the tour beyond the saved 10% penalty.
- Z2. During 2-opt move evaluation, score with the real penalty function
      (not just euclidean delta) — slower per move but globally correct.
- Z3. Bias starting tour to put primes at positions 9, 19, 29, ... by
      reordering after construction.

### Data-structure / engineering
- D1. Pre-compute and cache cKDTree once outside the budget; reuse across
      restarts.
- D2. Linked-list tour representation (doubly-linked) for O(1) splice in
      Or-opt instead of array roll.
- D3. Numba-jit the score function to amortise penalty evaluation.
- D4. Cache squared distances for the active candidate list per node.

### Hyperparam knobs (sweep one at a time)
- H1. Candidate-list k ∈ {5, 7, 10, 15, 20, 30}.
- H2. Or-opt segment lengths set ∈ {{1}, {1,2}, {1,2,3}}.
- H3. Number of ILS restarts vs. depth per restart.
- H4. Double-bridge segment size as fraction of N.
- H5. Time fraction split: construction vs. improvement vs. polish.

### Combination / orchestration
- X1. Pipeline: NN → 2-opt(k=10) → Or-opt(1,2) → polish(Z1).
- X2. Pipeline: greedy-edge → 2-opt(k=20) → Or-opt(1,2,3).
- X3. ILS: X1 inner loop, double-bridge perturbation between, run until budget.
- X4. Best-of-N: run X1 from k=4 random NN seeds in parallel-via-loop, keep best.

## Appended (cycle 1)

Observations from logged runs so far: NN seed eats ~175s of the 300s budget
(huge), 2-opt converges in <1s with candidate lists, Or-1 dominates Or-2/Or-3
gains, ILS yields modest tail improvements.

- E1. **Fast NN via cKDTree candidate list**: at each step, walk candidates[cur]
      until finding an unvisited city (brute fallback). Should drop NN from
      ~175s to ~5s, freeing 170s for ILS.
- L7. **Don't-look bits for 2-opt + Or-opt**: skip cities whose neighborhood
      hasn't changed since last failed sweep. Makes near-converged sweeps O(1)
      per city. Frees budget for more ILS iterations.
- Z4. **Prime post-pass**: scan steps k where k%10==0 and origin non-prime;
      try cheap local swaps (single swap with a nearby prime, or position
      shift by 1) to flip origin to prime, accept if net cost drops.

## Appended (cycle 3)

Observations through row 16: P4 random-NN-restart-on-stuck is the most recent
big win (−455). The escape mechanism demonstrably finds new basins. Or-opt with
reversed-segment insertion (O4r) and L=4,5 extension both worked. Z1-integrated
in inner loop FAILED — taxing inner loop more than its gain. Pattern: cheap
escapes good, expensive inner-loop additions bad.

- P4t. **P4-tighten**: drop RESTART_AFTER from 40 → 20 idle iters. P4 proved
       the mechanism; a lower threshold should surface more basin escapes
       within budget.
- O4r45. **Or-opt L=4,5 reversed**: extend reversed-segment insertion (O4r,
       currently L=2,3) to L=4,5. Two independent wins (O4r and length extension)
       are obvious to combine.
- Z2e. **Z2-efficient**: penalty-aware 2-opt with modulo-10 position tracking.
       Track which moves cross a position k%10==0 boundary and apply the real
       penalty delta only there; pure-euclidean elsewhere. Cheap if scoped.
- LNS. **LNS cheapest-insert repair**: remove ~4% of cities at random, repair
       by cheapest-insertion. More structural than restart; targets the
       flat-ridge diagnosis by destroying tour structure rather than re-seeding.
