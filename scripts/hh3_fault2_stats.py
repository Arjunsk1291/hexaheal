"""HexaHeal v3 Stage 4 table: second fault type (femur joint locked / leg torque 30%), single legs, seeds 0-9, MEASURED. -> docs/V3_fault2.md"""
import json
import collections

LEG = ["R1", "R2", "R3", "L1", "L2", "L3"]
F = [("tripod", "plain tripod", "results/v3/hh3_fault2_tripod.jsonl"), ("tuned", "tuned tripod", "results/v3/hh3_fault2_tuned.jsonl"), ("v2B", "v2 Tier B (frozen config)", "results/v3/hh3_fault2_v2B_baseconfig.jsonl")]
D = {}
for k, _, p in F:
    D[k] = collections.defaultdict(list)
    for line in open(p):
        r = json.loads(line); D[k][r["case"]].append(r)
cases = [f"{k}_{i}" for k in ("lock", "torque30") for i in range(6)]
L = ["# HexaHeal v3 Stage 4: second fault type (MEASURED; MuJoCo simulation; seeds 0-9; fault at 4 s; flat; 14 s)", "",
     "Faults on single legs only (stated subset): **lock** = femur joint locked at its current angle; **torque30** = that leg's actuators limited to 30% of torque. Controllers were NOT tuned for these faults (v2 uses the frozen leg-loss config; its detector was designed for leg loss). Cells = upright / recovered runs of 10.", "",
     "| controller | N_recovered (of 12) | N_upright (of 12) | recovered runs /120 | upright runs /120 | detections /120 |", "|---|---|---|---|---|---|"]
for k, nm, _ in F:
    d = D[k]
    L.append(f"| {nm} | {sum(1 for c in cases if sum(x['recovered'] for x in d[c]) >= 7)} | {sum(1 for c in cases if sum(not x['fell'] for x in d[c]) >= 7)} | {sum(x['recovered'] for c in cases for x in d[c])} | {sum(not x['fell'] for c in cases for x in d[c])} | {sum(1 for c in cases for x in d[c] if x.get('t_detect_s') is not None) if k == 'v2B' else '-'} |")
L += ["", "| case | " + " | ".join(nm for _, nm, _ in F) + " | v2 detections /10 |", "|---|---|---|---|---|"]
for c in cases:
    kind, i = c.split("_")
    L.append(f"| {kind} {LEG[int(i)]} | " + " | ".join(f"{sum(not x['fell'] for x in D[k][c])}/{sum(x['recovered'] for x in D[k][c])}" for k, _, _ in F) + f" | {sum(1 for x in D['v2B'][c] if x.get('t_detect_s') is not None)} |")
L += ["", "Reading: these faults are mild for this robot: the plain tripod keeps walking in 11 of 12 cases it is checked on... see table. v2 Tier B neither fixes nor breaks the one hard case (R3 femur lock). It fires on lock faults and never on 30% torque."]
open("docs/V3_fault2.md", "w").write("\n".join(L) + "\n")
print("\n".join(L[:12]))
