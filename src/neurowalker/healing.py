"""Self-healing layer: health monitor + explicit state machine
NORMAL -> FAULT_SUSPECTED -> DIAGNOSE -> ADAPT -> VERIFY -> NORMAL | SAFE_STOP.
Adaptation = gait re-planning via CMA-ES over CPG parameters, evaluated in short simulated rollouts of a model copy
with the diagnosed fault applied. Every decision is logged (timestamp, evidence, action)."""
from __future__ import annotations

import json
import time
from collections import deque

import cma
import numpy as np

from .env import HexapodEnv
from .faults import Fault
from .tripod import TripodController, TripodParams

STATES = ["NORMAL", "FAULT_SUSPECTED", "DIAGNOSE", "ADAPT", "VERIFY", "SAFE_STOP"]
WIN = 25  # 0.5 s window at 50 Hz


class HealthMonitor:
    def __init__(self):
        self.res = deque(maxlen=WIN)
        self.qs = deque(maxlen=WIN)
        self.qc = deque(maxlen=WIN)
        self.tilt = deque(maxlen=WIN)
        self.ema = np.zeros(18)
        self.base = None
        self._base_samples = []

    def update(self, t, q_cmd, q_sensed, roll, pitch):
        r = np.abs(q_cmd - q_sensed)
        self.ema = 0.9 * self.ema + 0.1 * r
        self.qs.append(q_sensed.copy()); self.qc.append(q_cmd.copy()); self.tilt.append(np.hypot(roll, pitch))
        if 1.5 <= t < 3.5:
            self._base_samples.append(self.ema.copy())
        elif self.base is None and t >= 3.5 and self._base_samples:
            self.base = np.max(self._base_samples, axis=0)

    def ready(self):
        return self.base is not None and len(self.qs) == WIN

    def features(self):
        qs, qc = np.array(self.qs), np.array(self.qc)
        elev = self.ema - self.base
        frozen = (qs.std(0) < 0.2 * qc.std(0)) & (qc.std(0) > 0.05)
        flat = qs.std(0) < 0.0015
        return {"elevation": elev, "frozen": frozen, "flat": flat, "tilt_rms": float(np.sqrt(np.mean(np.square(self.tilt))))}

    def suspect(self):
        f = self.features()
        return bool(f["elevation"].max() > 0.08 or f["frozen"].any() or f["tilt_rms"] > 0.25), f

    @staticmethod
    def diagnose(f):
        elev, frozen, flat = f["elevation"].reshape(6, 3), f["frozen"].reshape(6, 3), f["flat"].reshape(6, 3)
        cand = []
        for leg in range(6):
            if flat[leg].all():
                cand.append((leg, 0, "sensor_dropout", 3.0))
            elif (elev[leg] > 0.25).sum() >= 2:
                cand.append((leg, 1, "disable_leg", float(elev[leg].sum())))
            elif frozen[leg].any():
                cand.append((leg, int(np.argmax(frozen[leg])), "lock_joint", 2.0))
            elif elev[leg].max() > 0.08:
                cand.append((leg, int(np.argmax(elev[leg])), "reduce_torque", float(elev[leg].max())))
        if not cand:
            return None
        cand.sort(key=lambda c: -c[3])
        leg, joint, kind, score = cand[0]
        return {"leg": leg, "joint": joint, "kind": kind, "score": score, "n_candidates": len(cand)}


