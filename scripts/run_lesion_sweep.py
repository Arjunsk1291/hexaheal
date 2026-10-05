"""Lesion sweep: silence each named neuron group at t=2 s on flat ground and measure the behavioural effect."""
import sys
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

from neurowalker.brain import BrainController
from neurowalker.env import HexapodEnv

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
b = BrainController()
rows = []
def episode(group, seed):
    e = HexapodEnv("flat", max_time=10.0, rand=0.1, seed=seed, target_speed=0.25); e.reset(seed=seed)
    b.seed = seed; b.reset(); lesioned = False; xs = []; yaw = []
    while True:
        if group and not lesioned and e.t >= 2.0:
            b.lesion(group); lesioned = True
        _, _, te, tr, info = e.step(b.act(e)); xs.append((e.t, e.data.qpos[0])); yaw.append(e.euler()[2])
        if te or tr: break
    xs = np.array(xs); post = xs[xs[:, 0] >= 2.0]; pre = xs[(xs[:, 0] >= 1.0) & (xs[:, 0] < 2.0)]
    v_pre = (pre[-1, 1] - pre[0, 1]) / (pre[-1, 0] - pre[0, 0]); v_post = (post[-1, 1] - post[0, 1]) / (post[-1, 0] - post[0, 0])
    b.unlesion_all()
    return dict(group=group or "none", seed=seed, n_neurons=int(len(b.named_groups[group])) if group else 0, fell=bool(e.fell), speed_pre=v_pre, speed_post=v_post,
                speed_change_pct=100 * (v_post - v_pre) / max(v_pre, 1e-6), final_yaw_rad=float(yaw[-1]), y_drift=float(abs(e.data.qpos[1])))
for g in [None] + sorted(b.named_groups):
    for s in range(N):
        rows.append(episode(g, s))
df = pd.DataFrame(rows); df.to_parquet("results/lesion_sweep.parquet")
agg = df.groupby("group").agg(n_neurons=("n_neurons", "first"), speed_change_pct=("speed_change_pct", "mean"), speed_change_sd=("speed_change_pct", "std"),
                              abs_yaw=("final_yaw_rad", lambda x: float(np.mean(np.abs(x)))), falls=("fell", "sum"), n=("seed", "count")).sort_values("speed_change_pct")
agg.to_json("results/lesion_sweep_summary.json", orient="index", indent=1)
fig, ax = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
y = np.arange(len(agg))
ax[0].barh(y, agg.speed_change_pct, xerr=agg.speed_change_sd.fillna(0), color="#2dd4bf"); ax[0].set_yticks(y); ax[0].set_yticklabels(agg.index, fontsize=7)
ax[0].set_xlabel("speed change after lesion at t=2 s (%)"); ax[0].set_title("Effect on forward speed")
ax[1].barh(y, agg.abs_yaw, color="#f59e0b"); ax[1].set_xlabel("|final heading| (rad)"); ax[1].set_title("Effect on heading")
fig.suptitle(f"Lesion sweep ({N} seeds per group, flat ground; random_central_500 is the size-matched control)", fontsize=10); fig.tight_layout(); fig.savefig("docs/figures/lesion_sweep.png", dpi=150)
print(agg.round(2).to_string())
