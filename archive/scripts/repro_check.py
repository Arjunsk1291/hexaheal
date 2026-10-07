# ruff: noqa: E402
"""Stage 1 reproducibility check: same cell (connectome, disable_leg+healing, seed 8) repeated, idle and under CPU load.
Outcomes must be bit-identical. Writes results/repro_check.json."""
try:
    import torch  # noqa: F401
    import torch._dynamo  # noqa: F401
except ImportError:
    pass
import json
import subprocess
import sys

sys.path.insert(0, "scripts")
from make_media import make_ctrl
from neurowalker.benchmark import run_one

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 8
ctrl = make_ctrl("connectome")
out = {"seed": SEED, "cell": "connectome fault_disable_leg+healing", "runs": []}
def go(tag):
    r, log = run_one(ctrl, "connectome", "fault_disable_leg+healing", SEED)
    keep = {k: r[k] for k in ("fell", "t_end", "distance", "fault_pre_speed", "fault_post_speed", "t_detect_s", "t_verified_recovery_s", "final_state")}
    keep["log_states"] = [(e["t"], e["to"]) for e in log]; keep["tag"] = tag
    out["runs"].append(keep); print(keep, flush=True)
for i in range(3): go(f"idle{i}")
burn = subprocess.Popen([sys.executable, "-c", "while True: pass"])
try:
    for i in range(3): go(f"load{i}")
finally:
    burn.kill()
sig = [json.dumps({k: v for k, v in r.items() if k != "tag"}, sort_keys=True) for r in out["runs"]]
out["all_identical"] = len(set(sig)) == 1
json.dump(out, open("results/repro_check.json", "w"), indent=1, default=float)
print("ALL IDENTICAL:", out["all_identical"], flush=True)
