"""Benchmark arena: controllers x scenarios x seeds, raw per-episode metrics."""
from __future__ import annotations

import time

import numpy as np
import psutil

from .env import HexapodEnv
from .faults import Fault
from .healing import HealingController

TARGET_SPEED = 0.25
FAULT_T = 4.0
FAULTS = {
    "fault_disable_leg": Fault("disable_leg", FAULT_T, leg=2),
    "fault_lock_joint": Fault("lock_joint", FAULT_T, leg=4, joint=0),
    "fault_reduce_torque": Fault("reduce_torque", FAULT_T, leg=1, severity=0.05),
    "fault_sensor_dropout": Fault("sensor_dropout", FAULT_T, leg=3),
}
PUSH = (4.0, 0.0, 48.0, 0.15)  # t, Fx, Fy (N), duration (s)
TERRAIN_SCENARIOS = ["flat", "rough1", "rough2", "rough3", "slope10", "slope15", "slope20"]
SCENARIOS = TERRAIN_SCENARIOS + ["push"] + list(FAULTS) + [f"{k}+healing" for k in FAULTS]


def scenario_spec(name):
    heal = name.endswith("+healing")
    base = name.replace("+healing", "")
    if base in TERRAIN_SCENARIOS:
        return dict(terrain=base, t=10.0, faults=[], pushes=[], heal=False)
    if base == "push":
        return dict(terrain="flat", t=12.0, faults=[], pushes=[PUSH], heal=False)
    return dict(terrain="flat", t=14.0, faults=[FAULTS[base]], pushes=[], heal=heal)


def _speed(xs, ts, a, b):
    i, j = np.searchsorted(ts, a), np.searchsorted(ts, b) - 1
    j = min(j, len(ts) - 1)
    if j <= i:
        return float("nan")
    return float((xs[j] - xs[i]) / (ts[j] - ts[i]))


def run_one(ctrl, ctrl_name, scenario, seed):
    sp = scenario_spec(scenario)
    env = HexapodEnv(sp["terrain"], max_time=sp["t"], faults=sp["faults"], pushes=sp["pushes"], rand=0.1, seed=seed, target_speed=TARGET_SPEED)
    c = HealingController(ctrl, terrain=sp["terrain"], seed=seed) if sp["heal"] else ctrl
    if hasattr(ctrl, "seed"):
        ctrl.seed = seed
    env.reset(seed=seed)
    c.reset()
    ts, xs, ys, _tilt, roll, pitch = [], [], [], [], [], []
    lat = []
    proc = psutil.Process()
    cpu0, w0 = sum(proc.cpu_times()[:2]), time.perf_counter()
    while True:
        t0 = time.perf_counter()
        a = c.act(env)
        lat.append((time.perf_counter() - t0) * 1000)
        _, _, te, tr, info = env.step(a)
        ts.append(env.t); xs.append(float(env.data.qpos[0])); ys.append(float(env.data.qpos[1]))
        roll.append(info["roll"]); pitch.append(info["pitch"])
        if te or tr:
            break
    wall = time.perf_counter() - w0
    cpu = sum(proc.cpu_times()[:2]) - cpu0
    ts, xs, roll, pitch = map(np.array, (ts, xs, roll, pitch))
    r = dict(controller=ctrl_name, scenario=scenario, seed=seed, fell=bool(env.fell), t_end=float(env.t),
             distance=float(xs[-1] - env.x0), mean_speed=float((xs[-1] - env.x0) / max(env.t, 1e-6)),
             cot=float(env.cot()) if (xs[-1] - env.x0) > 0.05 else float("nan"),
             roll_rms=float(np.sqrt(np.mean(roll ** 2))), pitch_rms=float(np.sqrt(np.mean(pitch ** 2))),
             latency_ms=float(np.mean(lat)), cpu_util=float(cpu / max(wall, 1e-9)), wall_s=float(wall), y_drift=float(abs(ys[-1])))
    nan = float("nan")
    r.update(push_recovery_s=nan, fault_pre_speed=nan, fault_post_speed=nan, fault_retained=nan, fault_recovery_s=nan,
             t_detect_s=nan, t_verified_recovery_s=nan, final_state="")
    if sp["pushes"]:
        tp = PUSH[0] + PUSH[3]
        pre = np.sqrt(roll[ts < PUSH[0]] ** 2 + pitch[ts < PUSH[0]] ** 2)
        thr = max(0.03, 1.5 * float(np.sqrt(np.mean(pre ** 2))))
        tl = np.hypot(roll, pitch)
        if not env.fell:
            idx = np.where(ts >= tp)[0]
            for k in idx:
                w = (ts >= ts[k]) & (ts < ts[k] + 0.5)
                if ts[k] + 0.5 <= ts[-1] + 1e-9 and np.all(tl[w] < thr):
                    r["push_recovery_s"] = float(ts[k] - tp) 
                    break
    if sp["faults"]:
        pre = _speed(xs, ts, 1.5, FAULT_T)
        post = _speed(xs, ts, 10.0, 14.0) if env.t >= 13.9 else 0.0
        r["fault_pre_speed"], r["fault_post_speed"] = pre, post
        r["fault_retained"] = float(max(post, 0.0) / pre) if pre and pre > 0 else nan
        if not env.fell:  # first time after the fault when 1 s-window speed stays >= 70% of pre-fault speed for 2 s
            for k in np.where(ts >= FAULT_T)[0]:
                sp1 = _speed(xs, ts, ts[k], ts[k] + 2.0)
                if ts[k] + 2.0 <= ts[-1] and not np.isnan(sp1) and sp1 >= 0.7 * pre:
                    r["fault_recovery_s"] = float(ts[k] - FAULT_T); break
        if sp["heal"]:
            r["final_state"] = c.state
            if c.t_detect is not None:
                r["t_detect_s"] = float(c.t_detect - FAULT_T)
            if c.t_recover is not None:
                r["t_verified_recovery_s"] = float(c.t_recover - FAULT_T)
    return r, (c.log if sp["heal"] else None)
