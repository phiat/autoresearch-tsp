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

## Appended (permute: cross-class with LNS-prime backbone)

6 X-class combinations of validated keeps. Most leverage the recent LNS-prime
direction (3 keeps in a row) by composing it with earlier kept ideas (Or-opt
L=4,5 reversed, Z1 prime-swap, P4 NN restart, H1 k-shrink). X1-X4 are seeded
in the construction/orchestration section above.

- X5. **prime-swap polish inside LNS-prime repair**: after each LNS-prime
       reinsertion batch, invoke prime_swap_pass once before returning the
       perturbed tour. Captures the transient prime-position misalignments
       reinsertion creates before ILS local search erases the context.
       Combines Z1 (kept post-pass) with LNS-prime (current best path).
- X6. **Or-opt-segment repair inside LNS-prime**: when reinserting, group
       2–3 originally-adjacent removed cities into a segment and apply
       O4r-style forward-vs-reversed insertion test rather than per-city
       cheapest-insert. Combines O4r (reversed-segment, +ve) with LNS-prime
       (kept) to retain locally-coherent structure during repair.
- X7. **Local Or-opt sweep around just-reinserted regions**: after each
       LNS reinsertion batch, run a short Or-opt(L=4,5) sweep restricted
       to the cities just reinserted and their immediate neighbours.
       Or-opt L=4,5 extension was a kept win; applying it locally targets
       the rough seam cheapest-insert leaves.
- X8. **P4 restart followed by LNS-prime smoothing**: when no_improve >=
       RESTART_AFTER, do the existing NN-from-random-city, then immediately
       run one LNS-prime perturbation on the fresh tour before ILS local
       search resumes. NN basin is far from current best; LNS-prime would
       prime-align it before committing compute. Combines P4 + LNS-prime.
- X9. **k=7 candidates for 2-opt, k=4 for LNS repair**: split candidate
       widths by operator. 2-opt was breadth-limited at k=10 (H1k7 kept);
       LNS repair benefits from tight local insertion (current k=4). Tests
       whether candidate-width is operator-specific. Combines H1k7 + H1k4.
- X10. **prime_swap_pass after each accepted ILS improvement**: invoke Z1 at
       higher cadence — once per ILS accept rather than once at end. Cheap
       (~1ms per call) and targets boundary moves while their geometric
       context is still hot. Pure-Z1 escalation, not strictly cross-class
       but a cadence permutation that combines Z1 + ILS rhythm.

## Appended (research: domain-specific — Santa 2018 writeups)

Sources: general TSP/ILS/LNS/GLS literature (Voudouris & Tsang 1999 GLS;
Helsgaun LKH k-opt papers; Blazinskas k-swap-kick 2011; backbone-TSP
Springer 2014; LKH relaxed-gain-criterion arXiv:2401.16149).
No Santa-specific writeups consulted per user instruction.

- Z5. **GLS edge-penalty augmented scoring**: maintain a per-edge penalty
      array (float32, shape N, initialized 0) incremented at each local-optima
      convergence for edges with max utility = dist/(1+penalty); run 2-opt with
      augmented cost h = euclidean + lambda*penalty instead of raw euclidean.
      GLS (Voudouris & Tsang 1999) systematically depenalizes the solution
      landscape so the same local minimum is never revisited — directly
      addresses the plateau stagnation pattern without any structural overhead.

- P5. **k-swap-kick compound perturbation**: apply k=2 sequential random
      double-bridge kicks (each cutting 4 random edges) in a single perturbation
      step, yielding an 8-opt non-sequential move; accept the compound-kicked
      tour as the new ILS start. Blazinskas (2011) shows k=2 stacked kicks
      escape deeper local-optima funnels than a single double-bridge while
      remaining cheaper than 3x. Gives the ILS arm a stronger kick option when
      single double-bridge has been exhausted for 20+ idle iters.

