"""V3 Stage 3 oracle: long-budget OFFLINE CMA-ES over a rich open-loop gait (free per-leg phase/stride/lift + global params; src/neurowalker/v3.py FreeGait)
to find out whether ANY gait in this family can walk with each leg-loss set. Faults are active from t=0 (steady-state existence question, not detection).
Search (fitness) uses tuning seeds 100-101; the best gait is then validated on seeds 0-9 (10 s episodes). 'walks' = no fall in 10 s and distance >= 1.0 m in 10 s (0.1 m/s) on >= 8/10 validation seeds.
Usage: python scripts/oracle_v3.py [--gens N] [case ...]   cases like dl_2 or dl_2_5. Output results/v3_oracle.jsonl (resumable)."""
import itertools
import json
import os
import sys

import cma
import numpy as np

sys.path.insert(0, "scripts")
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.v3 import FreeGait

args = sys.argv[1:]
gens = 30
if args and args[0] == "--gens":
    gens = int(args[1]); args = args[2:]
cases = args or [f"dl_{i}" for i in range(6)] + [f"dl_{i}_{j}" for i, j in itertools.combinations(range(6), 2)]
path = "results/v3_oracle.jsonl"
done = {json.loads(line)["case"] for line in open(path)} if os.path.exists(path) else set()
LO = np.array([0.8, 0.1, 0.1, 0.4, -0.5, -0.2] + [0.0] * 6 + [0.0] * 6 + [0.0] * 6)
HI = np.array([2.6, 0.55, 0.6, 0.85, 0.5, 0.2] + [1.0] * 6 + [1.6] * 6 + [1.6] * 6)
X0 = np.array([1.5, 0.35, 0.35, 0.55, 0.0, 0.0, 0, .5, 0, .5, 0, .5][:12] + [1.0] * 6 + [1.0] * 6)
X0[6:12] = [0, .5, 0, .5, 0, .5]  # tripod phases (legs 0,2,4 in A)
X0[6:12] = [0, 0.5, 0, 0.5, 0, 0.5]


def rollout(x, legs, seed, t=10.0):
    e = HexapodEnv("flat", max_time=t, faults=[Fault("disable_leg", 0.0, leg=lg) for lg in legs], rand=0.1, seed=seed, target_speed=0.25)
    e.reset(seed=seed); g = FreeGait(x); g.reset()
    while True:
        _, _, te, tr, _ = e.step(g.act(e))
        if te or tr: break
    return e.distance(), abs(float(e.data.qpos[1])), bool(e.fell), e.t


def fit(u, legs):
    x = LO + np.clip(u, 0, 1) * (HI - LO); tot = 0.0
    for sd in (100, 101):
        d, y, fell, t = rollout(x, legs, sd)
        tot += d - 1.0 * y - (3.0 if fell else 0.0) + 0.1 * t
    return -tot / 2


for case in cases:
    if case in done: continue
    legs = [int(v) for v in case[3:].split("_")]
    best = (1e9, None)
    for rs, init in enumerate(("tripod", "random")):
        rng = np.random.default_rng(len(case) * 100 + rs)
        u0 = (X0 - LO) / (HI - LO) if init == "tripod" else rng.uniform(0.2, 0.8, len(LO))
        es = cma.CMAEvolutionStrategy(np.clip(u0, 0, 1), 0.3, {"popsize": 16, "seed": 7 + rs, "verbose": -9, "bounds": [0, 1]})
        for _ in range(gens):
            s = es.ask(); f = [fit(v, legs) for v in s]; es.tell(s, f)
            if min(f) < best[0]: best = (min(f), s[int(np.argmin(f))])
    x = LO + np.clip(best[1], 0, 1) * (HI - LO)
    val = [rollout(x, legs, sd) for sd in range(10)]
    rec = dict(case=case, legs=legs, gens=gens, popsize=16, restarts=2, search_fitness=-best[0], x=x.tolist(),
               val_falls=int(sum(v[2] for v in val)), val_dist=[round(v[0], 3) for v in val], val_t=[round(v[3], 2) for v in val],
               walks=bool(sum((not v[2]) and v[0] >= 1.0 for v in val) >= 8))
    with open(path, "a") as f: f.write(json.dumps(rec) + "\n")
    print(case, "walks", rec["walks"], "falls", rec["val_falls"], "dist", np.round(np.mean(rec["val_dist"]), 2), flush=True)
print("DONE")
