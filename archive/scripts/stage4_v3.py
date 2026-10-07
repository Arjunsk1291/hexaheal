"""V3 Stage 4: hybrid controller = tuned-tripod pitch feedback + healing layer + connectome speed/freq/turn nudges (gated off after the first fault suspicion).
Modes:  tune  SEEDS  -> results/v3_stage4_tune_<a>-<b>.jsonl   (variants: scale/clip choices; seeds 100-109 ONLY)
        final SEEDS VARIANT -> results/v3_stage4_final_<a>-<b>.jsonl (the variant chosen on tuning seeds; seeds 0-9)
Healing wraps the hybrid in every cell (healthy cells included), to compare with tuned_tripod+healing."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from neurowalker.benchmark import run_one, scenario_spec
from neurowalker.healing import HealingController
from neurowalker.v3 import HybridBrain

mode, rng_ = sys.argv[1], sys.argv[2]
a, b = rng_.split("-"); seeds = range(int(a), int(b) + 1)
VARIANTS = {"h_full": dict(scale=(1, 1, 1)), "h_half": dict(scale=(0.5, 0.5, 1)), "h_turn": dict(scale=(0, 0, 1)), "h_speed": dict(scale=(1, 1, 0)), "h_clip": dict(scale=(1, 1, 1), clip=(0.15, 0.1, 0.1)), "h_none": dict(scale=(0, 0, 0)), "h_half_pg": dict(scale=(0.5, 0.5, 1), pitch_gate=0.10), "h_full_pg": dict(scale=(1, 1, 1), pitch_gate=0.10), "h_half_pg2": dict(scale=(0.5, 0.5, 1), pitch_gate=0.06)}
TUNE_CELLS = ["flat", "rough3", "push", "slope15", "fault_disable_leg+healing", "fault_lock_joint+healing"]
FINAL_CELLS = ["flat", "rough1", "rough3", "push", "slope10", "slope15", "slope20", "fault_disable_leg+healing", "fault_lock_joint+healing", "fault_sensor_dropout+healing", "fault_sequential+healing", "healthy+healing"]
names = (sys.argv[3:] or list(VARIANTS)) if mode == "tune" else [sys.argv[3]]
cells = TUNE_CELLS if mode == "tune" else FINAL_CELLS
path = f"results/v3_stage4_{mode}_{a}-{b}.jsonl"
done = set()
if os.path.exists(path):
    for line in open(path):
        r = json.loads(line); done.add((r["variant"], r["scenario"], r["seed"]))
for n in names:
    for sc in cells:
        for sd in seeds:
            if (n, sc, sd) in done: continue
            hb = HybridBrain(**VARIANTS[n]); sp = scenario_spec(sc)
            ctrl = hb if sp["heal"] else HealingController(hb, terrain=sp["terrain"], seed=sd)
            r, _ = run_one(ctrl, "hybrid", sc, sd); r["variant"] = n
            with open(path, "a") as f: f.write(json.dumps(r, default=float) + "\n")
            print(n, sc, sd, "fell", r["fell"], "t_end", round(r["t_end"], 2), "dist", round(r["distance"], 3), flush=True)
print("DONE")
