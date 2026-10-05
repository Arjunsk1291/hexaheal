"""V3 Stage 2: why does the connectome fall ~6.5 s after a disabled leg (fault at 4 s) even with healing?
Variants on fault_disable_leg+healing (run on tuning seeds 100-109 first, then final seeds 0-9):
  base      healing + unmodified connectome nudges (the v2 cell)
  a_off     healed gait + connectome nudges disabled (scale 0)
  b_half    nudges scaled 0.5
  b_clip    nudges clipped to |dev| <= (0.15 speed, 0.1 freq, 0.1 turn, 0.05 stance)
  c_search  CMA-ES run on the real connectome-driven controller (nudges included)
  tripod    plain tripod + healing (reference)
Usage: python scripts/stage2_v3.py SEEDRANGE [variants...]  -> results/v3_stage2_<a>-<b>.jsonl (resumable)."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from neurowalker.benchmark import run_one
from neurowalker.healing import HealingController  # noqa: F401
from neurowalker.tripod import TripodController
from neurowalker.v3 import ScaledBrain

a, b = sys.argv[1].split("-"); seeds = range(int(a), int(b) + 1)
names = sys.argv[2:] or ["base", "a_off", "b_half", "b_clip", "c_search", "tripod"]
path = f"results/v3_stage2_{a}-{b}.jsonl"
done = set()
if os.path.exists(path):
    for line in open(path):
        r = json.loads(line); done.add((r["controller"], r["seed"]))


def make(n):
    if n == "tripod": return TripodController(), None
    if n == "base": return ScaledBrain(1.0), None
    if n == "a_off": return ScaledBrain(0.0), None
    if n == "b_half": return ScaledBrain(0.5), None
    if n == "b_clip": return ScaledBrain(1.0, clip=(0.15, 0.1, 0.1, 0.05)), None
    if n == "only_speedfreq": return ScaledBrain([1, 1, 0, 0]), None
    if n == "only_turn": return ScaledBrain([0, 0, 1, 0]), None
    if n == "only_stance": return ScaledBrain([0, 0, 0, 1]), None
    if n == "c_search": return ScaledBrain(1.0), "search"


import neurowalker.benchmark as bm

for n in names:
    for sd in seeds:
        if (n, sd) in done: continue
        ctrl, mode = make(n)
        if mode == "search":
            orig = bm.HealingController
            bm.HealingController = lambda base, **kw: orig(base, search_ctrl=ScaledBrain(1.0), **kw)
        r, _log = run_one(ctrl, n, "fault_disable_leg+healing", sd)
        if mode == "search": bm.HealingController = orig
        with open(path, "a") as f: f.write(json.dumps(r, default=float) + "\n")
        print(n, sd, "fell", r["fell"], "t_end", round(r["t_end"], 2), "dist", round(r["distance"], 3), "verified", round(r.get("t_verified_recovery_s", float("nan")), 2), flush=True)
print("DONE")
