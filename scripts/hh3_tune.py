"""HexaHeal v3 Stage 2 tuning on seeds 100-109 ONLY (never 0-9). Usage: hh3_tune.py CTRL NAME key=val ... -> results/v3/tune_<NAME>.jsonl (resumable).
CTRL: tuned | B (healing v2 Tier B, defaults from results/hh_v2_config.json overridden by key=val). Prints N_recovered, N_upright (cases with >=7/10) and run totals."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from hh_common import CASES, make, tuned

from neurowalker.hh_eval import run_episode

ctrl, name = sys.argv[1], sys.argv[2]
kw = dict(json.load(open("results/hh_v2_config.json"))["B"]) if ctrl == "B" else {}
for a in sys.argv[3:]:
    k, v = a.split("=")
    kw[k] = v if k == "interim" else (float(v) if "." in v else int(v)) if v not in ("True", "False") else v == "True"
path = f"results/v3/tune_{name}.jsonl"
done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(path)} if os.path.exists(path) else set()
for case in CASES:
    for sd in range(100, 110):
        if (case, sd) in done: continue
        r = run_episode(tuned() if ctrl == "tuned" else make("B", **kw), case, sd)
        r["cfg"] = kw
        with open(path, "a") as f: f.write(json.dumps(r, default=float) + "\n")
rows = [json.loads(line) for line in open(path)]
by = {}
for r in rows: by.setdefault(r["case"], []).append(r)
nrec = sum(1 for v in by.values() if sum(x["recovered"] for x in v) >= 7)
nup = sum(1 for v in by.values() if sum(not x["fell"] for x in v) >= 7)
print(ctrl, name, kw, "N_recovered", nrec, "N_upright", nup, "recovered runs", sum(x["recovered"] for x in rows), "upright runs", sum(not x["fell"] for x in rows), flush=True)
