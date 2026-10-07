"""HexaHeal Stage 2: re-validate every oracle gait on held-out seeds 0-9.
DEFINITION (fixed before running): a gait 'walks' on a seed if, with the leg(s) disabled from t=0 for 15 s of sim time, it does not fall AND forward progress
(x displacement) is at least X = 40% of the nominal speed. Nominal speed = the commanded target speed 0.25 m/s, so X*15 s = 1.5 m. A CASE 'holds up' if it
walks on >= 7/10 seeds (same threshold as the primary metric). Oracle gaits are UPPER BOUNDS (open loop, fault known from t=0, searched offline), not controllers.
Gait selection per case: the candidate (short or long budget) with the best SEARCH fitness (tuning seeds 100-101), never by seeds 0-9.
Output: results/hh_stage2_oracle_0-9.jsonl (one row per case x seed) and results/hh_stage2_oracle_summary.json."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "scripts")
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.freegait import FreeGait

NOMINAL, X_FRAC, T_EP, MIN_SEEDS = 0.25, 0.40, 15.0, 7
OUT = "results/hh_stage2_oracle_0-9.jsonl"
best = {}
for f in ("results/v3_oracle.jsonl", "results/v3_oracle_long.jsonl", "results/v3_oracle_long2.jsonl"):
    if os.path.exists(f):
        for line in open(f):
            r = json.loads(line)
            if r["case"] not in best or r["search_fitness"] > best[r["case"]]["search_fitness"]:
                best[r["case"]] = dict(r, src=f)
done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(OUT)} if os.path.exists(OUT) else set()
for case, r in sorted(best.items(), key=lambda kv: (len(kv[1]["legs"]), kv[1]["legs"])):
    for seed in range(10):
        if (case, seed) in done: continue
        e = HexapodEnv("flat", max_time=T_EP, faults=[Fault("disable_leg", 0.0, leg=lg) for lg in r["legs"]], rand=0.1, seed=seed, target_speed=NOMINAL)
        e.reset(seed=seed); g = FreeGait(np.array(r["x"])); g.reset()
        while True:
            _, _, te, tr, _ = e.step(g.act(e))
            if te or tr: break
        d = float(e.distance()); fell = bool(e.fell)
        row = dict(case=case, legs=r["legs"], seed=seed, fell=fell, t_end=float(e.t), distance=d, speed=d / max(float(e.t), 1e-6),
                   speed_ratio=d / max(float(e.t), 1e-6) / NOMINAL, lateral=abs(float(e.data.qpos[1])), src=r["src"], search_fitness=r["search_fitness"],
                   walks=bool((not fell) and e.t >= T_EP - 0.05 and d >= X_FRAC * NOMINAL * T_EP))
        with open(OUT, "a") as f: f.write(json.dumps(row) + "\n")
    print(case, flush=True)
rows = [json.loads(line) for line in open(OUT)]
summ = {}
for case in best:
    rs = [x for x in rows if x["case"] == case]
    k = sum(x["walks"] for x in rs)
    summ[case] = dict(walk_seeds=k, falls=sum(x["fell"] for x in rs), mean_speed_ratio=float(np.mean([x["speed_ratio"] for x in rs])), holds_up=k >= MIN_SEEDS, src=best[case]["src"])
json.dump(dict(definition=dict(T=T_EP, nominal=NOMINAL, x_frac=X_FRAC, min_seeds=MIN_SEEDS), cases=summ, n_hold_up=sum(v["holds_up"] for v in summ.values())), open("results/hh_stage2_oracle_summary.json", "w"), indent=1)
print("hold up:", sum(v["holds_up"] for v in summ.values()), "of", len(summ))
