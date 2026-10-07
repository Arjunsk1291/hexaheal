"""HexaHeal evaluation harness (simulation). One episode of a leg-loss case: leg(s) disabled at FAULT_T, flat, 14 s, target 0.25 m/s.
Metrics: survived (no fall by the end), time-to-fall (episode length if no fall), speed-tracking error (RMSE of 1 s-window forward speed vs target over [FAULT_T, 14 s],
speed counted as 0 after a fall), distance. Healing controllers add detection time and diagnosis."""
from __future__ import annotations

import numpy as np

from .benchmark import FAULT_T, TARGET_SPEED
from .env import HexapodEnv
from .faults import Fault

T_END = 14.0
LAST_S, REC_FRAC = 8.0, 0.5
LEG = ["R1", "R2", "R3", "L1", "L2", "L3"]


def case_legs(case):
    return [int(v) for v in case[3:].split("_")] if case.startswith("dl_") else []


def case_name(case):
    return "+".join(LEG[i] for i in case_legs(case)) or case


def run_episode(ctrl, case, seed, fault_t=FAULT_T, faults=None):
    legs = case_legs(case)
    env = HexapodEnv("flat", max_time=T_END, faults=faults if faults is not None else [Fault("disable_leg", fault_t, leg=lg) for lg in legs], rand=0.1, seed=seed, target_speed=TARGET_SPEED)
    if hasattr(ctrl, "seed"):
        ctrl.seed = seed
    env.reset(seed=seed); ctrl.reset()
    ts, xs = [], []
    while True:
        _, _, te, tr, _ = env.step(ctrl.act(env))
        ts.append(env.t); xs.append(float(env.data.qpos[0]))
        if te or tr: break
    ts, xs = np.array(ts), np.array(xs)
    # 1 s-window speed on a 0.5 s grid over [fault_t, T_END]; after a fall (episode end) speed is 0
    errs = []
    for a in np.arange(fault_t, T_END - 1.0 + 1e-9, 0.5):
        if a + 1.0 <= ts[-1] + 1e-9:
            i, j = np.searchsorted(ts, a), min(np.searchsorted(ts, a + 1.0), len(ts) - 1)
            v = (xs[j] - xs[i]) / max(ts[j] - ts[i], 1e-9)
        else:
            v = 0.0
        errs.append((v - TARGET_SPEED) ** 2)
    # v3 (pre-registered): mean forward speed over the LAST 8 s of the episode, (x(14) - x(6)) / 8; recovered = no fall and >= 50% of nominal
    k8 = int(np.searchsorted(ts, T_END - LAST_S))
    v8 = float((xs[-1] - xs[min(k8, len(xs) - 1)]) / LAST_S) if (not env.fell and ts[-1] >= T_END - 0.05) else 0.0
    r = dict(case=case, seed=seed, fell=bool(env.fell), t_end=float(env.t), distance=float(xs[-1] - env.x0), v_last8=v8, recovered=bool((not env.fell) and v8 >= REC_FRAC * TARGET_SPEED),

             speed_rmse=float(np.sqrt(np.mean(errs))) if errs else float("nan"))
    # v4 diagnostics: first time after the fault at which the mean speed over the next 2 s is >= 0.125 m/s (no fall inside that window); None = never
    i0 = np.searchsorted(ts, fault_t)
    j = np.searchsorted(ts, ts[i0:] + 2.0)
    ok = (ts[i0:] + 2.0 <= ts[-1] + 1e-9) & (j < len(ts))
    sp = np.where(ok, (xs[np.minimum(j, len(ts) - 1)] - xs[i0:]) / 2.0, -1.0)
    hit = np.nonzero(sp >= REC_FRAC * TARGET_SPEED)[0]
    r["first_walk_s"] = float(ts[i0 + hit[0]] - fault_t) if len(hit) else None
    lg = getattr(ctrl, "log", None)
    if lg:
        tp = [e["t"] for e in lg if e["to"] == "PLAN"]
        tr_ = [e["t"] for e in lg if e["to"] == "RUN"]
        r["t_plan_start_s"] = None if not tp else float(tp[0] - fault_t)
        r["t_stand_s"] = float(tr_[0] - tp[0]) if tp and tr_ and tr_[0] >= tp[0] else None
    if hasattr(ctrl, "summary") and hasattr(ctrl, "t_detect"):
        s = ctrl.summary()
        r.update(t_detect_s=None if ctrl.t_detect is None else float(ctrl.t_detect - fault_t), diag=s.get("diag") or ([s["diagnosis"]["leg"]] if s.get("diagnosis") else None), true_legs=legs,
                 false_alarm=bool(s.get("false_alarm", False)))
    return r
