"""Classic tripod-gait CPG controller (baseline). Two phase-locked oscillator groups, 180 deg apart."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .hexapod import TRIPOD_A


@dataclass
class TripodParams:
    freq: float = 1.5  # Hz
    stride: float = 0.35  # coxa half-amplitude (rad)
    lift: float = 0.35  # femur lift (rad)
    tibia_lift: float = 0.25
    duty: float = 0.55  # stance fraction
    turn_bias: float = 0.0  # >0 turns left (right legs stride more)


class TripodController:
    name = "tripod_cpg"

    def __init__(self, params: TripodParams | None = None):
        self.p = params or TripodParams()
        self.phase = 0.0
        self.disabled_legs: set[int] = set()  # used by the self-healing layer
        self.leg_stride_scale = np.ones(6)

    @property
    def cpg(self):
        return self

    def reset(self):
        self.phase = 0.0

    def leg_targets(self, phase, leg, stride, turn, lift_scale=1.0):
        p = self.p
        ph = (phase + (0.0 if leg in TRIPOD_A else 0.5)) % 1.0
        side = 1.0 if leg < 3 else -1.0  # right legs: +
        s = stride * self.leg_stride_scale[leg] * (1 + side * turn)
        if ph < p.duty:  # stance: foot sweeps backward
            u = ph / p.duty
            coxa, lift = s * (1 - 2 * u), 0.0
        else:  # swing: foot sweeps forward and lifts
            u = (ph - p.duty) / (1 - p.duty)
            coxa = s * (-1 + 2 * (0.5 - 0.5 * np.cos(np.pi * u)))
            lift = np.sin(np.pi * u)
        return np.array([coxa, -p.lift * lift * lift_scale, p.tibia_lift * lift * lift_scale])

    def act(self, env, dt=None, speed_gain=1.0, turn=0.0, stance_adj=0.0, freq_scale=1.0):
        dt = dt or env.dt
        p = self.p
        self.phase = (self.phase + dt * p.freq * freq_scale) % 1.0
        turn = float(np.clip(turn + p.turn_bias, -0.8, 0.8))
        q = np.zeros(18)
        for leg in range(6):
            t = self.leg_targets(self.phase, leg, p.stride * speed_gain, turn)
            t[1] += stance_adj
            q[leg * 3:leg * 3 + 3] = env.q_nom[leg * 3:leg * 3 + 3] + t
        return env.q_to_action(q)


def run_episode(ctrl, env, seed=0, max_time=None, callback=None):
    obs, _ = env.reset(seed=seed)
    ctrl.reset()
    while True:
        a = ctrl.act(env)
        obs, r, term, trunc, info = env.step(a)
        if callback:
            callback(env, info)
        if term or trunc or (max_time and env.t >= max_time):
            return info
