"""HexaHeal v3 Stage 1: oracle gaits re-run on seeds 0-9 with the pre-registered 'recovered' rule (last 8 s window [7,15], >= 0.125 m/s, no fall).
Same gait selection as hh_stage2_oracle_validation.py (best search fitness on tuning seeds). Oracle = faults from t=0, 15 s: an upper bound, not a controller."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "scripts")
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.freegait import FreeGait

OUT = "results/v3/hh3_oracle_0-9.jsonl"
best = {}
for f in ("results/v3_oracle.jsonl", "results/v3_oracle_long.jsonl", "results/v3_oracle_long2.jsonl"):
    for line in open(f):
        r = json.loads(line)
        if r["case"] not in best or r["search_fitness"] > best[r["case"]]["search_fitness"]:
            best[r["case"]] = r
done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(OUT)} if os.path.exists(OUT) else set()
for case, r in sorted(best.items(), key=lambda kv: (len(kv[1]["legs"]), kv[1]["legs"])):
    for seed in range(10):
        if (case, seed) in done: continue
        e = HexapodEnv("flat", max_time=15.0, faults=[Fault("disable_leg", 0.0, leg=lg) for lg in r["legs"]], rand=0.1, seed=seed, target_speed=0.25)
        e.reset(seed=seed); g = FreeGait(np.array(r["x"])); g.reset()
        ts, xs = [], []
        while True:
            _, _, te, tr, _ = e.step(g.act(e)); ts.append(e.t); xs.append(float(e.data.qpos[0]))
            if te or tr: break
        ts, xs = np.array(ts), np.array(xs)
        full = (not e.fell) and ts[-1] >= 15.0 - 0.05
        v8 = float((xs[-1] - xs[min(np.searchsorted(ts, 7.0), len(xs) - 1)]) / 8.0) if full else 0.0
        row = dict(case=case, seed=seed, fell=bool(e.fell), t_end=float(e.t), v_last8=v8, recovered=bool(full and v8 >= 0.125), controller="oracle")
        open(OUT, "a").write(json.dumps(row) + "\n")
    print(case, flush=True)
print("DONE oracle")
