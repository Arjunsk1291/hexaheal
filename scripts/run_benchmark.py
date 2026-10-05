"""Run the arena. Resumable: partial rows are appended to results/benchmark_partial.jsonl."""
import argparse
import json
import os
import time

import pandas as pd

from neurowalker.benchmark import SCENARIOS, run_one
from neurowalker.tripod import TripodController

ap = argparse.ArgumentParser()
ap.add_argument("--controllers", default="tripod,connectome,ppo")
ap.add_argument("--scenarios", default=",".join(SCENARIOS))
ap.add_argument("--seeds", type=int, default=10)
ap.add_argument("--max-minutes", type=float, default=60)
ap.add_argument("--ppo-model", default="models/ppo_residual.zip")
a = ap.parse_args()
os.makedirs("results/decision_logs", exist_ok=True)
part = "results/benchmark_partial.jsonl"
done = set()
if os.path.exists(part):
    for l in open(part):
        r = json.loads(l); done.add((r["controller"], r["scenario"], r["seed"]))
ctrls = {}
for name in a.controllers.split(","):
    if name == "tripod": ctrls[name] = TripodController()
    elif name == "connectome":
        from neurowalker.brain import BrainController; ctrls[name] = BrainController()
    elif name == "ppo":
        from neurowalker.rl import PPOController; ctrls[name] = PPOController(a.ppo_model)
t0 = time.time(); n = 0
for sc in a.scenarios.split(","):
    for cn, c in ctrls.items():
        for seed in range(a.seeds):
            if (cn, sc, seed) in done: continue
            if (time.time() - t0) / 60 > a.max_minutes:
                print("time budget reached; resume to continue"); raise SystemExit(0)
            row, log = run_one(c, cn, sc, seed)
            with open(part, "a") as f: f.write(json.dumps(row) + "\n")
            if log is not None and seed == 0:
                json.dump({"controller": cn, "scenario": sc, "seed": seed, "decisions": log}, open(f"results/decision_logs/{cn}__{sc}__seed{seed}.json", "w"), indent=1, default=float)
            n += 1
            if n % 10 == 0: print(n, cn, sc, seed, f"{(time.time()-t0)/60:.1f} min", flush=True)
rows = [json.loads(l) for l in open(part)]
pd.DataFrame(rows).to_parquet("results/benchmark.parquet")
print("wrote results/benchmark.parquet", len(rows))
