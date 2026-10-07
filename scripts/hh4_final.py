"""HexaHeal v4: Tier B (frozen v3 config, re-run only to log stand-still diagnostics) and Tier B+ (warm start from the nearest LEAVE-ONE-CASE-OUT library gait). Seeds 0-9 only (or --smoke: tuning seeds 100-101, bug check only).
Usage: hh4_final.py v2B|v2Bplus [smoke] -> results/v4/hh4_final_<name>_0-9.jsonl (resumable). Pre-registration: docs/PREREGISTRATION_V4.md."""
import json
import os
import sys

sys.path.insert(0, "scripts")
from hh_common import CASES, library, make

from neurowalker.hh_eval import case_legs, run_episode

name = sys.argv[1]
smoke = len(sys.argv) > 2 and sys.argv[2] == "smoke"
cfg = json.load(open("results/v3/v2_config_final.json"))["B"]
LIB = library()
mirror = lambda S: tuple(sorted((i + 3) % 6 for i in S))  # noqa: E731
seeds = range(100, 102) if smoke else range(10)
path = f"results/v4/hh4_{'smoke' if smoke else 'final'}_{name}_0-9.jsonl"
done = {(json.loads(line)["case"], json.loads(line)["seed"]) for line in open(path)} if os.path.exists(path) else set()
for case in CASES:
    for sd in seeds:
        if (case, sd) in done: continue
        c = make("B", **cfg)
        if name == "v2Bplus":
            S = tuple(sorted(case_legs(case)))
            c.warm_library = LIB; c.exclude = {S, mirror(S)}
        r = run_episode(c, case, sd)
        r["controller"] = name
        if name == "v2Bplus": r["warm_from"] = getattr(c, "info_warm", None)
        with open(path, "a") as f: f.write(json.dumps(r, default=float) + "\n")
    print(name, case, flush=True)
print("DONE", name)
