"""HexaHeal Stage 6: survival heatmap (21 cases x controllers, oracle row on top). Reads results/hh_final_*_0-9.jsonl and the Stage 2 oracle summary. Simulation only."""
import json
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "scripts")
from hh_common import CASES

from neurowalker.hh_eval import case_name

CT = [("tripod", "plain\ntripod"), ("tuned", "tuned\ntripod"), ("v1", "tuned +\nhealing v1"), ("v2A", "v2 Tier A\n(library)"), ("v2B", "v2 Tier B\n(online)"), ("ppo", "PPO\nreference")]
orc = json.load(open("results/hh_stage2_oracle_summary.json"))["cases"]
M = np.zeros((len(CASES), 1 + len(CT)))
for i, c in enumerate(CASES): M[i, 0] = orc[c]["walk_seeds"]
for j, (k, _) in enumerate(CT):
    d = {}
    for line in open(f"results/hh_final_{k}_0-9.jsonl"):
        r = json.loads(line); d.setdefault(r["case"], []).append(not r["fell"])
    for i, c in enumerate(CASES): M[i, j + 1] = sum(d[c])
fig, ax = plt.subplots(figsize=(8.5, 9))
im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=10, aspect="auto")
ax.set_xticks(range(M.shape[1])); ax.set_xticklabels(["oracle\n(upper bound)"] + [n for _, n in CT], fontsize=8)
ax.xaxis.tick_top(); ax.set_yticks(range(len(CASES))); ax.set_yticklabels([case_name(c) for c in CASES], fontsize=8)
for i in range(M.shape[0]):
    for j in range(M.shape[1]): ax.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=8)
ax.axvline(0.5, color="k", lw=2)
fig.colorbar(im, ax=ax, fraction=0.03, label="seeds (of 10) surviving; oracle: seeds that walk")
fig.text(0.5, 0.01, "MuJoCo simulation, seeds 0-9, leg(s) disabled at 4 s, 14 s. Oracle: fault from t=0, 15 s (upper bound).", ha="center", fontsize=8)
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig("docs/media_hh/survival_heatmap.png", dpi=150)
print("ok")
