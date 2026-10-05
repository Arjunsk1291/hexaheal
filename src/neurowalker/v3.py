"""V3 controllers: nudge-limited connectome (diagnosis Stage 2) and the hybrid (Stage 4)."""
from __future__ import annotations

import numpy as np

from .brain import BrainController


class ScaledBrain(BrainController):
    """BrainController whose CPG nudges are scaled and clipped. scale (scalar or per-nudge [speed, freq, turn, stance]) 0 disables nudges (pure CPG); clip limits |deviation| of each nudge."""
    name = "connectome_scaled"

    def __init__(self, scale=1.0, clip=None, **kw):
        super().__init__(**kw)
        self.scale, self.clip = scale, clip

    def act(self, env, turn_cmd=0.0, legs_disabled=None):
        import time
        t0 = time.perf_counter()
        lv = self.encode(env, turn_cmd)
        self.last_rates = 100.0 * lv
        self._drive(lv)
        ms = env.dt * 1000.0
        counts = self.net.run(ms)
        c = self.decode(counts, ms)
        g = self.g
        dev = np.array([g["speed"] * c["speed"], g["speed_freq"] * c["speed"], g["turn"] * c["turn"], g["stance"] * c["pitch"]]) * np.asarray(self.scale)
        if self.clip is not None:
            dev = np.clip(dev, -np.array(self.clip), np.array(self.clip))
        speed_gain = float(np.clip(1.0 + dev[0], 0.5, 1.5)); freq_scale = float(np.clip(1.0 + dev[1], 0.6, 1.4))
        turn = float(np.clip(dev[2], -0.6, 0.6)); stance = float(np.clip(dev[3], -0.2, 0.2))
        a = self.cpg.act(env, speed_gain=speed_gain, turn=turn, stance_adj=stance, freq_scale=freq_scale)
        self.rt_ms.append((time.perf_counter() - t0) * 1000)
        self.nudges.append((speed_gain, freq_scale, turn, stance))
        return a


class FreeGait:
    """Open-loop gait with free per-leg phase offsets, stride scales and lift scales (superset of the tripod CPG). Used only by the offline oracle (Stage 3).
    x = [freq, stride, lift, duty, turn_bias, stance_adj] + 6 phase offsets + 6 stride scales + 6 lift scales."""
    name = "free_gait"
    N = 24

    def __init__(self, x):
        from .tripod import TripodController, TripodParams
        x = np.asarray(x, float)
        self.cpg = TripodController(TripodParams(freq=x[0], stride=x[1], lift=x[2], duty=x[3], turn_bias=x[4]))
        self.stance = x[5]; self.off = x[6:12]; self.ss = x[12:18]; self.ls = x[18:24]
        self.phase = 0.0

    def reset(self):
        self.phase = 0.0

    def act(self, env, **kw):
        c = self.cpg; p = c.p
        self.phase = (self.phase + env.dt * p.freq) % 1.0
        turn = float(np.clip(p.turn_bias, -0.8, 0.8))
        q = np.zeros(18)
        for leg in range(6):
            c.leg_stride_scale = np.ones(6)
            t = c.leg_targets((self.phase + self.off[leg] - (0.0 if leg in (0, 2, 4) else 0.5)) % 1.0, leg, p.stride * self.ss[leg], turn, lift_scale=self.ls[leg])
            t[1] += self.stance
            q[leg * 3:leg * 3 + 3] = env.q_nom[leg * 3:leg * 3 + 3] + t
        return env.q_to_action(q)


class HybridBrain(BrainController):
    """Stage 4 hybrid: tuned-tripod pitch feedback (kp) sets the stance offset; connectome speed/frequency/turn nudges (each scaled) ride on top while
    nudge_gate is True (the healing wrapper turns the gate off at the first fault suspicion; Stage 2 showed the speed/freq nudges drive the post-fault fall).
    The connectome's own pitch/stance nudge is not used."""
    name = "hybrid"

    def __init__(self, kp=1.2, scale=(1.0, 1.0, 1.0), clip=None, **kw):
        super().__init__(**kw)
        self.kp, self.scale, self.clip = kp, np.asarray(scale, float), clip
        self.nudge_gate = True

    def act(self, env, turn_cmd=0.0, legs_disabled=None):
        import time
        t0 = time.perf_counter()
        lv = self.encode(env, turn_cmd)
        self.last_rates = 100.0 * lv
        self._drive(lv)
        ms = env.dt * 1000.0
        c = self.decode(self.net.run(ms), ms)
        g = self.g
        dev = np.array([g["speed"] * c["speed"], g["speed_freq"] * c["speed"], g["turn"] * c["turn"]]) * self.scale
        if not self.nudge_gate:
            dev = dev * 0.0
        elif self.clip is not None:
            dev = np.clip(dev, -np.array(self.clip), np.array(self.clip))
        _, pitch, _ = env.euler()
        stance = float(np.clip(self.kp * pitch, -0.3, 0.3))
        a = self.cpg.act(env, speed_gain=float(np.clip(1.0 + dev[0], 0.5, 1.5)), turn=float(np.clip(dev[2], -0.6, 0.6)), stance_adj=stance, freq_scale=float(np.clip(1.0 + dev[1], 0.6, 1.4)))
        self.rt_ms.append((time.perf_counter() - t0) * 1000)
        self.nudges.append((float(np.clip(1.0 + dev[0], 0.5, 1.5)), float(np.clip(1.0 + dev[1], 0.6, 1.4)), float(dev[2]), stance))
        return a
