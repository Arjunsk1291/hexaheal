"""HexaHeal v3 Stage 4: second fault type, seeds 0-9. Usage: hh3_fault2.py CTRL [CONFIG_JSON] (tripod|tuned|v2B) -> results/v3/hh3_fault2_<ctrl>.jsonl (resumable).
Faults at t=4 s on each single leg R1..L3: 'lock' = femur joint locked at its current angle; 'torque30' = leg actuators limited to 30% of torque. 12 cases x 10 seeds."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from hh_common import make, tuned

from neurowalker.faults import Fault
from neurowalker.hh_eval import FAULT_T, run_episode
from neurowalker.tripod import TripodController

name = sys.argv[1]
cfg = json.load(open(sys.argv[2]))["B"] if len(sys.argv) > 2 else None
path = f"results/v3/hh3_fault2_{name}.jsonl"
done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(path)} if os.path.exists(path) else set()
for kind in ("lock", "torque30"):
    for leg in range(6):
        case = f"{kind}_{leg}"
        for sd in range(10):
            if (case, sd) in done: continue
            f = [Fault("lock_joint", FAULT_T, leg=leg, joint=1)] if kind == "lock" else [Fault("reduce_torque", FAULT_T, leg=leg, severity=0.3)]
            c = TripodController() if name == "tripod" else tuned() if name == "tuned" else make("B", **cfg)
            r = run_episode(c, case, sd, faults=f)
            r["controller"] = name; r["true_legs"] = [leg]
            open(path, "a").write(json.dumps(r, default=float) + "\n")
    print(name, kind, "done", flush=True)
