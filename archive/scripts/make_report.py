"""Summaries (mean, 95% CI), figures and an auto-generated analysis from results/benchmark.parquet."""
import json
import os
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_json("results/benchmark_partial.jsonl", lines=True)
df.to_parquet("results/benchmark.parquet")
os.makedirs("docs/figures", exist_ok=True)
CTRL = [c for c in ["tripod", "connectome", "ppo"] if c in df.controller.unique()]
LABEL = {"tripod": "Tripod CPG", "connectome": "Connectome-inspired", "ppo": "PPO residual"}
COL = {"tripod": "#94a3b8", "connectome": "#2dd4bf", "ppo": "#f59e0b"}
METRICS = ["distance", "mean_speed", "cot", "roll_rms", "pitch_rms", "latency_ms", "cpu_util", "push_recovery_s", "fault_retained",
           "fault_recovery_s", "t_detect_s", "t_verified_recovery_s"]
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 150})


def ci(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    n = len(x)
    if n == 0: return (np.nan, np.nan, 0)
    m = x.mean()
    h = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return (float(m), float(h), n)


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(max(0, c - h)), float(min(1, c + h)))


summ = {}
for (c, s), g in df.groupby(["controller", "scenario"]):
    d = {m: dict(zip(["mean", "ci95", "n"], ci(g[m]))) for m in METRICS}
    k = int(g.fell.sum()); lo, hi = wilson(k, len(g))
    d["fall_rate"] = {"mean": k / len(g), "ci95_low": lo, "ci95_high": hi, "n": len(g), "falls": k}
    d["final_states"] = g.final_state.value_counts().to_dict() if "final_state" in g else {}
    summ.setdefault(c, {})[s] = d
json.dump(summ, open("results/summary.json", "w"), indent=1, default=float)

TERR = ["flat", "rough1", "rough2", "rough3", "slope10", "slope15", "slope20", "push"]
TERR = [t for t in TERR if t in df.scenario.unique()]
def grouped(ax, scen, metric, ylabel, title, ctrls=CTRL, keyfmt=lambda s: s):
    w = 0.8 / len(ctrls); x = np.arange(len(scen))
    for i, c in enumerate(ctrls):
        m = [summ.get(c, {}).get(s, {}).get(metric, {}).get("mean", np.nan) for s in scen]
        e = [summ.get(c, {}).get(s, {}).get(metric, {}).get("ci95", np.nan) for s in scen]
        ax.bar(x + (i - (len(ctrls) - 1) / 2) * w, m, w, yerr=np.nan_to_num(e), color=COL[c], label=LABEL[c], capsize=2, error_kw={"lw": 0.8})
    ax.set_xticks(x); ax.set_xticklabels([keyfmt(s) for s in scen], rotation=30, ha="right"); ax.set_ylabel(ylabel); ax.set_title(title)

fig, ax = plt.subplots(2, 2, figsize=(12, 7.5))
grouped(ax[0, 0], TERR, "distance", "distance (m, 10 s episode)", "Distance travelled (mean, 95% CI)")
grouped(ax[0, 1], TERR, "cot", "cost of transport (-)", "Cost of transport (lower is better)")
grouped(ax[1, 0], TERR, "roll_rms", "roll RMS (rad)", "Roll RMS")
for i, c in enumerate(CTRL):
    fr = [summ[c][s]["fall_rate"] for s in TERR if s in summ.get(c, {})]
    x = np.arange(len(fr)) + (i - (len(CTRL) - 1) / 2) * 0.8 / len(CTRL)
    ax[1, 1].bar(x, [f["mean"] * 100 for f in fr], 0.8 / len(CTRL), color=COL[c], label=LABEL[c],
                 yerr=[[ (f["mean"] - f["ci95_low"]) * 100 for f in fr], [(f["ci95_high"] - f["mean"]) * 100 for f in fr]], capsize=2, error_kw={"lw": 0.8})
ax[1, 1].set_xticks(range(len(TERR))); ax[1, 1].set_xticklabels(TERR, rotation=30, ha="right"); ax[1, 1].set_ylabel("fall rate (%)"); ax[1, 1].set_title("Fall rate (Wilson 95% CI)")
ax[0, 0].legend(frameon=False, fontsize=8)
fig.suptitle("NeuroWalker arena: terrain and push scenarios (10 seeds per cell, simulation only)", fontsize=12)
fig.tight_layout(); fig.savefig("docs/figures/arena_terrain.png"); plt.close(fig)

