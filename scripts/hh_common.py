import itertools
import json
import os

from neurowalker.healing2 import HealingV2
from neurowalker.tuned import TunedTripod

CASES = [f"dl_{i}" for i in range(6)] + [f"dl_{i}_{j}" for i, j in itertools.combinations(range(6), 2)]


def tuned():
    b = json.load(open("results/tuned_tripod_tuning.json"))["best"]
    return TunedTripod(b["kp"], b["kr"], b["ks"])


def library():
    """Offline gait library: per fault set, the free-gait candidate with the best SEARCH fitness (tuning seeds 100-101). Never chosen on seeds 0-9."""
    best = {}
    for f in ("results/v3_oracle.jsonl", "results/v3_oracle_long.jsonl", "results/v3_oracle_long2.jsonl"):
        if os.path.exists(f):
            for line in open(f):
                r = json.loads(line)
                if r["case"] not in best or r["search_fitness"] > best[r["case"]]["search_fitness"]:
                    best[r["case"]] = r
    return {tuple(r["legs"]): r["x"] for r in best.values()}


def make(tier, **kw):
    return HealingV2(tuned(), tier=tier, library=library() if tier == "A" else None, **kw)


def survivors_table(rows):
    by = {}
    for r in rows:
        by.setdefault(r["case"], []).append(not r["fell"])
    k = {c: sum(v) for c, v in by.items()}
    return k, sum(1 for v in k.values() if v >= 7), sum(k.values())
