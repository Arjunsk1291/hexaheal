"""HexaHeal v4 Stage 3 figures (vector SVG + PNG). Data: results/v3, results/v4. Simulation only."""
import json
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, "scripts")
from hh_common import CASES

from neurowalker.hh_eval import case_name

BG, FG, DIM, TEAL, ALERT, PANEL = "#0d1117", "#e6edf3", "#8b949e", "#2dd4bf", "#ff5d5d", "#161b22"
plt.rcParams.update({"font.family": "Noto Sans", "svg.fonttype": "none", "text.color": FG, "axes.labelcolor": FG, "xtick.color": DIM, "ytick.color": DIM,
                     "axes.edgecolor": DIM, "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "font.size": 11})
OUT = "docs/media_v4/"
TAG = "Simulation only (MuJoCo, seeds 0-9)"


def save(fig, name):
    fig.savefig(OUT + name + ".svg"); fig.savefig(OUT + name + ".png", dpi=200); plt.close(fig)


def load(f):
    R = {}
    for line in open(f):
        r = json.loads(line); R.setdefault(r["case"], {})[r["seed"]] = r
    return R


# 1. latency curve
d = json.load(open("results/v3/latency_stats.json"))
ds = d["delays"]; P = d["pooled"]
fig, ax = plt.subplots(figsize=(9, 5.4))
x = ds; rec = [P[str(t)]["recovered"] / 100 for t in ds]; upr = [P[str(t)]["upright"] / 100 for t in ds]
lo = [P[str(t)]["rec_wilson"][0] for t in ds]; hi = [P[str(t)]["rec_wilson"][1] for t in ds]
ax.fill_between(x, lo, hi, color=TEAL, alpha=0.18, lw=0)
ax.plot(x, rec, "o-", color=TEAL, lw=2.6, label="recovered (walking)")
ax.plot(x, upr, "o--", color=DIM, lw=1.8, label="upright (no fall)")
ax.plot([0, 1.5], [0, 0], "-", color=FG, lw=1.6, label="plain tripod (recovered: 0)")
T_DET = d["mean_detect_s_delay0"]
ax.axvline(T_DET, color=ALERT, lw=1.4); ax.text(T_DET + 0.015, 0.96, f"detection {T_DET:.2f} s", color=ALERT, fontsize=10, va="top")
ax.set_xlabel("response delay after diagnosis (s)"); ax.set_ylabel("share of runs"); ax.set_ylim(-0.03, 1.0); ax.set_yticks(np.arange(0, 1.01, 0.25)); ax.set_yticklabels([f"{int(v*100)}%" for v in np.arange(0, 1.01, 0.25)])
ax.set_title("How long can the robot wait? Recovered share falls from 55% to 15%", loc="left", color=FG, fontsize=13)
ax.grid(color="#21262d", lw=0.8); [ax.spines[s].set_visible(False) for s in ("top", "right")]
ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.88))
fig.text(0.01, 0.01, f"{TAG}. 10 cases x 10 seeds = 100 runs per delay; cases chosen from tuning-seed results where healing can work (stated bias). 95% Wilson band.", color=DIM, fontsize=7)
fig.subplots_adjust(bottom=0.13); save(fig, "latency_curve")

# 2. recovered matrix
F = {"oracle (knows fault)": "results/v3/hh3_oracle_0-9.jsonl", "final controller (Tier B)": "results/v3/hh3_final_v2B_0-9.jsonl",
     "Tier B+ (not adopted)": "results/v4/hh4_final_v2Bplus_0-9.jsonl", "plain tripod": "results/v3/hh3_final_tripod_0-9.jsonl"}
D = {k: load(f) for k, f in F.items()}
fig, ax = plt.subplots(figsize=(13, 3.9)); ax.set_xlim(0, 21); ax.set_ylim(0, len(D) ); ax.invert_yaxis(); ax.axis("off")
tot = {}
for i, (k, R) in enumerate(D.items()):
    n = 0
    for j, c in enumerate(CASES):
        rc = sum(bool(R[c][s]["recovered"]) for s in range(10)); up = sum(not R[c][s]["fell"] for s in range(10))
        col = TEAL if rc >= 7 else (PANEL if up >= 7 else ALERT)
        n += rc >= 7
        ax.add_patch(FancyBboxPatch((j + 0.06, i + 0.08), 0.88, 0.84, boxstyle="round,pad=0,rounding_size=0.12", fc=col, ec="#30363d" if col == PANEL else col, lw=1))
        ax.text(j + 0.5, i + 0.5, str(rc), ha="center", va="center", fontsize=9, color=BG if col == TEAL else FG)
    tot[k] = n
    ax.text(-0.15, i + 0.5, f"{k}  ({n}/21)", ha="right", va="center", fontsize=10.5, color=FG)
for j, c in enumerate(CASES): ax.text(j + 0.5, -0.12, case_name(c), ha="center", va="bottom", fontsize=8, color=DIM, rotation=60)
fig.text(0.01, 0.07, "Cell = recovered runs of 10 seeds. Teal: recovered in at least 7 of 10. Dark: upright, not recovered. Red: falls in more than 3 of 10.", color=DIM, fontsize=9)
fig.text(0.01, 0.02, f"{TAG}. Recovered = no fall and at least 0.125 m/s over the last 8 s. Oracle row: fault from t=0, 15 s run (different conditions).", color=DIM, fontsize=9)
fig.suptitle("Recovered cases: 21 fault cases x 10 seeds", x=0.01, ha="left", color=FG, fontsize=14)
fig.subplots_adjust(left=0.2, top=0.78, bottom=0.14); save(fig, "recovered_matrix"); print(tot)

# 3. architecture
fig, ax = plt.subplots(figsize=(13, 3.6)); ax.set_xlim(0, 13); ax.set_ylim(0, 3.6); ax.axis("off")
steps = [("FAULT", "leg torque lost\nat t = 4 s", ALERT), ("DETECT", "failed-leg set\nin about 0.34 s", TEAL), ("STAND", "hold still,\nrobot stays upright", TEAL), ("RE-PLAN", "CMA-ES search,\n60 gait trials", TEAL), ("GAIT SWITCH", "new gait starts\n~5 s after fault", TEAL)]
for i, (t, s, c) in enumerate(steps):
    x0 = 0.3 + i * 2.55
    ax.add_patch(FancyBboxPatch((x0, 1.1), 2.1, 1.5, boxstyle="round,pad=0,rounding_size=0.15", fc=PANEL, ec=c, lw=2))
    ax.text(x0 + 1.05, 2.25, t, ha="center", va="center", fontsize=12, color=c, weight="bold"); ax.text(x0 + 1.05, 1.6, s, ha="center", va="center", fontsize=9.5, color=FG)
    if i < 4: ax.annotate("", xy=(x0 + 2.5, 1.85), xytext=(x0 + 2.12, 1.85), arrowprops=dict(arrowstyle="-|>", color=DIM, lw=1.6))
ax.text(0.3, 3.3, "Fault response pipeline", fontsize=14, color=FG, weight="bold")
ax.text(0.3, 0.55, "Standing lasts a fixed 4.6 s of simulated time in every planning run (MEASURED). The offline oracle skips detect, stand and re-plan: it knows the fault from t = 0.", color=DIM, fontsize=9)
ax.text(0.3, 0.2, TAG + ". No hardware.", color=DIM, fontsize=9)
save(fig, "architecture")
