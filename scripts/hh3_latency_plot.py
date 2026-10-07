"""HexaHeal v3 Stage 3: recovered fraction vs response delay. Reads results/v3/hh3_latency_v2_config_base_<delay>.jsonl (seeds 0-9, healing v2 Tier B, frozen config) and the Stage 1 plain-tripod rows for the same 10 cases.
Writes docs/media_v3/latency_curve.png, docs/V3_latency.md, results/v3/latency_stats.json. Simulation only."""
import json
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from neurowalker.hh_eval import case_name

DELAYS = [0.0, 0.2, 0.4, 0.7, 1.0, 1.5]
CASES = [f"dl_{i}" for i in range(6)] + ["dl_0_4", "dl_0_5", "dl_1_3", "dl_1_4"]


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - h) / d), min(1.0, (c + h) / d)


R = {}
for d in DELAYS:
    p = f"results/v3/hh3_latency_v2_config_base_{d:.1f}.jsonl"
    R[d] = [json.loads(line) for line in open(p)] if os.path.exists(p) else []
R = {d: r for d, r in R.items() if len(r) == 100}
tri = [r for r in map(json.loads, open("results/v3/hh3_final_tripod_0-9.jsonl")) if r["case"] in CASES]
det = [r["t_detect_s"] for r in R.get(0.0, []) if r.get("t_detect_s") is not None and r["t_detect_s"] >= 0]
t_det = float(np.mean(det)) if det else float("nan")
out = {"delays": list(R), "mean_detect_s_delay0": t_det, "pooled": {}, "per_case": {}, "tripod_pooled_recovered": sum(r["recovered"] for r in tri), "tripod_pooled_upright": sum(not r["fell"] for r in tri)}
ds = sorted(R)
rec = [sum(r["recovered"] for r in R[d]) for d in ds]
upr = [sum(not r["fell"] for r in R[d]) for d in ds]
for d, a, b in zip(ds, rec, upr):
    out["pooled"][str(d)] = {"recovered": a, "upright": b, "n": 100, "rec_wilson": wilson(a, 100), "upr_wilson": wilson(b, 100)}
fig, ax = plt.subplots(figsize=(9, 5.2))
lo = [wilson(a, 100)[0] for a in rec]; hi = [wilson(a, 100)[1] for a in rec]
ax.fill_between(ds, lo, hi, color="#2a9d8f", alpha=0.25)
ax.plot(ds, [a / 100 for a in rec], "o-", color="#2a9d8f", lw=2.5, label="healing v2 Tier B: recovered (walking)")
ax.plot(ds, [b / 100 for b in upr], "s--", color="#8d99ae", lw=1.5, label="healing v2 Tier B: upright (not fallen)")
ax.axhline(out["tripod_pooled_recovered"] / 100, color="#e76f51", lw=2, label=f"plain tripod: recovered ({out['tripod_pooled_recovered']}/100, no healing, delay does not apply)")
ax.axhline(0.7, color="k", lw=0.6, ls=":")
ax.axvline(t_det, color="#e9c46a", lw=2); ax.text(t_det + 0.02, 0.97, f"measured detection {t_det:.2f} s", color="#8a6d00", va="top")
ax.set_xlabel("artificial response delay before healing starts (s)"); ax.set_ylabel("fraction of runs (10 faults x 10 seeds)"); ax.set_ylim(0, 1.02)
ax.set_title("How fast must a hexapod heal? (MuJoCo simulation, seeds 0-9, Wilson 95%)"); ax.legend(loc="center right", fontsize=8)
os.makedirs("docs/media_v3", exist_ok=True); fig.tight_layout(); fig.savefig("docs/media_v3/latency_curve.png", dpi=150)
L = ["# HexaHeal v3 Stage 3: response-delay sweep (MEASURED; MuJoCo simulation; seeds 0-9)", "",
     "Faults: 6 single legs + R1+L2, R1+L3, R2+L1, R2+L2 (fixed rule in docs/PREREGISTRATION_V3.md; chosen from tuning-seed results, so they are cases where healing can work). Delay = time the diagnosis is held back after it is ready; the robot keeps its current gait meanwhile. Pooled over 10 cases x 10 seeds = 100 runs per delay. Plain tripod does not heal, so it is one flat reference.", "",
     f"Measured detection time (mean, delay 0): {t_det:.2f} s.", "", "| delay (s) | recovered /100 [Wilson 95%] | upright /100 [Wilson 95%] |", "|---|---|---|"]
for d in ds:
    p = out["pooled"][str(d)]
    L.append(f"| {d:.1f} | {p['recovered']} [{p['rec_wilson'][0]:.2f}, {p['rec_wilson'][1]:.2f}] | {p['upright']} [{p['upr_wilson'][0]:.2f}, {p['upr_wilson'][1]:.2f}] |")
L.append(f"| plain tripod (no healing) | {out['tripod_pooled_recovered']} | {out['tripod_pooled_upright']} |")
L += ["", "Per case, recovered runs of 10 by delay " + ", ".join(f"{d:.1f}" for d in ds) + " s:", "", "| case | " + " | ".join(f"{d:.1f} s" for d in ds) + " | plain tripod |", "|---|" + "---|" * (len(ds) + 1)]
for c in CASES:
    row = [sum(r["recovered"] for r in R[d] if r["case"] == c) for d in ds]
    out["per_case"][c] = row
    L.append(f"| {case_name(c)} | " + " | ".join(map(str, row)) + f" | {sum(r['recovered'] for r in tri if r['case'] == c)} |")
tol = [d for d, a in zip(ds, rec) if a / 100 >= 0.7]
out["tolerable_delay_grid_point"] = max(tol) if tol else None
L += ["", f"Tolerable delay (largest swept delay with pooled recovered fraction >= 0.7, no interpolation): **{out['tolerable_delay_grid_point']} s**" if tol else "No swept delay reaches a pooled recovered fraction of 0.7 (even at delay 0).", "",
      "GUESS (not tested): conclusions for other faults, terrain, speeds or hardware are UNKNOWN."]
open("docs/V3_latency.md", "w").write("\n".join(L) + "\n")
json.dump(out, open("results/v3/latency_stats.json", "w"), indent=1)
print("\n".join(L[:20]))
