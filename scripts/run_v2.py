# ruff: noqa: E402
"""v2 experiment runner (resumable, one JSON line per episode).
  python scripts/run_v2.py ablation [seeds]   variants x 8 cells (Stage 3)
  python scripts/run_v2.py stage2   [seeds]   tripod/connectome/ppo x sequential + healthy cells (Stage 2)
  python scripts/run_v2.py tuned    [seeds]   tuned tripod (gains from results/tuned_tripod_tuning.json) on all cells
  python scripts/run_v2.py pposeeds [seeds]   PPO training seeds 1-4 (models/ppo_residual_s*.zip) on all cells
  python scripts/run_v2.py rebench  [seeds]   tripod/connectome/ppo x the original 16+ cells re-run with fixed healing
seeds default 0-9 (final evaluation). Pass e.g. 100-109 for tuning/debugging; output file name carries the seed range."""
try:
    import torch  # noqa: F401
    import torch._dynamo  # noqa: F401
except ImportError:
    pass
import json
import os
import sys

import numpy as np

sys.path.insert(0, "scripts")
from make_media import make_ctrl
from neurowalker.ablation import VARIANTS, make_variant
from neurowalker.benchmark import SCENARIOS, run_one

ABL_CELLS = ["flat", "rough1", "rough3", "push", "slope10", "fault_disable_leg+healing", "fault_lock_joint+healing", "fault_sensor_dropout+healing"]
S2_CELLS = ["fault_sequential", "fault_sequential+healing", "healthy+healing"]
mode = sys.argv[1]
a, b = (sys.argv[2].split("-") if len(sys.argv) > 2 else ("0", "9"))
seeds = list(range(int(a), int(b) + 1))
path = f"results/v2_{mode}_{a}-{b}.jsonl"
done = set()
if os.path.exists(path):
    for line in open(path):
        r = json.loads(line); done.add((r["controller"], r["scenario"], r["seed"]))
if mode == "ablation":
    plan = [(v, ABL_CELLS) for v in VARIANTS]; build = make_variant
elif mode == "stage2":
    plan = [(c, S2_CELLS) for c in ("tripod", "connectome", "ppo")]; build = make_ctrl
elif mode == "mlp":
    plan = [("mlp", ABL_CELLS)]; build = make_variant
elif mode == "tuned":
    from neurowalker.tuned import TunedTripod
    best = json.load(open("results/tuned_tripod_tuning.json"))["best"]  # gains chosen on seeds 100-109 only
    plan = [("tuned_tripod", list(SCENARIOS) + S2_CELLS)]; build = lambda n: TunedTripod(best["kp"], best["kr"], best["ks"])
elif mode == "pposeeds":
    from neurowalker.rl import PPOController
    plan = [(f"ppo_s{k}", list(SCENARIOS)) for k in (1, 2, 3, 4) if os.path.exists(f"models/ppo_residual_s{k}.zip")]
    build = lambda n: PPOController(f"models/ppo_residual_s{n.split('_s')[1]}.zip")
else:
    plan = [(c, list(SCENARIOS)) for c in ("tripod", "connectome", "ppo")]; build = make_ctrl
for name, cells in plan:
    todo = [(sc, sd) for sc in cells for sd in seeds if (name, sc, sd) not in done]
    if not todo:
        continue
    ctrl = build(name)
    for sc, sd in todo:
        r, _ = run_one(ctrl, name, sc, sd)
        nud = np.array(getattr(ctrl, "nudges", [])) if hasattr(ctrl, "nudges") else np.zeros((0, 4))
        if len(nud):
            r.update(nudge_speed_gain_absdev=float(np.mean(np.abs(nud[:, 0] - 1))), nudge_freq_scale_absdev=float(np.mean(np.abs(nud[:, 1] - 1))),
                     nudge_turn_abs=float(np.mean(np.abs(nud[:, 2]))), nudge_stance_abs=float(np.mean(np.abs(nud[:, 3]))))
        with open(path, "a") as f:
            f.write(json.dumps(r, default=float) + "\n")
        print(name, sc, sd, "fell", r["fell"], "dist", round(r["distance"], 3), flush=True)
print("DONE", mode, flush=True)
