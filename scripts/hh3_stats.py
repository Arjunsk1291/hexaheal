"""HexaHeal v3 Stage 1 scoring: both definitions (upright, recovered) for every controller on all 21 cases, seeds 0-9 (MEASURED).
Usage: hh3_stats.py TAG [ctrl:file ...]  -> docs/V3_<TAG>.md, results/v3/<TAG>_stats.json. Defaults to the Stage 1 re-score files results/v3/hh3_final_<c>_0-9.jsonl."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "scripts")
from hh_common import CASES

from neurowalker.hh_eval import case_name

tag = sys.argv[1]
NAMES = {"tripod": "plain tripod", "tuned": "tuned tripod", "v1": "healing v1", "v2A": "v2 Tier A (library)", "v2B": "v2 Tier B (online)", "ppo": "PPO reference", "oracle": "oracle (upper bound)"}
spec = [a.split(":", 1) for a in sys.argv[2:]] or [(c, f"results/v3/hh3_final_{c}_0-9.jsonl") for c in NAMES if c != "oracle"]
spec = [(c, f) for c, f in spec if os.path.exists(f)]
oracle_p = "results/v3/hh3_oracle_0-9.jsonl"
if os.path.exists(oracle_p) and not any(c == "oracle" for c, _ in spec):
    spec.append(("oracle", oracle_p))
R = {}
for c, f in spec:
    R[c] = {}
    for line in open(f):
        r = json.loads(line); R[c].setdefault(r["case"], {})[r["seed"]] = r
order = [c for c in NAMES if c in R] + [c for c in R if c not in NAMES]
nm = lambda c: NAMES.get(c, c)  # noqa: E731


def mat(c, key):
    return np.array([[bool(R[c][case][s][key]) if key == "recovered" else (not R[c][case][s]["fell"]) for s in range(10)] for case in CASES])


REC = {c: mat(c, "recovered") for c in R}
UPR = {c: mat(c, "upright") for c in R}
nsurv = lambda m: int((m.sum(1) >= 7).sum())  # noqa: E731
rng = np.random.default_rng(0)
idx = rng.integers(0, 10, (10000, 10))


def wilson(k, n=10, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def boot(M, a, b):
    d = np.array([nsurv(M[a][:, i]) - nsurv(M[b][:, i]) for i in idx])
    return [nsurv(M[a]) - nsurv(M[b]), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


out = {"N_recovered": {c: nsurv(REC[c]) for c in R}, "N_upright": {c: nsurv(UPR[c]) for c in R},
       "total_recovered": {c: int(REC[c].sum()) for c in R}, "total_upright": {c: int(UPR[c].sum()) for c in R},
       "standing_still_total": {c: int((UPR[c] & ~REC[c]).sum()) for c in R}, "boot_recovered": {}, "boot_upright": {}}
L = [f"# HexaHeal v3 - {tag}: recovered vs upright (MEASURED; MuJoCo simulation, 2 vCPU sandbox; seeds 0-9; fault at 4 s, flat, 14 s)", "",
     "Definitions (docs/PREREGISTRATION_V3.md): **upright** = no fall. **recovered** = upright AND forward speed over the last 8 s >= 0.125 m/s (50% of 0.25). A case counts if it holds on >= 7 of 10 seeds. Oracle row: faults from t=0, 15 s, last-8 s window, upper bound with different conditions.", "",
     "| controller | N_recovered (of 21) | N_upright (of 21) | recovered runs /210 | upright runs /210 | upright but standing still /210 |", "|---|---|---|---|---|---|"]
for c in order:
    L.append(f"| {nm(c)} | {out['N_recovered'][c]} | {out['N_upright'][c]} | {out['total_recovered'][c]} | {out['total_upright'][c]} | {out['standing_still_total'][c]} |")
L += ["", "## Paired bootstrap, difference in N (10,000 resamples of the 10 seeds jointly across cases, seed-matched)", "", "| comparison | N_recovered diff [95% CI] | N_upright diff [95% CI] |", "|---|---|---|"]
for a, b in (("v2B", "tripod"), ("v2B", "tuned"), ("v2B", "v1"), ("v2A", "tripod"), ("v1", "tripod"), ("v1", "tuned"), ("v2B", "ppo"), ("v2A", "v2B")):
    if a in R and b in R:
        r1, r2 = boot(REC, a, b), boot(UPR, a, b)
        out["boot_recovered"][f"{a}-{b}"], out["boot_upright"][f"{a}-{b}"] = r1, r2
        L.append(f"| {nm(a)} - {nm(b)} | {r1[0]:+d} [{r1[1]:+.1f}, {r1[2]:+.1f}] | {r2[0]:+d} [{r2[1]:+.1f}, {r2[2]:+.1f}] |")
for title, M in (("Recovered matrix (runs recovered / 10 per case)", REC), ("Upright matrix (runs upright / 10 per case)", UPR)):
    L += ["", f"## {title}", "", "| case | " + " | ".join(nm(c) for c in order) + " |", "|---|" + "---|" * len(order)]
    for i, case in enumerate(CASES):
        L.append(f"| {case_name(case)} | " + " | ".join(f"{int(M[c][i].sum())} [{wilson(int(M[c][i].sum()))[0]:.2f},{wilson(int(M[c][i].sum()))[1]:.2f}]" for c in order) + " |")
L += ["", "## Upright but standing still, per case (runs of 10 that did not fall yet averaged < 0.125 m/s over the last 8 s)", "", "| case | " + " | ".join(nm(c) for c in order) + " |", "|---|" + "---|" * len(order)]
for i, case in enumerate(CASES):
    L.append(f"| {case_name(case)} | " + " | ".join(str(int((UPR[c][i] & ~REC[c][i]).sum())) for c in order) + " |")
L += ["", "Mean last-8 s speed per case (m/s, over the 10 seeds; fallen runs count 0)", "", "| case | " + " | ".join(nm(c) for c in order) + " |", "|---|" + "---|" * len(order)]
for case in CASES:
    L.append(f"| {case_name(case)} | " + " | ".join(f"{np.mean([R[c][case][s]['v_last8'] for s in range(10)]):.3f}" for c in order) + " |")
open(f"docs/V3_{tag}.md", "w").write("\n".join(L) + "\n")
json.dump(out, open(f"results/v3/{tag}_stats.json", "w"), indent=1)
print("\n".join(L[:22]))
