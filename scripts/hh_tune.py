"""HexaHeal Stage 4 tuning on seeds 100-109 ONLY. Usage: hh_tune.py TIER NAME key=val ...  -> results/hh_tune_<TIER>_<NAME>.jsonl (resumable)."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from hh_common import CASES, make, survivors_table

from neurowalker.hh_eval import run_episode

tier, name = sys.argv[1], sys.argv[2]
kw = {}
for a in sys.argv[3:]:
    k, v = a.split("=")
    kw[k] = v if k == "interim" else float(v) if "." in v else int(v)
path = f"results/hh_tune_{tier}_{name}.jsonl"
done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(path)} if os.path.exists(path) else set()
for case in CASES:
    for sd in range(100, 110):
        if (case, sd) in done: continue
        r = run_episode(make(tier, **kw), case, sd)
        r["cfg"] = kw
        with open(path, "a") as f: f.write(json.dumps(r, default=float) + "\n")
rows = [json.loads(line) for line in open(path)]
k, n7, tot = survivors_table(rows)
print(tier, name, kw, "N_surv(>=7/10)", n7, "total survivors", tot, flush=True)
