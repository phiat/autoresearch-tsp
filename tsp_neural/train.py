"""Train a tiny MLP move-acceptance scorer on harvested 2-opt moves.

Loads the latest moves/*.npz, derives a 9-d feature vector per move
from city coords + prime flags, balances positives/negatives, trains a
2-layer MLP with BCE (default) or MSE-on-gain (LOSS=mse), and saves
the checkpoint plus feature mean/std to checkpoints/<tag>.pt.

Reports AUC on a held-out unbalanced split, compared against the
geographic baseline (`score = -d_a_c`, i.e. closer candidates first).
"""

import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from prepare import load_cities

LOSS_MODE = os.environ.get("LOSS", "bce")  # "bce" or "mse"

CHECKPOINTS_DIR = Path(__file__).parent / "checkpoints"
MOVES_DIR = Path(__file__).parent / "moves"

FEATURE_NAMES = [
    "d_a_anext", "d_c_cnext", "d_a_c", "d_anext_cnext",
    "prime_a", "prime_anext", "prime_c", "prime_cnext",
    "log_pos_delta",
]
N_FEATURES = len(FEATURE_NAMES)


def latest_moves_path() -> Path:
    paths = sorted(MOVES_DIR.glob("*.npz"), key=lambda p: p.stat().st_mtime)
    if not paths:
        raise FileNotFoundError("no moves/*.npz found — run `just harvest` first")
    return paths[-1]


def build_features(npz_path: Path, xy: np.ndarray, is_prime: np.ndarray):
    d = np.load(npz_path)
    a, an, c, cn = d["a"], d["a_next"], d["c"], d["c_next"]
    pd = np.abs(d["pos_delta"]).astype(np.float32)
    accepted = d["accepted"].astype(np.uint8)

    def edge_len(u, v):
        dx = xy[u, 0] - xy[v, 0]
        dy = xy[u, 1] - xy[v, 1]
        return np.sqrt(dx * dx + dy * dy).astype(np.float32)

    feats = np.empty((len(a), N_FEATURES), dtype=np.float32)
    feats[:, 0] = edge_len(a, an)
    feats[:, 1] = edge_len(c, cn)
    feats[:, 2] = edge_len(a, c)
    feats[:, 3] = edge_len(an, cn)
    feats[:, 4] = is_prime[a].astype(np.float32)
    feats[:, 5] = is_prime[an].astype(np.float32)
    feats[:, 6] = is_prime[c].astype(np.float32)
    feats[:, 7] = is_prime[cn].astype(np.float32)
    feats[:, 8] = np.log1p(pd)
    return feats, accepted


