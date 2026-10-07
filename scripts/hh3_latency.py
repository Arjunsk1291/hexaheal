"""HexaHeal v3 Stage 3: response-delay sweep, seeds 0-9. Usage: hh3_latency.py CONFIG_JSON DELAY_S [DELAY_S ...] -> results/v3/hh3_latency_<configname>_<delay>.jsonl (resumable).
Cases (fixed rule in docs/PREREGISTRATION_V3.md): 6 single-leg losses + dl_0_4, dl_0_5, dl_1_3, dl_1_4. Controller: healing v2 Tier B with CONFIG_JSON's B config; the delay holds the diagnosis back while the robot keeps its current gait."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from hh_common import make

from neurowalker.hh_eval import run_episode

CASES = [f"dl_{i}" for i in range(6)] + ["dl_0_4", "dl_0_5", "dl_1_3", "dl_1_4"]
TAG = os.path.basename(sys.argv[1])[:-5]
cfg = json.load(open(sys.argv[1]))["B"]
for d in sys.argv[2:]:
    path = f"results/v3/hh3_latency_{TAG}_{float(d):.1f}.jsonl"
    done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(path)} if os.path.exists(path) else set()
    for case in CASES:
        for sd in range(10):
            if (case, sd) in done: continue
            r = run_episode(make("B", **dict(cfg, extra_delay_s=float(d))), case, sd)
            r["delay_s"] = float(d); r["controller"] = "v2B"
            open(path, "a").write(json.dumps(r, default=float) + "\n")
    print("delay", d, "done", flush=True)
