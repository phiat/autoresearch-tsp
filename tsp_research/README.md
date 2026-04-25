# tsp_research

Autoresearch-style harness for the [Kaggle Traveling Santa 2018 Prime Paths](https://www.kaggle.com/competitions/traveling-santa-2018-prime-paths/overview) challenge.

Same philosophy as [karpathy/autoresearch](https://github.com/karpathy/autoresearch):
fixed time budget, the agent edits a single file, one scalar metric, autonomous
loop. Different domain — combinatorial optimisation instead of LLM training.

## Files

```
prepare.py      — frozen: data loader, prime sieve, score_tour() metric
solve.py        — agent's playground; baseline = nearest-neighbor
program.md      — agent instructions
pyproject.toml  — minimal deps (numpy, pandas, sympy)
data/           — Kaggle CSVs (gitignored)
submissions/    — solver output (gitignored)
results.tsv     — local experiment ledger (gitignored)
```

## Quick start

```bash
# 1. Make sure data/cities.csv exists (unzip the Kaggle archive into ./data/)
# 2. Set up the venv
uv sync

# 3. Smoke test the harness (loads data, scores identity tour)
uv run prepare.py

# 4. Run the baseline solver (~5 min wall clock)
uv run solve.py
```

## Metric

`score_tour(tour)` returns the official Santa cost: euclidean tour length with
a 1.1× multiplier on every 10th step whose **origin** city is not prime.

Validation is strict — the tour must be a permutation of all CityIds, starting
and ending at City 0.
