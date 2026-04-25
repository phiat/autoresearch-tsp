"""Move-data harvesting for the neural-guided loop.

Pre-allocates fixed-size numpy buffers that the numba-jitted 2-opt
sweep writes into for every candidate it scores. After the solve, the
filled prefix is sliced and saved as a compressed npz so later cycles
can train on it.

Schema per row (one row per scored 2-opt candidate, accepted or not):
  a, a_next, c, c_next : int32 city ids of the 4 endpoints involved
  pos_delta            : int32 = |cj - ai|, distance along the tour
  gain                 : float32 signed Euclidean gain from the swap
  accepted             : uint8  1 if gain > 1e-12 (the sweep took it)
"""

import numpy as np
from pathlib import Path

MOVES_DIR = Path(__file__).parent / "moves"
MAX_ROWS = 25_000_000  # ~525MB at 21B/row; we cap and stop logging past this


def make_buffers(max_rows: int = MAX_ROWS) -> dict:
    return dict(
        a=np.zeros(max_rows, dtype=np.int32),
        a_next=np.zeros(max_rows, dtype=np.int32),
        c=np.zeros(max_rows, dtype=np.int32),
        c_next=np.zeros(max_rows, dtype=np.int32),
        pos_delta=np.zeros(max_rows, dtype=np.int32),
        gain=np.zeros(max_rows, dtype=np.float32),
        accepted=np.zeros(max_rows, dtype=np.uint8),
        count=np.zeros(1, dtype=np.int64),
    )


def save_buffers(buffers: dict, tag: str) -> tuple[Path, int]:
    MOVES_DIR.mkdir(parents=True, exist_ok=True)
    n = int(buffers["count"][0])
    cap = len(buffers["a"])
    n = min(n, cap)
    out_path = MOVES_DIR / f"{tag}.npz"
    np.savez_compressed(
        out_path,
        a=buffers["a"][:n],
        a_next=buffers["a_next"][:n],
        c=buffers["c"][:n],
        c_next=buffers["c_next"][:n],
        pos_delta=buffers["pos_delta"][:n],
        gain=buffers["gain"][:n],
        accepted=buffers["accepted"][:n],
    )
    return out_path, n
