"""V3 Stage 5: video evidence plan (NO rendering). Fixed selection rule: all seeds 0-9 of each candidate cell, never a best-of subset.
Reads existing result files only; writes docs/v3_video_plan.md."""
import glob

import pandas as pd

df = pd.concat([pd.read_json(f, lines=True) for f in sorted(glob.glob("results/v2_*_0-9.jsonl")) + sorted(glob.glob("results/v3_stage4_final_0-9.jsonl"))]).fillna({"variant": ""})
df = df.drop_duplicates(["controller", "scenario", "seed", "variant"], keep="last")
if "variant" not in df: df["variant"] = ""
md = ["# V3 Stage 5: video evidence plan (plan only, nothing rendered)", "",
      "Selection rule (fixed in advance): every seed 0-9 of a chosen cell is shown, in seed order, no cherry-picking. A 10-robot grid = the same cell, 10 seeds, one controller per grid; two grids side by side compare controllers. Each row below is the recorded outcome for that seed so you can check it before anything is rendered. T = time of fall in s (episode length 14 s unless stated); OK = no fall.", ""]


def grid(title, ctrl, scen, variant=""):
    g = df[(df.controller == ctrl) & (df.scenario == scen) & (df.variant == variant)].sort_values("seed")
    if len(g) != 10: return [f"### {title}: data for {ctrl} / {scen} {variant} not available (n={len(g)})", ""]
    cells = ["T=%.2f" % r.t_end if r.fell else "OK" for r in g.itertuples()]
    return [f"### {title}", f"- {ctrl} {variant} / {scen}: falls {int(g.fell.sum())}/10, mean distance {g.distance.mean():.2f} m", "- per seed 0-9: " + ", ".join(f"s{i}:{c}" for i, c in zip(g.seed, cells)), ""]


md += ["## Candidate A (clearest single story): single disabled leg, plain tripod, with vs without healing", ""]
md += grid("A1 without healing", "tripod", "fault_disable_leg") + grid("A2 with healing", "tripod", "fault_disable_leg+healing")
md += ["## Candidate B: same cell, connectome (healing does NOT help it)", ""] + grid("B1 connectome no healing", "connectome", "fault_disable_leg") + grid("B2 connectome with healing", "connectome", "fault_disable_leg+healing")
md += ["## Candidate C: tuned tripod single leg", ""] + grid("C1 tuned no healing", "tuned_tripod", "fault_disable_leg") + grid("C2 tuned with healing", "tuned_tripod", "fault_disable_leg+healing")
md += ["## Candidate D: 15 degree slope, connectome vs tuned tripod", ""] + grid("D1 connectome slope15", "connectome", "slope15") + grid("D2 tuned tripod slope15", "tuned_tripod", "slope15")
md += ["## Candidate E: hybrid on the same single-leg cell and slope", ""] + grid("E1 hybrid disable_leg+healing", "hybrid", "fault_disable_leg+healing", "h_half_pg") + grid("E2 hybrid slope15", "hybrid", "slope15", "h_half_pg")
md += ["## Recommendation", "",
       "- Best 10-robot comparison on current evidence: A1 vs A2 (the only cell where healing visibly changes the plain tripod: 10/10 falls to 3/10). It must be described as 'healing helps the plain tripod on one leg loss' and NOT 'healing helps the connectome' (B2 falls 10/10) and NOT generally (Stage 3 map: it hurts in several double-fault cases).",
       "- D1 vs D2 shows the simple tuned tripod beating the connectome on slopes; it is an honest-negative clip, not a promotional one.",
       "- Anything about the hybrid waits for the final Stage 4 table (docs/v3_stage4_tables.md).",
       "- Every clip must carry an on-screen label: 'MuJoCo simulation, connectome-inspired controller, seeds 0-9 shown in order'. No claims about real hardware, ROS 2 or Docker."]
open("docs/v3_video_plan.md", "w").write("\n".join(md) + "\n")
print("\n".join(md[:24]))
