"""HexaHeal v4 Stage 2 stats (seeds 0-9, MEASURED): Tier B+ vs Tier B vs plain tripod, pre-registered rule, stand-still diagnostic. -> results/v4/stage2_stats.json"""
import json
import sys

import numpy as np

sys.path.insert(0, "scripts")
from hh_common import CASES

def load(f):
    R = {}
    for line in open(f):
        r = json.loads(line); R[(r["case"], r["seed"])] = r
    return R
F = {"tripod": "results/v3/hh3_final_tripod_0-9.jsonl", "B_v3": "results/v3/hh3_final_v2B_0-9.jsonl", "B_rerun": "results/v4/hh4_final_v2B_0-9.jsonl", "Bplus": "results/v4/hh4_final_v2Bplus_0-9.jsonl", "oracle": "results/v3/hh3_oracle_0-9.jsonl"}
R = {k: load(f) for k, f in F.items()}
M = lambda k, key: np.array([[bool(R[k][(c, s)]["recovered"]) if key == "rec" else (not R[k][(c, s)]["fell"]) for s in range(10)] for c in CASES])  # noqa: E731
REC = {k: M(k, "rec") for k in R}; UPR = {k: M(k, "up") for k in R}
N = lambda m: int((m.sum(1) >= 7).sum())  # noqa: E731
idx = np.random.default_rng(0).integers(0, 10, (10000, 10))
def boot(m, a, b):
    d = np.array([N(m[a][:, i]) - N(m[b][:, i]) for i in idx]); return [N(m[a]) - N(m[b]), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
out = {"N_rec": {k: N(REC[k]) for k in R}, "N_up": {k: N(UPR[k]) for k in R}, "runs_rec": {k: int(REC[k].sum()) for k in R}, "runs_up": {k: int(UPR[k].sum()) for k in R},
       "still_runs": {k: int((UPR[k] & ~REC[k]).sum()) for k in R},
       "boot_rec": {"Bplus-B_rerun": boot(REC, "Bplus", "B_rerun"), "Bplus-tripod": boot(REC, "Bplus", "tripod"), "B_rerun-tripod": boot(REC, "B_rerun", "tripod")},
       "boot_up": {"Bplus-B_rerun": boot(UPR, "Bplus", "B_rerun"), "Bplus-tripod": boot(UPR, "Bplus", "tripod")}}
d = out["boot_rec"]["Bplus-B_rerun"]
out["rule_passed"] = bool(d[0] >= 2 and out["N_rec"]["Bplus"] >= 8 and d[1] > 0)
out["B_rerun_matches_v3"] = {"N_rec": [out["N_rec"]["B_rerun"], out["N_rec"]["B_v3"]], "same_runs": int(sum(R["B_rerun"][k]["recovered"] == R["B_v3"][k]["recovered"] and R["B_rerun"][k]["fell"] == R["B_v3"][k]["fell"] for k in R["B_v3"]))}
# stand-still diagnostic (Tier B re-run): all times relative to the fault
diag = {}
for c in CASES:
    rs = [R["B_rerun"][(c, s)] for s in range(10)]
    up = [r for r in rs if not r["fell"]]
    stand = [r["t_stand_s"] for r in rs if r.get("t_stand_s") is not None]
    fw = [r["first_walk_s"] for r in up if r.get("first_walk_s") is not None]
    sw = [r for r in up if r.get("t_stand_s") is not None and r.get("t_plan_start_s") is not None]
    walk_post = sum(1 for r in sw if r.get("first_walk_s") is not None and r["first_walk_s"] >= r["t_plan_start_s"] + r["t_stand_s"] - 0.5)
    diag[c] = {"upright_with_switch": len(sw), "walk_after_switch": walk_post, "upright": len(up), "never_walk": sum(r.get("first_walk_s") is None for r in up), "stand_s_mean": float(np.mean(stand)) if stand else None, "first_walk_s_mean": float(np.mean(fw)) if fw else None, "n_stand": len(stand)}
tot_up = sum(v["upright"] for v in diag.values()); out["diag"] = diag
out["diag_pool"] = {"upright_runs": tot_up, "never_walk_runs": sum(v["never_walk"] for v in diag.values()), "still_end_runs": out["still_runs"]["B_rerun"]}
json.dump(out, open("results/v4/stage2_stats.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "diag"}, indent=1)); print(out["diag_pool"])
