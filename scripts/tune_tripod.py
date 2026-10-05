"""Tune TunedTripod gains on seeds 100-109 only (never 0-9). Grid over kp, kr, ks; objective: falls on slope15 and slope10, then slope15 distance,
subject to flat distance >= 0.95 * plain tripod flat distance (same seeds). Writes results/tuned_tripod_tuning.json."""
import itertools
import json

import numpy as np

from neurowalker.benchmark import run_one
from neurowalker.tuned import TunedTripod

SEEDS = range(100, 110)
def ev(g, sc):
    c = TunedTripod(*g)
    rs = [run_one(c, "tuned_tripod", sc, s)[0] for s in SEEDS]
    return sum(r["fell"] for r in rs), float(np.mean([r["distance"] for r in rs]))
base_flat = ev((0, 0, 0), "flat")[1]
rows = []
for g in itertools.product([-1.2, -0.6, 0.0, 0.6, 1.2, 2.0], [0.0, 0.5, 1.0], [0.0, 2.0, 4.0]):
    f15, d15 = ev(g, "slope15"); f10, d10 = ev(g, "slope10"); _, df = ev(g, "flat")
    rows.append(dict(kp=g[0], kr=g[1], ks=g[2], falls15=f15, dist15=d15, falls10=f10, dist10=d10, flat=df, ok_flat=bool(df >= 0.95 * base_flat)))
    print(rows[-1], flush=True)
ok = [r for r in rows if r["ok_flat"]]
best = min(ok, key=lambda r: (r["falls15"] + r["falls10"], -r["dist15"]))
json.dump(dict(seeds="100-109", base_flat=base_flat, best=best, grid=rows), open("results/tuned_tripod_tuning.json", "w"), indent=1)
print("BEST", best)