- D5. **Position-index array for O(1) boundary detection in 2-opt**: maintain a
      companion pos[] array (pos[city] = index in tour) alongside the tour array,
      updated in O(segment) after each 2-opt reversal; use it during 2-opt
      candidate evaluation to test in O(1) whether either endpoint sits within 2
      steps of a k%10==0 boundary and apply real penalty delta only there. Enables
      Z2e at true O(1) per candidate pair rather than a per-move modulo scan,
      removing the overhead that blocked Z2e previously.

- X11. **GLS-penalty-biased LNS destroy**: at each LNS destroy step, bias city
       selection toward cities incident to high-penalty edges (edges with
       penalty > median penalty) rather than only toward penalty-origin positions;
       this couples the GLS edge memory with the LNS-prime destroy mechanism so
       that repeatedly-bad structural edges are targeted even when they don't fall
       on a k%10==0 boundary. Merges two proven penalty-aware signals (LNS-prime
       and GLS-style edge history) without inner-loop overhead.

- H6. **Adaptive perturbation arm weights via success-ratio bandit**: replace the
      fixed 1/3-each arm probability among double-bridge / segment-shift /
      LNS-prime with a running success-ratio softmax updated after each accepted
      ILS improvement — arm weight proportional to improvements_this_arm /
      calls_this_arm, temperature tau=0.5. Online bandit arm selection
      (ALNS/Balans literature) costs ~0 compute and automatically routes budget
      toward whichever perturbation arm is currently productive as the tour
      geometry changes across a 300s run.

## Appended (research: classical — LKH/3-opt/sequential-edge-exchange)

Sources: Helsgaun (2009) "General k-opt submoves for the LK TSP heuristic"
(Mathematical Programming Computation, PDF at seas.gwu.edu); arXiv:2401.16149
(Ammann et al., relaxing the positive gain criterion, 13% speed-up on large
instances); arXiv:2501.04072 (Wang et al., backbone-frequency + MAB for LKH,
Jan 2025); tsp-basics.blogspot.com 3-opt move anatomy; cfld/simple_tsp
(Python+Numba LK-style implementation, <500 lines); Voudouris GLS citeseerx
doc (lambda schedule and edge-utility formula).

- L8. **Sequential LK-chain (depth-2) in numba**: implement a single-source
      LK-chain in a @njit function: pick t1=city, remove edge (t1,t2), for
      each candidate t3 (from K=4 list, gain1 = dist(t1,t2)-dist(t2,t3) > 0),
      try closing (t3->t1 gain_close) first; if gain_close > 0 apply 2-opt
      move immediately (this recovers standard 2-opt); else extend to t4 via
      tour-successor and test a 3-opt close: gain_total = gain1 +
      dist(t3,t4) - dist(t4,t1); apply if > 0. Strictly sequential, no
      backtracking beyond depth 2, uses the same pos[] array (D5) for O(1)
      segment direction test. Helsgaun 2009 shows this depth-2 sequential
      kernel is the dominant productive case; cfld/simple_tsp implements it
      in <150 lines of numba without linked lists. Breaks the plateau by
      finding improving 3-edge exchanges invisible to 2-opt.

- L9. **Relaxed gain criterion at depth 2 (allow one negative intermediate
      step)**: in the L8 chain, after computing gain1 = dist(t1,t2)-dist(t2,t3),
      allow gain1 to be slightly negative (threshold: gain1 > -0.01*dist(t1,t2))
      before testing the depth-2 close; only require gain_total > 0 for
      acceptance. arXiv:2401.16149 (Ammann et al.) proves this single relaxation
      discovers improving alternating cycles that strict positive-gain misses,
      and delivers 13% more improving moves on DIMACS large instances at
      negligible overhead (one extra branch per candidate pair). Gate the
      relaxation behind a flag so L8 baseline is not disturbed.

