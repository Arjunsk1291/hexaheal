"""HexaHeal healing v2 (simulation only). Same health monitor as v1, but:
 - diagnoses the SET of faulted legs (v1 diagnosed one leg at a time);
 - re-plans in the free-gait family (per-leg phase offsets, per-leg amplitude and lift, global duty/frequency/stance), not just tripod parameters;
 - while planning it can hold a standing pose instead of continuing a broken gait ('interim');
 - Tier A: the gait comes from an offline library keyed by the diagnosed fault set (library built from tuning-seed search; upper-bound style, no online learning).
 - Tier B: online CMA-ES in short simulated rollouts of a model copy, limited by a deterministic SIM-time budget (max_trials x SIM_S_PER_TRIAL), never wall clock.
Every transition is logged."""
from __future__ import annotations

import cma
import numpy as np

from .env import HexapodEnv
from .faults import Fault
from .freegait import FreeGait
from .healing import HealthMonitor

SIM_S_PER_TRIAL = 0.075
LO = np.array([0.8, 0.1, 0.1, 0.4, -0.5, -0.2] + [0.0] * 6 + [0.0] * 6 + [0.0] * 6)
HI = np.array([2.6, 0.55, 0.6, 0.85, 0.5, 0.2] + [1.0] * 6 + [1.6] * 6 + [1.6] * 6)
X0 = np.array([1.5, 0.35, 0.35, 0.55, 0.0, 0.0] + [0, 0.5, 0, 0.5, 0, 0.5] + [1.0] * 6 + [1.0] * 6)


def diagnose_set(f, masked=(), thr=0.25, n_joints=2, free_space=1):
    """Legs with disable-like evidence: all-flat sensors, or elevated tracking error on >= n_joints joints. f['elevation'] may be a peak-held vector."""
    elev, flat = f["elevation"].reshape(6, 3), f["flat"].reshape(6, 3)
    legs = [lg for lg in range(6) if lg not in masked and (flat[lg].all() or (elev[lg] > thr).sum() >= n_joints)]
    return sorted(legs)