class HealingController:
    """Wraps any controller exposing .cpg (TripodController) and .act(env)."""

    def __init__(self, base, terrain="flat", max_trials=18, rollout_s=2.5, seed=0):
        self.base = base
        self.name = base.name + "+healing"
        self.terrain, self.max_trials, self.rollout_s, self.seed = terrain, max_trials, rollout_s, seed
        self.reset()

    def reset(self):
        self.base.reset()
        self.mon = HealthMonitor()
        self.state = "NORMAL"
        self.log: list[dict] = []
        self.prev_action = None
        self.t_state = 0.0
        self.suspect_count = 0
        self.diag = None
        self.new_params = None
        self.delay_steps = 0
        self.x_hist = deque(maxlen=400)
        self.pre_fault_speed = None
        self.verify_start = None
        self.attempt = 0
        self.t_detect = self.t_recover = None
        self.adapt_wall_s = None

    def _log(self, env, to, evidence=None, action=None):
        self.log.append({"t": round(float(env.t), 3), "from": self.state, "to": to, "evidence": evidence or {}, "action": action or {}})
        self.state = to
        self.t_state = env.t

    def _speed(self, env, window):
        h = list(self.x_hist)
        if len(h) < 2:
            return 0.0
        n = min(window, len(h) - 1)
        return (h[-1][1] - h[-1 - n][1]) / (h[-1][0] - h[-1 - n][0] + 1e-9)

    # ---- model-based gait search
    def _search(self, env, diag):
        fault = Fault(diag["kind"], 0.0, leg=diag["leg"], joint=diag["joint"], severity=getattr(self, "est_severity", 0.05),
                      angle=float(np.mean(np.array(self.mon.qs)[:, diag["leg"] * 3 + diag["joint"]])))
        p0 = self.base.cpg.p
        lo = np.array([1.0, 0.15, 0.15, 0.5, -0.4, 0.0]); hi = np.array([2.4, 0.5, 0.5, 0.8, 0.4, 1.0])
        x0 = np.array([p0.freq, p0.stride, p0.lift, p0.duty, p0.turn_bias, 1.0])
        to_u = lambda x: (x - lo) / (hi - lo)
        from_u = lambda u: lo + np.clip(u, 0, 1) * (hi - lo)

        def apply(c, x):
            c.p = TripodParams(freq=x[0], stride=x[1], lift=x[2], duty=x[3], turn_bias=x[4], tibia_lift=p0.tibia_lift)
            c.leg_stride_scale = np.ones(6); c.leg_stride_scale[diag["leg"]] = x[5]

        def fitness(u):
            x = from_u(u)
            e = HexapodEnv(self.terrain, max_time=self.rollout_s + 0.5, faults=[fault], seed=self.seed, target_speed=env.target_speed)
            e.reset(seed=self.seed)
            c = TripodController(); apply(c, x)
            while True:
                _, _, te, tr, _ = e.step(c.act(e))
                if te or tr:
                    break
            d = e.distance(); y = abs(e.data.qpos[1])
            return -(d - 1.0 * y - (2.0 if e.fell else 0.0))

        t0 = time.perf_counter()
        es = cma.CMAEvolutionStrategy(to_u(x0), 0.25, {"popsize": 6, "seed": self.seed + 1, "verbose": -9, "bounds": [0, 1]})
        n = 0
        best_f, best_u = fitness(to_u(x0)), to_u(x0)
        n += 1
        f_init = best_f
        while n < self.max_trials:
            sols = es.ask()
            fs = [fitness(s) for s in sols]
            n += len(sols)
            es.tell(sols, fs)
            i = int(np.argmin(fs))
            if fs[i] < best_f:
                best_f, best_u = fs[i], sols[i]
        wall = time.perf_counter() - t0
        return from_u(best_u), apply, {"trials": n, "wall_s": round(wall, 2), "fitness_before": round(-f_init, 3), "fitness_after": round(-best_f, 3)}

    def act(self, env, **kw):
        t = env.t
        if self.prev_action is not None:
            self.mon.update(t, env.action_to_q(self.prev_action), env.last_sensed_q, *env.euler()[:2])
        self.x_hist.append((t, float(env.data.qpos[0])))
        if self.state == "SAFE_STOP":
            self.prev_action = np.zeros(18)
            return self.prev_action
        if self.state == "NORMAL" and self.mon.ready() and t < 3.9:
            self.pre_fault_speed = self._speed(env, 100)
        if self.state == "NORMAL" and self.mon.ready():
            sus, f = self.mon.suspect()
            self.suspect_count = self.suspect_count + 1 if sus else 0
            if self.suspect_count >= 8:
                self.t_detect = t
                self._log(env, "FAULT_SUSPECTED", {"max_elevation_rad": round(float(f["elevation"].max()), 3), "frozen_joints": int(f["frozen"].sum()), "tilt_rms": round(f["tilt_rms"], 3)})
        elif self.state == "FAULT_SUSPECTED" and t - self.t_state >= 0.6:
            f = self.mon.features()
            d = self.mon.diagnose(f)
            self._log(env, "DIAGNOSE", {"elevation_by_leg": np.round(f["elevation"].reshape(6, 3), 2).tolist()})
            if d is None:
                self._log(env, "NORMAL", action={"decision": "false alarm, no localizable fault"}); self.suspect_count = 0
            else:
                self.diag = d
                self.diag_t = t
                self._log(env, "ADAPT", {"diagnosis": d}, {"decision": "gait re-plan via CMA-ES"})
                if d["kind"] == "sensor_dropout":
                    self.new_params = None
                    self.adapt_info = {"note": "sensors of this leg flagged unreliable; leg continues open-loop under the CPG", "trials": 0, "wall_s": 0.0}
                    self.delay_steps = 0
                else:
                    self.est_severity = 0.05
                    x, apply, info = self._search(env, d)
                    self.new_params = (x, apply)
                    self.adapt_info = info
                    self.adapt_wall_s = info["wall_s"]
                    self.delay_steps = int(np.ceil(info["wall_s"] / env.dt))  # old gait continues while the search "runs"
        elif self.state == "ADAPT":
            if self.delay_steps > 0:
                self.delay_steps -= 1
            else:
                if self.new_params is not None:
                    x, apply = self.new_params
                    apply(self.base.cpg, x)
                self.verify_start = (t, float(env.data.qpos[0]))
                self._log(env, "VERIFY", self.adapt_info, {"applied_params": None if self.new_params is None else np.round(self.new_params[0], 3).tolist()})
        elif self.state == "VERIFY" and t - self.verify_start[0] >= 1.5:
            sp = (env.data.qpos[0] - self.verify_start[1]) / (t - self.verify_start[0])
            ref = max(self.pre_fault_speed or 0.0, 1e-3)
            ok = (not env.fell) and sp >= 0.5 * ref and self.mon.features()["tilt_rms"] < 0.3
            ev = {"speed_m_s": round(float(sp), 3), "pre_fault_speed_m_s": round(float(ref), 3), "ratio": round(float(sp / ref), 3)}
            if ok:
                self.t_recover = t
                self._log(env, "NORMAL", ev, {"decision": "recovery verified"})
                self.suspect_count = -10 ** 6  # healed: do not re-trigger on the residual signature of the known fault
            elif self.attempt == 0:
                self.attempt = 1
                self._log(env, "ADAPT", ev, {"decision": "verify failed, second search with larger budget"})
                self.max_trials = 36
                x, apply, info = self._search(env, self.diag)
                self.new_params = (x, apply); self.adapt_info = info
                self.delay_steps = int(np.ceil(info["wall_s"] / env.dt))
            else:
                self._log(env, "SAFE_STOP", ev, {"decision": "unable to verify recovery, standing still"})
        a = self.base.act(env, **kw)
        self.prev_action = a
        return a

    def summary(self):
        return {"state": self.state, "t_detect": self.t_detect, "t_recover": self.t_recover, "diagnosis": self.diag, "adapt_wall_s": self.adapt_wall_s}

    def save_log(self, path):
        json.dump({"controller": self.name, "decisions": self.log, "summary": self.summary()}, open(path, "w"), indent=1, default=float)
