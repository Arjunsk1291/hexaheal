"""HexaHeal Stage 5 statistics from results/hh_final_*_0-9.jsonl (seeds 0-9). Writes docs/hh_tables.md and results/hh_stats.json."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "scripts")
from hh_common import CASES

from neurowalker.hh_eval import case_name

CTRL = [("tripod", "plain tripod"), ("tuned", "tuned tripod"), ("v1", "tuned + healing v1"), ("v2A", "healing v2 Tier A (library)"), ("v2B", "healing v2 Tier B (online)"), ("ppo", "PPO reference")]
R = {}
for c, _ in CTRL:
    p = f"results/hh_final_{c}_0-9.jsonl"
    if os.path.exists(p):
        R[c] = {}
        for line in open(p):
            r = json.loads(line); R[c].setdefault(r["case"], {})[r["seed"]] = r
oracle = json.load(open("results/hh_stage2_oracle_summary.json"))["cases"]


def wilson(k, n=10, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def surv(c):
    return np.array([[not R[c][case][s]["fell"] for s in range(10)] for case in CASES])  # 21 x 10


def nsurv(m): return int((m.sum(1) >= 7).sum())


S = {c: surv(c) for c in R}
N = {c: nsurv(m) for c, m in S.items()}
orc_n = sum(v["holds_up"] for v in oracle.values())
rng = np.random.default_rng(0)
idx = rng.integers(0, 10, (10000, 10))


def boot(a, b):
    d = np.array([nsurv(S[a][:, i]) - nsurv(S[b][:, i]) for i in idx])
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


out = {"N_surv": N, "oracle_hold_up": orc_n, "gap": {c: orc_n - n for c, n in N.items()}}
L = ["# HexaHeal Stage 5 results (MEASURED; MuJoCo simulation, 2 vCPU sandbox; seeds 0-9; fault at 4 s, flat, 14 s)", "",
     "Primary metric: N_surv = number of the 21 leg-loss cases survived (no fall) on at least 7 of 10 seeds. Oracle = Stage 2 gaits, faults from t=0, 15 s, an upper bound (different conditions, never counted as a controller).", "",
     "| controller | N_surv (of 21) | gap to oracle (" + str(orc_n) + " - N_surv) | total survivors /210 |", "|---|---|---|---|"]
for c, nm in CTRL:
    if c in R: L.append(f"| {nm} | {N[c]} | {orc_n - N[c]} | {int(S[c].sum())} |")
L.append(f"| oracle (upper bound) | {orc_n} | 0 | {sum(v['walk_seeds'] for v in oracle.values())} (walk criterion) |")
L += ["", "## Paired bootstrap (10,000 resamples of the 10 seeds jointly across all cases), difference in N_surv", "", "| comparison | diff | 95% CI |", "|---|---|---|"]
for a, b in (("v2B", "v1"), ("v2A", "v1"), ("v2B", "tuned"), ("v1", "tuned"), ("v2B", "ppo"), ("v2A", "v2B")):
    if a in S and b in S:
        lo, hi = boot(a, b); out.setdefault("boot", {})[f"{a}-{b}"] = [N[a] - N[b], lo, hi]
        L.append(f"| {a} - {b} | {N[a] - N[b]:+d} | [{lo:+.1f}, {hi:+.1f}] |")
if "v2B" in S and "v1" in S:
    d = N["v2B"] - N["v1"]; lo, _ = boot("v2B", "v1")
    verdict = "CLOSES the gap" if (d >= 3 and lo > 0) else "NO CLOSURE"
    out["closure_verdict_tierB"] = verdict
    L += ["", f"Pre-registered rule (docs/PREREGISTRATION_HEXAHEAL.md): Tier B must gain >= 3 cases over healing v1 with the CI excluding zero. Tier B - v1 = {d:+d}, CI lower bound {lo:+.1f}. **Verdict: {verdict}.** Tier A is an upper-bound style result and is not used for the claim."]
L += ["", "## Survival matrix (survivors / 10, per case; Wilson 95% in brackets)", "", "| case | oracle | " + " | ".join(nm for c, nm in CTRL if c in R) + " |", "|---|---|" + "---|" * sum(c in R for c, _ in CTRL)]
for i, case in enumerate(CASES):
    o = oracle[case]
    cells = []
    for c, _ in CTRL:
        if c in R:
            k = int(S[c][i].sum()); lo, hi = wilson(k); cells.append(f"{k} [{lo:.2f},{hi:.2f}]")
    L.append(f"| {case_name(case)} | {o['walk_seeds']}/10 walk | " + " | ".join(cells) + " |")
L += ["", "## Time-to-fall (mean s over seeds; 14.0 = never fell) and speed-tracking error (RMSE m/s vs 0.25, mean over seeds)", "", "| case | " + " | ".join(nm for c, nm in CTRL if c in R) + " |", "|---|" + "---|" * sum(c in R for c, _ in CTRL)]
for case in CASES:
    cells = []
    for c, _ in CTRL:
        if c in R:
            rr = [R[c][case][s] for s in range(10)]
            cells.append(f"{np.mean([r['t_end'] for r in rr]):.1f} s / {np.mean([r['speed_rmse'] for r in rr]):.2f}")
    L.append(f"| {case_name(case)} | " + " | ".join(cells) + " |")
L += ["", "## Healing diagnostics (v1 diagnoses one leg at a time; v2 the set)", ""]
for c in ("v1", "v2A", "v2B"):
    if c not in R: continue
    rows = [R[c][case][s] for case in CASES for s in range(10)]
    det = [r for r in rows if r.get("t_detect_s") is not None and r["t_detect_s"] >= 0]
    exact = sum(1 for r in rows if r.get("diag") and sorted(r["diag"]) == sorted(r["true_legs"]))
    sub = sum(1 for r in rows if r.get("diag") and set(r["diag"]) <= set(r["true_legs"]) and sorted(r["diag"]) != sorted(r["true_legs"]))
    wrong = sum(1 for r in rows if r.get("diag") and not set(r["diag"]) <= set(r["true_legs"]))
    none = sum(1 for r in rows if not r.get("diag"))
    L.append(f"- {c}: exact fault-set identification {exact}/210, partial subset {sub}, includes a wrong leg {wrong}, no diagnosis {none}; detection time after fault (mean, episodes with a detection) {np.mean([r['t_detect_s'] for r in det]):.2f} s ({len(det)}/210 detected)")
    out.setdefault("diag", {})[c] = dict(exact=exact, subset=sub, wrong=wrong, none=none)
    hp = f"results/hh_healthy_{c}_0-9.jsonl"
    if os.path.exists(hp):
        h = [json.loads(line) for line in open(hp)]
        fp = sum(1 for r in h if r.get("t_detect_s") is not None or r.get("false_alarm"))
        fl = sum(r["fell"] for r in h)
        L.append(f"  - healthy runs (no fault, healing on, seeds 0-9): false positives {fp}/{len(h)}, falls {fl}/{len(h)}")
        out["diag"][c]["healthy_false_pos"] = fp
# where healing lowers survival
L += ["", "## Where healing lowers survival (survivors/10, no healing -> with healing)", ""]
for base, heal in (("tuned", "v1"), ("tuned", "v2A"), ("tuned", "v2B")):
    if base in S and heal in S:
        worse = [f"{case_name(CASES[i])} {int(S[base][i].sum())}->{int(S[heal][i].sum())}" for i in range(21) if S[heal][i].sum() < S[base][i].sum()]
        better = sum(1 for i in range(21) if S[heal][i].sum() > S[base][i].sum())
        L.append(f"- {heal} vs {base}: lowers {len(worse)} cases ({', '.join(worse) or 'none'}); raises {better}")
open("docs/hh_tables.md", "w").write("\n".join(L) + "\n")
json.dump(out, open("results/hh_stats.json", "w"), indent=1, default=float)
print("\n".join(L[:14]))