class MLP(nn.Module):
    def __init__(self, n_in=N_FEATURES, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def auc_numpy(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney AUC. Higher score should mean more likely positive."""
    labels = labels.astype(bool)
    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="stable")
    ranks = np.empty(len(scores), dtype=np.float64)
    ranks[order] = np.arange(len(scores)) + 1.0  # 1-indexed
    sum_ranks_pos = ranks[labels].sum()
    return float((sum_ranks_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def train_and_eval(tag: str = "latest"):
    t0 = time.perf_counter()
    moves_path = latest_moves_path()
    print(f"loading moves from {moves_path.name}")
    xy, is_prime = load_cities()

    feats, labels = build_features(moves_path, xy, is_prime)
    d_raw = np.load(moves_path)
    gain = d_raw["gain"].astype(np.float32)
    n = len(feats)
    print(f"  rows: {n:,}   accepted: {int(labels.sum()):,} ({100*labels.mean():.3f}%)   loss: {LOSS_MODE}")

    rng = np.random.default_rng(42)
    pos_idx = np.where(labels == 1)[0]
    neg_idx = np.where(labels == 0)[0]
    neg_sample = rng.choice(neg_idx, size=len(pos_idx), replace=False)

    holdout_pool = np.setdiff1d(neg_idx, neg_sample, assume_unique=False)
    holdout_neg_n = min(200_000, len(holdout_pool))
    holdout_neg = rng.choice(holdout_pool, size=holdout_neg_n, replace=False)

    bal_idx = rng.permutation(np.concatenate([pos_idx, neg_sample]))
    n_bal = len(bal_idx)
    n_train = int(0.8 * n_bal)
    n_val = int(0.1 * n_bal)
    train_idx = bal_idx[:n_train]
    val_idx = bal_idx[n_train:n_train + n_val]
    test_idx = bal_idx[n_train + n_val:]

    mu = feats[train_idx].mean(axis=0)
    sd = feats[train_idx].std(axis=0)
    sd = np.where(sd < 1e-6, 1.0, sd)

    def norm(x):
        return ((x - mu) / sd).astype(np.float32)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  device: {device}")
    if LOSS_MODE == "mse":
        gain_mu = float(gain.mean())
        gain_sd = float(gain.std()) or 1.0
        targets_full = ((gain - gain_mu) / gain_sd).astype(np.float32)
    else:
        gain_mu = 0.0
        gain_sd = 1.0
        targets_full = labels.astype(np.float32)

    Xtr = torch.from_numpy(norm(feats[train_idx])).to(device)
    Ytr = torch.from_numpy(targets_full[train_idx]).to(device)
    Xval = torch.from_numpy(norm(feats[val_idx])).to(device)
    Yval = labels[val_idx]
    Xtest = torch.from_numpy(norm(feats[test_idx])).to(device)
    Ytest = labels[test_idx]

    holdout_idx = np.concatenate([pos_idx, holdout_neg])
    Xho = torch.from_numpy(norm(feats[holdout_idx])).to(device)
    Yho = labels[holdout_idx]
    geo_score_ho = -feats[holdout_idx, 2]  # smaller d_a_c = picked first

    model = MLP().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  model_params: {n_params}")
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss() if LOSS_MODE == "mse" else nn.BCEWithLogitsLoss()

    batch = 4096
    epochs = 30
    best_val_auc = 0.0
    best_state = None
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(Xtr), device=device)
        total_loss = 0.0
        for i in range(0, len(Xtr), batch):
            idx = perm[i:i + batch]
            logits = model(Xtr[idx])
            loss = loss_fn(logits, Ytr[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += float(loss) * len(idx)
        total_loss /= len(Xtr)

        model.eval()
        with torch.no_grad():
            val_scores = model(Xval).cpu().numpy()
        val_auc = auc_numpy(val_scores, Yval)
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        if ep % 5 == 0 or ep == epochs - 1:
            print(f"  epoch {ep:3d}  loss={total_loss:.4f}  val_auc={val_auc:.4f}")

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        test_scores = model(Xtest).cpu().numpy()
        ho_scores = model(Xho).cpu().numpy()
    test_auc = auc_numpy(test_scores, Ytest)
    ho_auc_model = auc_numpy(ho_scores, Yho)
    ho_auc_geo = auc_numpy(geo_score_ho, Yho)

    print(f"  test_auc (balanced):     {test_auc:.4f}")
    print(f"  holdout_auc (model):     {ho_auc_model:.4f}")
    print(f"  holdout_auc (geographic, -d_a_c): {ho_auc_geo:.4f}")
    print(f"  delta vs geographic:     {ho_auc_model - ho_auc_geo:+.4f}")

    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINTS_DIR / f"{tag}.pt"
    torch.save({
        "state_dict": model.state_dict(),
        "mu": mu.tolist(),
        "sd": sd.tolist(),
        "feature_names": FEATURE_NAMES,
        "n_in": N_FEATURES,
        "test_auc": test_auc,
        "holdout_auc_model": ho_auc_model,
        "holdout_auc_geo": ho_auc_geo,
        "loss_mode": LOSS_MODE,
        "gain_mu": gain_mu,
        "gain_sd": gain_sd,
    }, ckpt_path)

    training_seconds = time.perf_counter() - t0
    print(f"---")
    print(f"val_cost:         (training-only run)")
    print(f"solve_seconds:    0.00")
    print(f"total_seconds:    {training_seconds:.2f}")
    print(f"model_params:     {n_params}")
    print(f"training_seconds: {training_seconds:.2f}")
    print(f"test_auc:         {test_auc:.4f}")
    print(f"holdout_auc:      {ho_auc_model:.4f}")
    print(f"baseline_auc:     {ho_auc_geo:.4f}")
    print(f"checkpoint:       {ckpt_path}")
    return ckpt_path


if __name__ == "__main__":
    train_and_eval()
