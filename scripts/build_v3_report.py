"""Assemble docs/RESULTS_V3.md from the generated stage tables. Run after scripts/map_v3.py, stage4_stats_v3.py, plan_v3.py, stage1_v3.py."""
import json
import os

orc = [json.loads(line) for line in open("results/v3_oracle.jsonl")] if os.path.exists("results/v3_oracle.jsonl") else []
LEG = ["R1", "R2", "R3", "L1", "L2", "L3"]
nm = lambda c: "+".join(LEG[int(i)] for i in c[3:].split("_"))
walk = [o for o in orc if o["walks"]]; nowalk = [o for o in orc if not o["walks"]]
read = lambda p: open(p).read().split("\n", 2)[2] if os.path.exists(p) else "(missing)"
s1, mp, s4, plan = (read(p) for p in ("docs/v3_stage1_tables.md", "docs/v3_recovery_map.md", "docs/v3_stage4_tables.md", "docs/v3_video_plan.md"))
head = open("docs/v3_header.md").read()
oracle_txt = (f"Oracle cases finished: {len(orc)}/21. Walks (>=8/10 validation seeds, no fall, >=1.0 m in 10 s): " + (", ".join(nm(o["case"]) for o in walk) or "none") + ". Did not reach the walking criterion within the budget: " + (", ".join(f"{nm(o['case'])} ({o['val_falls']}/10 falls)" for o in nowalk) or "none") + ".")
out = head.replace("{{ORACLE}}", oracle_txt).replace("{{S1}}", s1).replace("{{MAP}}", mp).replace("{{S4}}", s4).replace("{{PLAN}}", plan)
open("docs/RESULTS_V3.md", "w").write(out)
print(oracle_txt)
