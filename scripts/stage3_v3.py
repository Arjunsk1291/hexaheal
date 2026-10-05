"""V3 Stage 3: recovery map. All 6 single and all 15 double leg losses (simultaneous at 4 s, flat, 14 s), tuned tripod and plain tripod, each without and with healing, seeds 0-9.
Output results/v3_stage3_map_0-9.jsonl (resumable). Planner limit vs physics limit is separated by scripts/oracle_v3.py."""
import itertools
import json
import os
import sys

sys.path.insert(0, "scripts")
from neurowalker.benchmark import run_one
from neurowalker.tripod import TripodController
from neurowalker.tuned import TunedTripod

a, b = (sys.argv[1] if len(sys.argv) > 1 else "0-9").split("-"); seeds = range(int(a), int(b) + 1)
path = f"results/v3_stage3_map_{a}-{b}.jsonl"
best = json.load(open("results/tuned_tripod_tuning.json"))["best"]
cases = [f"dl_{i}" for i in range(6)] + [f"dl_{i}_{j}" for i, j in itertools.combinations(range(6), 2)]
done = set()
if os.path.exists(path):
    for line in open(path):
        r = json.loads(line); done.add((r["controller"], r["scenario"], r["seed"]))
for cname in ("tripod", "tuned_tripod"):
    for heal in ("", "+healing"):
        for case in cases:
            for sd in seeds:
                if (cname, case + heal, sd) in done: continue
                ctrl = TripodController() if cname == "tripod" else TunedTripod(best["kp"], best["kr"], best["ks"])
                r, log = run_one(ctrl, cname, case + heal, sd)
                if log is not None:
                    r["n_recover"] = sum(1 for d in log if d["to"] == "NORMAL" and "recovery verified" in str(d["action"]))
                    r["n_safe_stop"] = sum(1 for d in log if d["to"] == "SAFE_STOP")
                with open(path, "a") as f: f.write(json.dumps(r, default=float) + "\n")
        print(cname, heal or "no-heal", "done", flush=True)
print("DONE")
