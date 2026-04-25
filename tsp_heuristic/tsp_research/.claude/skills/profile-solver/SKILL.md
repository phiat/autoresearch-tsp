---
name: profile-solver
description: Profile solve.py with cProfile to surface hotspots. Use when an experiment ran inside budget but didn't move val_cost, or when wall-clock seems dominated by something unexpected. Returns the top time-consuming functions ranked by cumulative time.
---

# profile-solver

Profile the current `solve.py` to find where compute is going.

## When to use

- An experiment ran cleanly but val_cost barely moved → maybe the
  algorithm is starved by an unexpected hotspot (e.g. cKDTree
  rebuild, score_tour calls, python-level loops).
- Considering an engineering idea (D-class) and want data first.
- Sanity-checking that a numba-jit'd function is actually being
  called the way you expect.

## Procedure

1. Use a **truncated budget** so profiling itself doesn't take 5 min.
   Inject `TIME_BUDGET=30` via env override or a temporary edit; revert
   the edit immediately after profiling. (Note: `prepare.py` is
   off-limits — use an env var if `solve.py` reads one, else accept
   the full 5-min profile.)

2. Run with cProfile:

   ```bash
   uv run python -X dev -c "
   import cProfile, pstats, io
   import solve
   pr = cProfile.Profile()
   pr.enable()
   solve.main()
   pr.disable()
   s = io.StringIO()
   pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(25)
   print(s.getvalue())
   " > profile.log 2>&1
   ```

3. Read the top 25 entries. Surface the hotspots that aren't already
   numba-jit'd or cython.

4. Map hotspots to existing `ideas.md` items where possible
   (e.g. "score_tour shows 30% of time → D3 (numba-jit score) is now
   high EV"). If no existing idea fits, propose adding one via the
   normal growth protocol.

5. Delete `profile.log` when done — it's not part of the loop's
   tracked artifacts.

## Output

A short report (≤10 lines):
- Top 3 hotspots (function, % of cumulative time).
- The one idea (existing or new) most worth trying based on what you
  saw.
- One-line recommendation.

## Caveats

- cProfile under-counts numba-compiled functions (they appear as a
  single C call). For numba hotspots, instrument with `time.perf_counter()`
  around the call sites instead.
- The first run includes numba JIT compile time — discount any hot
  function that's only hit once.
