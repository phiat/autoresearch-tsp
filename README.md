# autoresearch-tsp

Two autonomous LLM research loops attacking the same problem — the
[Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/overview)
TSP (197,769 cities, with a 1.1× penalty on every 10th step from a
non-prime origin). Same metric (`val_cost`), same 5-min wall-clock
budget per cycle, same keep-or-revert mechanic. Different *levers*
the agent can pull.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
and the [marimo walkthrough video](https://www.youtube.com/watch?v=bMoNOb0iXpA).

## The two projects

|                  | [`tsp_heuristic/`](tsp_heuristic/)        | [`tsp_neural/`](tsp_neural/)                  |
|------------------|------------------------------------------|------------------------------------------------|
| **Approach**     | classical heuristic search               | neural-guided local search                     |
| **Lever**        | algorithm design                         | model design + integration                     |
| **Trains a model?** | **no** — pure numpy/numba/scipy       | **yes** — small PyTorch model per cycle        |
| **What's optimised** | a permutation of 197,769 ints (the tour) | a tour, *plus* the move-scorer that helps build it |
| **Deps**         | numpy, pandas, sympy, scipy, numba       | + `torch`                                      |
| **Pipeline today** | NN seed → 2-opt → Or-opt → ILS → prime polish | NN seed → 2-opt (baseline; agent adds learning from cycle 1) |
| **Risk**         | low; classical literature is deep        | high; learned/classical glue is fiddly         |

Both share `prepare.py` (the metric is bit-identical) and the same
harness shape: agent edits one file (`solve.py`), runs under a
fixed 5-min budget, scores against `val_cost`, keeps or reverts,
appends to `results.tsv`, repeats.

Each subdir is self-contained. See its `README.md` for setup, its
`AGENTS.md` for the tooling inventory, and its `program.md` for the
loop's operating rules.

## Layout

```
tsp_heuristic/    classical loop (matured pipeline; current best ~1.548M)
tsp_neural/       neural-guided loop (scaffolded; first cycle TBD)
autoresearch/     vendored upstream (karpathy's repo, reference only)
AGENTS.md         agent guidance for the outer repo
```

## Running both loops in parallel

Both loops commit to **`main`** from the same working tree. File-level
isolation comes from the separate subdirs (`tsp_heuristic/solve.py` vs
`tsp_neural/solve.py`); neither loop touches the other's. The
`revert` recipe in each `justfile` uses `git revert HEAD --no-edit`
(not `git reset --hard`) so a discard from one loop never wipes the
other's commits.

```bash
# tsp_heuristic — first Claude Code session
cd /home/phiat/lab/apr/auto-rez/tsp_heuristic
uv sync && just data && just run        # smoke test
# point a Claude Code session here, follow program.md

# tsp_neural — second Claude Code session
cd /home/phiat/lab/apr/auto-rez/tsp_neural
uv sync && just data && just run        # smoke test (downloads PyTorch first time)
# point a *separate* Claude Code session here, follow its program.md
```

Two sessions, two subdirs, one branch (`main`), one working tree.
Their commits will interleave in `git log`. Use `compare-runs` across
the two paradigms once both have rows in their respective
`results.tsv` (per-subdir, gitignored).

## Status

- **`tsp_heuristic/`** — pipeline matured to: fast cKDTree-walked NN
  seed → 2-opt + Or-opt(1,2,3) local search with k-NN candidate lists
  → ILS with adaptive double-bridge / segment-shift perturbation →
  prime-aware swap polish. Current best `val_cost` ≈ **1,548K** (~14.6%
  off the identity-tour baseline). Recap series in
  `tsp_heuristic/recap-*.md`.
- **`tsp_neural/`** — scaffolded; agent's first 3 cycles must
  introduce learning per `tsp_neural/program.md` (harvest moves →
  train small scorer → integrate into 2-opt).

For reference, top public-leaderboard scores for Santa 2018 were in
the 1.514M range.

## Provenance

- **Inspiration & template**: [karpathy/autoresearch](https://github.com/karpathy/autoresearch).
- **Task**: [Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/).
- **Inspired by this video**: [marimo: autoresearch on the Santa 2018 TSP](https://www.youtube.com/watch?v=bMoNOb0iXpA).

## License

MIT.
