"""
Generate progress.png at repo root showing % SOTA over experiment index
for both tsp_heuristic and tsp_neural loops, with the SOTA reference at 100%.

% SOTA = 100 - gap, where gap = (val_cost - SOTA) / SOTA * 100. Higher is
better. Best-so-far line uses cummax over KEPT rows only (discards don't
update the running best).

Usage (from repo root or any subdir):
    uv run --with matplotlib --with pandas python scripts/chart_progress.py

Reads:
  tsp_heuristic/results.tsv
  tsp_neural/results.tsv

Writes:
  progress.png  (overwritten in place; re-run to refresh)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SOTA = 1_514_000
OUTPUT = REPO_ROOT / "progress.png"

LOOPS = [
    ("tsp_heuristic", REPO_ROOT / "tsp_heuristic" / "results.tsv", "#1f77b4"),
    ("tsp_neural",    REPO_ROOT / "tsp_neural"    / "results.tsv", "#ff7f0e"),
]


def load_loop(name: str, path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, sep="\t")
    except Exception as e:
        print(f"warn: failed to read {path}: {e}")
        return None
    if "val_cost" not in df.columns or len(df) == 0:
        return None
    df = df.copy()
    df["cycle"] = range(1, len(df) + 1)

    # Convert to % SOTA. Treat 0 (crash sentinel) as NaN.
    val = df["val_cost"].replace(0, pd.NA).astype("Float64")
    df["sota_pct"] = 100.0 - (val - SOTA) / SOTA * 100.0

    # Best-so-far line: cummax of % SOTA, but ONLY keep-status rows can update
    # the running best (discards don't survive — they shouldn't pull the line up).
    mask_keep = df["status"].astype(str).str.lower() == "keep"
    df["sota_for_best"] = df["sota_pct"].where(mask_keep)
    df["best_pct"] = df["sota_for_best"].cummax().ffill()
    return df


def main() -> None:
    fig, ax = plt.subplots(figsize=(9, 5), dpi=120)

    summary_lines: list[str] = []
    all_pcts: list[float] = []

    for name, path, color in LOOPS:
        df = load_loop(name, path)
        if df is None:
            print(f"skip: {name} (no data at {path})")
            continue

        # Best-so-far line — only plot where best is finite.
        mask = df["best_pct"].notna()
        ax.plot(
            df.loc[mask, "cycle"],
            df.loc[mask, "best_pct"],
            marker="o",
            markersize=3,
            linestyle="-",
            linewidth=1.6,
            color=color,
            label=f"{name}/  (best so far)",
        )

        # Overlay each kept run faintly for context.
        keeps = df[(df["status"].astype(str).str.lower() == "keep")
                   & (df["sota_pct"].notna())]
        if len(keeps):
            ax.scatter(
                keeps["cycle"],
                keeps["sota_pct"].astype(float),
                marker=".",
                s=12,
                color=color,
                alpha=0.35,
            )

        best_pct = float(df["sota_for_best"].max())
        all_pcts.append(best_pct)
        # Find the val_cost of the best-kept row for the summary line.
        best_val = float(df.loc[df["sota_for_best"].idxmax(), "val_cost"])

        # Δ12: % SOTA change over the last 12 experiments (cumulative best
        # at cycle N minus cumulative best at cycle N-12). Positive =
        # improving. Reported as percentage points (pp) of SOTA.
        WINDOW = 12
        n_rows = len(df)
        if n_rows >= WINDOW + 1:
            past_best_pct_series = df["best_pct"].iloc[: n_rows - WINDOW]
            past_best_pct = float(past_best_pct_series.dropna().iloc[-1]) \
                if past_best_pct_series.notna().any() else float("nan")
            now_best_pct = float(df["best_pct"].iloc[-1])
            delta_pp = now_best_pct - past_best_pct \
                if past_best_pct == past_best_pct else float("nan")
            delta_str = f"{delta_pp:+.3f}pp"
        else:
            delta_str = "n/a"

        summary_lines.append(
            f"{name:14s}  {len(df):3d} cycles  "
            f"best={best_val:>11,.0f}  ({best_pct:.2f}% SOTA)  "
            f"Δ12={delta_str}"
        )

    # SOTA reference at 100%.
    ax.axhline(
        100.0,
        color="#666666",
        linestyle="--",
        linewidth=1.0,
        label="SOTA reference (100%)",
    )

    # Y-axis: focus on the working range (~96-100%) so movement is visible.
    if all_pcts:
        floor = min(all_pcts) - 1.0
        ax.set_ylim(max(floor, 90.0), 100.5)

    ax.set_xlabel("logged experiment index (cycle)")
    ax.set_ylabel("% SOTA  (higher is better)")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()
    ax.set_title(f"% SOTA over experiments   ({ts})")
    ax.legend(loc="lower right", framealpha=0.95)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.2f}%"))

    plt.tight_layout()
    plt.savefig(OUTPUT, dpi=120, bbox_inches="tight")

    size_kb = OUTPUT.stat().st_size // 1024
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({size_kb} KB)")
    for line in summary_lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