FK = ["fault_disable_leg", "fault_lock_joint", "fault_reduce_torque", "fault_sensor_dropout"]
if all(f in df.scenario.unique() for f in FK):
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.4))
    labels = [f.replace("fault_", "").replace("_", " ") for f in FK]
    for j, (suffix, hatch) in enumerate([("", ""), ("+healing", "//")]):
        for i, c in enumerate(CTRL):
            m = [summ[c].get(f + suffix, {}).get("fault_retained", {}).get("mean", np.nan) * 100 for f in FK]
            e = [summ[c].get(f + suffix, {}).get("fault_retained", {}).get("ci95", np.nan) * 100 for f in FK]
            w = 0.8 / (2 * len(CTRL)); x = np.arange(4) + ((j * len(CTRL) + i) - (2 * len(CTRL) - 1) / 2) * w
            ax[0].bar(x, m, w, yerr=np.nan_to_num(e), color=COL[c], hatch=hatch, edgecolor="white", label=f"{LABEL[c]}{' + healing' if suffix else ''}", capsize=2, error_kw={"lw": 0.8})
    ax[0].set_xticks(range(4)); ax[0].set_xticklabels(labels, rotation=15); ax[0].set_ylabel("speed retained (% of pre-fault)"); ax[0].set_title("Retained speed after fault"); ax[0].legend(frameon=False, fontsize=6.5)
    for i, c in enumerate(CTRL):
        w = 0.8 / len(CTRL); x = np.arange(4) + (i - (len(CTRL) - 1) / 2) * w
        ax[1].bar(x, [summ[c].get(f + "+healing", {}).get("t_detect_s", {}).get("mean", np.nan) for f in FK], w, color=COL[c], yerr=np.nan_to_num([summ[c].get(f + "+healing", {}).get("t_detect_s", {}).get("ci95", np.nan) for f in FK]), capsize=2)
        ax[2].bar(x, [summ[c].get(f + "+healing", {}).get("t_verified_recovery_s", {}).get("mean", np.nan) for f in FK], w, color=COL[c], yerr=np.nan_to_num([summ[c].get(f + "+healing", {}).get("t_verified_recovery_s", {}).get("ci95", np.nan) for f in FK]), capsize=2)
    for a, t, yl in [(ax[1], "Time to detect", "s after fault"), (ax[2], "Time to verified recovery (healing runs that verified)", "s after fault")]:
        a.set_xticks(range(4)); a.set_xticklabels(labels, rotation=15); a.set_ylabel(yl); a.set_title(t)
    fig.tight_layout(); fig.savefig("docs/figures/self_healing.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
for k, (m, yl) in enumerate([("latency_ms", "controller latency (ms / 20 ms step)"), ("cpu_util", "CPU utilisation (1.0 = one core)")]):
    vals = [df[df.controller == c][m].mean() for c in CTRL]
    ax[k].bar([LABEL[c] for c in CTRL], vals, color=[COL[c] for c in CTRL]); ax[k].set_ylabel(yl); ax[k].set_yscale("log" if m == "latency_ms" else "linear")
    ax[k].tick_params(axis="x", rotation=15)
fig.suptitle("Compute cost (CPU only; measured in the build sandbox)", fontsize=10); fig.tight_layout(); fig.savefig("docs/figures/compute.png"); plt.close(fig)

# ---- auto analysis: only numbers read from the summary
lines = ["# Benchmark analysis (auto-generated from results/summary.json)", "",
         f"Episodes: {len(df)}; controllers: {', '.join(LABEL[c] for c in CTRL)}; seeds per cell: {int(df.groupby(['controller','scenario']).size().max())}.", "",
         "## Distance (m, mean +- 95% CI) and fall rate", "", "| scenario | " + " | ".join(LABEL[c] for c in CTRL) + " |", "|---|" + "---|" * len(CTRL)]
for s in TERR:
    row = []
    for c in CTRL:
        d = summ.get(c, {}).get(s)
        row.append("n/a" if not d else f"{d['distance']['mean']:.2f} +- {d['distance']['ci95']:.2f} ({d['fall_rate']['falls']}/{d['fall_rate']['n']} falls)")
    lines.append(f"| {s} | " + " | ".join(row) + " |")
lines += ["", "## Where each controller loses", ""]
for s in TERR:
    ds = {c: summ[c][s]["distance"]["mean"] for c in CTRL if s in summ.get(c, {})}
    if len(ds) < 2: continue
    best = max(ds, key=ds.get)
    losers = [f"{LABEL[c]} ({ds[c]:.2f} m vs {ds[best]:.2f} m)" for c in ds if c != best and ds[c] < ds[best] - 0.1]
    fr = {c: summ[c][s]["fall_rate"]["mean"] for c in ds}
    lines.append(f"- **{s}**: best distance {LABEL[best]}. " + (("Behind: " + "; ".join(losers) + ". ") if losers else "No meaningful gap. ") + "Fall rates: " + ", ".join(f"{LABEL[c]} {fr[c]*100:.0f}%" for c in ds) + ".")
if all(f in df.scenario.unique() for f in FK):
    lines += ["", "## Faults: retained speed (% of pre-fault), plain vs +healing", "", "| fault | " + " | ".join(f"{LABEL[c]} / +healing" for c in CTRL) + " |", "|---|" + "---|" * len(CTRL)]
    for f in FK:
        row = []
        for c in CTRL:
            a, b = summ[c].get(f, {}), summ[c].get(f + "+healing", {})
            g = lambda d: "n/a" if not d else f"{d['fault_retained']['mean']*100:.0f}%"
            row.append(f"{g(a)} / {g(b)}")
        lines.append(f"| {f.replace('fault_','')} | " + " | ".join(row) + " |")
    lines += ["", "## Detection and verified recovery (healing runs)", "", "| fault | controller | detect (s, mean) | verified recovery (s, mean) | runs verified / total |", "|---|---|---|---|---|"]
    for f in FK:
        for c in CTRL:
            d = summ[c].get(f + "+healing")
            if d:
                fs = d["final_states"]; ver = d["t_verified_recovery_s"]["n"]
                lines.append(f"| {f.replace('fault_','')} | {LABEL[c]} | {d['t_detect_s']['mean']:.2f} | {d['t_verified_recovery_s']['mean']:.2f} | {ver}/{d['t_detect_s']['n'] if d['t_detect_s']['n'] else 0} (final states {fs}) |")
open("docs/BENCHMARK.md", "w").write("\n".join(lines) + "\n")
print("report ok")
