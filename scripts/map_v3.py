"""Build the survival-rate matrix (no fall in 14 s, fault at 4 s) for single and double leg losses. Reads results/v3_stage3_map_0-9.jsonl, writes docs/v3_recovery_map.md.
Legs: 0 R1,1 R2,2 R3,3 L1,4 L2,5 L3 (indices as in hexapod.py: legs 0-2 right, 3-5 left)."""
import itertools
import json
import os

import pandas as pd


d = pd.read_json("results/v3_stage3_map_0-9.jsonl", lines=True)
orc = {json.loads(line)["case"]: json.loads(line) for line in open("results/v3_oracle.jsonl")} if os.path.exists("results/v3_oracle.jsonl") else {}
cases = [f"dl_{i}" for i in range(6)] + [f"dl_{i}_{j}" for i, j in itertools.combinations(range(6), 2)]
cols = [("tripod", ""), ("tripod", "+healing"), ("tuned_tripod", ""), ("tuned_tripod", "+healing")]
md = ["# V3 Stage 3 recovery map (seeds 0-9, flat, simulation, 2 vCPU sandbox)", "", "Survival = no fall by 14 s with leg(s) disabled at 4.0 s (cell = survivors/10). Oracle column: offline CMA-ES over a free-gait family, faults from t=0, validated on seeds 0-9 over 10 s (walks = no fall and >= 1.0 m on >= 8/10 seeds).", "",
      "| case | tripod | tripod+heal | tuned | tuned+heal | healing recoveries (tuned+heal, mean/run) | oracle: survivors/10, mean dist m | oracle walks? |", "|---|---|---|---|---|---|---|---|"]
for c in cases:
    row = []
    for ctrl, h in cols:
        g = d[(d.controller == ctrl) & (d.scenario == c + h)]
        row.append(f"{int((~g.fell).sum())}/{len(g)}" if len(g) else "-")
    g = d[(d.controller == "tuned_tripod") & (d.scenario == c + "+healing")]
    rec = f"{g.n_recover.mean():.1f}" if len(g) and "n_recover" in g else "-"
    o = orc.get(c)
    ocell = f"{10 - o['val_falls']}/10, {sum(o['val_dist']) / 10:.2f}" if o else "not run"
    md.append(f"| {c} | " + " | ".join(row) + f" | {rec} | {ocell} | {('YES' if o['walks'] else 'NO') if o else '-'} |")
md += ["", "Wilson 95% for k/10: 0/10 0.00-0.28, 3/10 0.11-0.60, 5/10 0.24-0.76, 7/10 0.40-0.89, 10/10 0.72-1.00."]
open("docs/v3_recovery_map.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
