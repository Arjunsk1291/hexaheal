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
