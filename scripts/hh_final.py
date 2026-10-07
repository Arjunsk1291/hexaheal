"""HexaHeal Stage 5: final evaluation on seeds 0-9 ONLY. Usage: hh_final.py CONTROLLER [healthy]  (tripod|tuned|v1|v2A|v2B|ppo).
All 21 leg-loss cases x 10 seeds -> results/hh_final_<ctrl>_0-9.jsonl (resumable). v2 configs come from results/hh_v2_config.json, fixed from tuning-seed results before this runs.
'healthy' runs the no-fault episode (seeds 0-9) with healing on to measure false positives -> results/hh_healthy_<ctrl>_0-9.jsonl."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from hh_common import CASES, make, tuned

from neurowalker.healing import HealingController
from neurowalker.hh_eval import run_episode
from neurowalker.rl import PPOController
from neurowalker.tripod import TripodController

name = sys.argv[1]
healthy = len(sys.argv) > 2 and sys.argv[2] == "healthy"
cfg = json.load(open("results/hh_v2_config.json")) if name.startswith("v2") else {}


def build(seed):
    if name == "tripod": return TripodController()
    if name == "tuned": return tuned()
    if name == "v1": return HealingController(tuned(), terrain="flat", seed=seed)
    if name == "ppo": return PPOController("models/ppo_residual.zip")
    return make(name[-1], **cfg[name[-1]])


path = f"results/hh_{'healthy' if healthy else 'final'}_{name}_0-9.jsonl"
cases = ["healthy"] if healthy else CASES
done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(path)} if os.path.exists(path) else set()
for case in cases:
    for sd in range(10):
        if (case, sd) in done: continue
        r = run_episode(build(sd), case, sd)
        r["controller"] = name
        with open(path, "a") as f: f.write(json.dumps(r, default=float) + "\n")
    print(name, case, flush=True) if not healthy else None
print("DONE", name)