class HealingV2:
    def __init__(self, base, tier="B", library=None, max_trials=60, rollout_s=3.0, confirm_s=0.6, interim="stand", seed=0, x0=None, suspect_n=8, peak_hold=True, min_confirm_s=0.1, thr=0.25, n_joints=2, free_space=1,
                 extra_delay_s=0.0, dnh=False, dnh_window=1.0, dnh_speed=0.125, dnh_tilt=0.35, dnh_lock_s=2.0, warm_s=0.0, warm_library=None):
        assert tier in ("A", "B")
        self.base, self.tier, self.library = base, tier, library or {}
        self.max_trials, self.rollout_s, self.confirm_s, self.interim, self.seed = max_trials, rollout_s, confirm_s, interim, seed
        self.suspect_n = int(suspect_n)
        self.free_space = int(free_space)
        # v3 additions. extra_delay_s: artificial response delay (Stage 3 sweep): the diagnosis is held back this long after it is ready, robot keeps its current gait.
        # dnh: 'do no harm' (Stage 2): watch the current gait for dnh_window s after the fault is suspected; if forward speed >= dnh_speed m/s and max |roll|,|pitch| < dnh_tilt rad, keep it.
        self.extra_delay_s, self.dnh, self.dnh_window, self.dnh_speed, self.dnh_tilt, self.dnh_lock_s = float(extra_delay_s), bool(dnh), dnh_window, dnh_speed, dnh_tilt, dnh_lock_s
        # v4: warm_library (dict {failed-leg tuple: gait vector}) -> CMA-ES starts from the nearest entry to the diagnosed set; `exclude` (set of tuples) removes entries (leave-one-case-out)
        self.warm_library, self.exclude = warm_library, set()
        self.warm_s = float(warm_s)  # v3 round 2: score search rollouts on steady-state distance (after warm_s) instead of total distance incl. the start-up transient
        self.peak_hold, self.min_confirm_s, self.thr, self.nj = peak_hold, min_confirm_s, thr, int(n_joints)
        self.x0 = np.array(X0 if x0 is None else x0, float)
        self.name = f"{base.name}+healing_v2{tier}"
        self.reset()

    def reset(self):
        self.base.reset()
        self.mon = HealthMonitor()
        self.state = "NORMAL"
        self.log = []
        self.prev_action = None
        self.t_state = 0.0
        self.suspect_count = 0
        self.known: list[int] = []
        self.diag = None
        self.t_detect = self.t_plan_done = None
        self.gait = None
        self.delay_steps = 0
        self.info = {}
        self.false_alarm = False
        self.t_ready = None
        self.lock_until = -1.0
        self.w_x0 = None
        self.w_tilt = 0.0
        self.kept = False

    def _log(self, env, to, evidence=None, action=None):
        self.log.append({"t": round(float(env.t), 3), "from": self.state, "to": to, "evidence": evidence or {}, "action": action or {}})
        self.state, self.t_state = to, env.t

    def _warm_x0(self, legs):
        d = set(legs)
        cands = [(len(d ^ set(k)), i, k) for i, k in enumerate(sorted(self.warm_library, key=lambda k: (len(k), k))) if k not in self.exclude]
        if not cands:
            return self.x0
        _, _, k = min(cands)
        self.info_warm = list(k)
        return np.clip(np.array(self.warm_library[k], float), LO, HI)

    def _search(self, env, legs):
        faults = [Fault("disable_leg", 0.0, leg=lg) for lg in legs]

        def fit(x):
            e = HexapodEnv("flat", max_time=self.rollout_s, faults=faults, rand=0.0, seed=self.seed, target_speed=env.target_speed)
            e.reset(seed=self.seed); g = FreeGait(x); g.reset()
            xw = None
            while True:
                _, _, te, tr, _ = e.step(g.act(e))
                if xw is None and e.t >= self.warm_s: xw = float(e.data.qpos[0])
                if te or tr: break
            dist = e.distance() if self.warm_s <= 0 or xw is None else float(e.data.qpos[0]) - xw
            return -(dist - abs(float(e.data.qpos[1])) - (3.0 if e.fell else 0.0) + 0.1 * e.t)

        to_u = lambda x: (x - LO) / (HI - LO)
        def from_u(u):
            x = LO + np.clip(u, 0, 1) * (HI - LO)
            if not self.free_space:  # ablation: tripod-only search space (no per-leg phase/amplitude/lift)
                x[6:] = X0[6:]
            return x
        x0 = self._warm_x0(legs) if self.warm_library else self.x0
        best_u, best_f = to_u(x0), fit(x0)
        n, f0 = 1, best_f
        es = cma.CMAEvolutionStrategy(best_u.copy(), 0.25, {"popsize": 6, "seed": self.seed + 1, "verbose": -9, "bounds": [0, 1]})
        while n < self.max_trials:
            sols = es.ask(); fs = [fit(from_u(s)) for s in sols]; n += len(sols); es.tell(sols, fs)
            i = int(np.argmin(fs))
            if fs[i] < best_f: best_f, best_u = fs[i], sols[i]
        return from_u(best_u), {"trials": n, "fitness_before": round(-f0, 3), "fitness_after": round(-best_f, 3)}

    def _decide(self, env, legs):
        if not legs:
            self.false_alarm = True
            self._log(env, "RUN" if self.gait is not None else "NORMAL", action={"decision": "no localizable fault"}); self.suspect_count = 0
        else:
            self.diag = sorted(set(self.known) | set(legs))
            self._log(env, "PLAN", {"diagnosed_legs": self.diag}, {"tier": self.tier})
            if self.tier == "A":
                x = self.library.get(tuple(self.diag))
                self.info = {"trials": 0, "library_hit": x is not None}
                self.gait = None if x is None else FreeGait(np.array(x))
                self.delay_steps = 0
            else:
                x, self.info = self._search(env, self.diag)
                self.gait = FreeGait(x)
                self.delay_steps = int(np.ceil(self.info["trials"] * SIM_S_PER_TRIAL / env.dt))
            if self.gait is not None: self.gait.reset()

    def _ready_decide(self, env, legs):
        t = env.t
        if self.t_ready is None:
            self.t_ready = t
        if t - self.t_ready < self.extra_delay_s:
            return
        if self.dnh and legs and self.gait is None:  # first fault only: watch the current gait post-fault
            if self.w_x0 is None:
                self.w_x0 = (self.t_state, float(env.data.qpos[0]))
            ro, pi = env.euler()[:2]
            self.w_tilt = max(self.w_tilt, abs(float(ro)), abs(float(pi)))
            if t - self.w_x0[0] < self.dnh_window:
                return
            v = (float(env.data.qpos[0]) - self.w_x0[1]) / max(t - self.w_x0[0], 1e-6)
            if v >= self.dnh_speed and self.w_tilt < self.dnh_tilt:
                self.kept = True
                self._log(env, "NORMAL", {"watch_speed": round(v, 3), "watch_tilt": round(self.w_tilt, 3)}, {"decision": "keep current gait (do no harm)"})
                self.lock_until = t + self.dnh_lock_s; self.suspect_count = 0; self.t_ready = None; self.w_x0 = None; self.w_tilt = 0.0
                return
        self._decide(env, legs)

    def act(self, env, **kw):
        t = env.t
        if self.prev_action is not None:
            self.mon.update(t, env.action_to_q(self.prev_action), env.last_sensed_q, *env.euler()[:2])
        if self.state in ("NORMAL", "RUN") and self.mon.ready() and t >= self.lock_until:
            sus, f = self.mon.suspect()
            self.suspect_count = self.suspect_count + 1 if sus else 0
            if self.suspect_count >= self.suspect_n:
                self.t_detect = self.t_detect if self.t_detect is not None else t
                self.peak = np.maximum(0.0, f["elevation"])
                self._log(env, "SUSPECTED", {"max_elevation_rad": round(float(f["elevation"].max()), 3), "tilt_rms": round(f["tilt_rms"], 3)})
        elif self.state == "SUSPECTED" and self.peak_hold:
            f = self.mon.features()
            self.peak = np.maximum(self.peak, f["elevation"])
            legs = diagnose_set(dict(f, elevation=self.peak), masked=self.known, thr=self.thr, n_joints=self.nj)
            dt = t - self.t_state
            if (legs and dt >= self.min_confirm_s) or dt >= self.confirm_s:
                self._ready_decide(env, legs)
        elif self.state == "SUSPECTED" and t - self.t_state >= self.confirm_s:
            self._ready_decide(env, diagnose_set(self.mon.features(), masked=self.known, thr=self.thr, n_joints=self.nj))
        elif self.state == "PLAN":
            if self.delay_steps > 0:
                self.delay_steps -= 1
            else:
                self.known = list(self.diag); self.t_plan_done = t
                self._log(env, "RUN", self.info, {"applied": self.gait is not None})
                self.mon = HealthMonitor(win=(t + 0.1, t + 0.9)); self.mon.masked = set(self.known)
                self.suspect_count = 0
                if self.gait is None:  # no library entry: fall back to the base controller
                    self.state = "NORMAL"
        if self.state == "PLAN" and self.interim == "stand":
            a = env.q_to_action(env.q_nom)
        elif self.state in ("RUN", "SUSPECTED") and self.gait is not None:
            a = self.gait.act(env)
        else:
            a = self.base.act(env, **kw)
        self.prev_action = a
        return a

    def summary(self):
        return {"state": self.state, "t_detect": self.t_detect, "diag": self.diag, "false_alarm": self.false_alarm, "t_plan_done": self.t_plan_done, "kept_gait": self.kept}
