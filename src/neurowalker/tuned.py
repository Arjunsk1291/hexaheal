"""Tuned tripod baseline: the plain tripod CPG plus simple analytic pitch/roll feedback (no learning, no network).
stance_adj (femur offset, rad) = kp*pitch + kr*|roll| ; stride scale reduced by ks*|pitch|. Gains are chosen on tuning seeds 100-109 only."""
from __future__ import annotations

import numpy as np

from .tripod import TripodController, TripodParams


class TunedTripod:
    name = "tuned_tripod"

    def __init__(self, kp=0.0, kr=0.0, ks=0.0, tripod: TripodParams | None = None):
        self.cpg = TripodController(tripod)
        self.kp, self.kr, self.ks = kp, kr, ks
        self.seed = 0

    def reset(self):
        self.cpg.reset()

    def act(self, env, **kw):
        roll, pitch, _ = env.euler()
        stance = float(np.clip(self.kp * pitch + self.kr * abs(roll), -0.3, 0.3))
        gain = float(np.clip(1.0 - self.ks * abs(pitch), 0.4, 1.0))
        return self.cpg.act(env, speed_gain=gain, stance_adj=stance)