- O5. **3-opt segment-exchange (type-4 reconnection only) with K=4 candidate
      list**: iterate outer city i; for each candidate j in candidates[i] with
      dist(i,j) < dist(i, tour[i-1]) (pruning); pick k = tour[j+1]; evaluate
      only the "double-segment-swap" reconnection (swap segment [i..j] and
      [j+1..k] leaving third segment in place) — this is the Or-opt-3 parent
      and the only non-sequential 3-opt type that avoids a segment reversal,
      making the array update a pure segment-move (O(1) with index arithmetic).
      Gain = dist(prev_i,i)+dist(j,j+1)+dist(k,next_k) -
             dist(prev_i,j+1)+dist(k,i)+dist(j,next_k). tsp-basics.blogspot
      3-opt anatomy (case 3) confirms this is the cheapest non-trivial reconnect
      to implement on a flat array; it subsumes Or-opt-L for L up to segment
      length and finds moves Or-opt misses because it relocates both flanking
      segments simultaneously.

- X12. **Backbone-frequency edge bias for LNS destroy**: after every 10 accepted
       ILS improvements, update a uint16 frequency array freq[city] += 1 for
       every city whose two tour-edges both appear in the current best tour
       (i.e., edges shared between current and best-so-far — the "backbone");
       during LNS destroy, sample removal probability proportional to
       (1 - freq[city]/max_freq) so low-backbone cities are preferentially
       destroyed. arXiv:2501.04072 (Wang et al. 2025) shows backbone frequency
       combined with LKH candidate lists lifts solution quality on 100k-city
       instances; here it plugs directly into the existing LNS-prime destroy
       loop via a single numpy weighting call, no new data structures.

- H7. **GLS lambda schedule: warm-start at lambda = 0.1*avg_edge_len, decay
      by 0.95 per no-improve cycle**: initialize lambda proportional to the
      mean candidate-edge length (avg of K=4 distances per city) rather than
      a fixed scalar; after each ILS improvement reset to initial value; after
      each failed sweep multiply by 0.95 down to floor lambda_min = 0.01*avg.
      Voudouris & Tsang (1999) specify lambda = alpha * C* where C* is the
      known optimal cost — for unknown C* the best practical proxy is the
      mean edge cost in the current tour; the decay schedule prevents penalty
      domination late in the run while the warm-start prevents under-penalization
      early. Pairs with Z5 (GLS penalty array, already in pool) and replaces
      the naive lambda=1.0 that Z5 currently assumes.

## Appended (research: classical/hybrid — manual injection, plateau break)

User-requested research injection at heuristic cycle ~47 (val_cost
plateau at 1,547,351). Sources: general TSP/local-search/metaheuristic
literature (no Santa-specific writeups consulted).

- L10. **Sequential 3-opt LK chain (depth-3) with α-nearness candidates**:
  extend L8's depth-2 chain to depth-3, using α-nearness from a
  Held-Karp 1-tree relaxation instead of geographic k-NN to pick the
  intermediate edges. Lin-Kernighan's original goes to depth-5;
  depth-3 captures most of the gain at tractable cost. Targets the
  basin floor 2-opt + Or-opt cannot reach.
  [src: Lin & Kernighan 1973; Helsgaun LKH-3, doi.org/10.4230/LIPIcs.SEA.2017]

- X13. **Path relinking between elite ILS local optima**:
  maintain a small "elite set" (top-3 kept tours by val_cost across
  ILS restarts). Between restarts, instead of (or alongside) the
  current double-bridge perturbation, pick two elite tours and
  generate intermediate tours by swapping edges from one toward the
  other in steps; accept the best 2-opt-converged intermediate as
  the new ILS start. Diversification axis orthogonal to single-tour
  perturbations — explicitly recombines high-quality solutions.
  [src: Glover 1997 scatter search; Resende & Werneck 2004 path-relinking
  TSP; Marti, Resende, Ribeiro 2010 Eur J Oper Res]

- P6. **Iterated tabu search**: replace pure ILS with a tabu-list
  on recent edges (length ~7). After each accepted improvement,
  forbid the *removed* edges from being re-added for the next K
  moves; this prevents thrashing in degenerate local-optima
  neighborhoods and forces structurally different next moves.
  Lighter-weight than path relinking; complementary to existing
  perturbations.
  [src: Misevicius 2005, Inf Sci "Iterated tabu search for the TSP";
  Glover 1989 Tabu Search Part I]
