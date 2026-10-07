"""Free per-leg gait family (phase offsets, duty, amplitude, lift) used by the oracle and healing v2. Simulation only."""
from __future__ import annotations

import numpy as np


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
