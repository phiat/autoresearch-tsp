"""
Generate progress.png at repo root showing best val_cost over cycle index
for both tsp_heuristic and tsp_neural loops, with a SOTA reference line.

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
    # Treat 0 as "crash" sentinel and ignore for best-so-far.
    df["val_for_best"] = df["val_cost"].replace(0, pd.NA)
    df["best"] = df["val_for_best"].cummin()
    return df


def main() -> None:
    fig, ax = plt.subplots(figsize=(9, 5), dpi=120)

    summary_lines: list[str] = []

    for name, path, color in LOOPS:
        df = load_loop(name, path)
        if df is None:
            print(f"skip: {name} (no data at {path})")
            continue
        # Best-so-far line, only plot where best is finite.
        mask = df["best"].notna()
        ax.plot(
            df.loc[mask, "cycle"],
            df.loc[mask, "best"],
            marker="o",
            markersize=3,
            linestyle="-",
            linewidth=1.6,
            color=color,
            label=f"{name}/  (best so far)",
        )
        # Overlay each kept run faintly for context.
        keeps = df[(df["status"] == "keep") & (df["val_for_best"].notna())]
        if len(keeps):
            ax.scatter(
                keeps["cycle"],
                keeps["val_cost"],
                marker=".",
                s=12,
                color=color,
                alpha=0.35,
            )
        best = df["val_for_best"].min()
        gap = (best - SOTA) / SOTA * 100
        sota_pct = 100 - gap
        summary_lines.append(
            f"{name:14s}  {len(df):3d} cycles  best={best:>11,.0f}  "
            f"({sota_pct:.2f}% SOTA)"
        )

    ax.axhline(
        SOTA,
        color="#666666",
        linestyle="--",
        linewidth=1.0,
        label=f"SOTA reference ({SOTA:,})",
    )

    ax.set_xlabel("logged experiment index (cycle)")
    ax.set_ylabel("val_cost (lower is better)")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()
    ax.set_title(f"Best val_cost over time   ({ts})")
    ax.legend(loc="upper right", framealpha=0.95)
    ax.grid(True, alpha=0.3)
    ax.ticklabel_format(axis="y", style="plain")

    plt.tight_layout()
    plt.savefig(OUTPUT, dpi=120, bbox_inches="tight")

    size_kb = OUTPUT.stat().st_size // 1024
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({size_kb} KB)")
    for line in summary_lines:
        print(f"  {line}")


if __name__ == "__main__":
    main()
