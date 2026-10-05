"""Shared bootstrap/Wilson helpers (copied verbatim from stats_v2.py): paired bootstrap 100,000 resamples, percentile 95%, rng seed 12345."""
import numpy as np

B = 100_000
rng = np.random.default_rng(12345)

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def paired(a, b):
    d = np.asarray(a) - np.asarray(b)
    bs = rng.choice(d, (B, len(d)), replace=True).mean(1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    p = max(2 * min((bs <= 0).mean(), (bs >= 0).mean()), 1 / (B + 1))
    dz = d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else float("nan")
    return dict(diff=float(d.mean()), lo=float(lo), hi=float(hi), p=float(p), dz=float(dz), n=len(d))
