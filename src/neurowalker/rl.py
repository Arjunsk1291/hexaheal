"""PPO residual policy on top of the tripod CPG (small 64x64 MLP). The policy outputs a bounded correction added to the CPG action."""
from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from .env import HexapodEnv
from .faults import FAULT_TYPES, Fault
from .tripod import TripodController

RES_SCALE = 0.25


class ResidualEnv(gym.Env):
    """Training env: random terrain (curriculum), random faults and pushes, domain randomization."""

    def __init__(self, terrains=("flat",), seed=0, max_time=8.0, p_fault=0.3, p_push=0.3):
        super().__init__()
        self.allowed = list(terrains)
        self.envs = {}
        self.rng = np.random.default_rng(seed)
        self.seed_ = seed
        self.max_time, self.p_fault, self.p_push = max_time, p_fault, p_push
        e0 = self._get("flat")
        self.action_space = spaces.Box(-1, 1, (18,), np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, (e0.obs_dim + 2,), np.float32)
        self.cpg = TripodController()

    def _get(self, name):
        if name not in self.envs:
            self.envs[name] = HexapodEnv(name, max_time=self.max_time, rand=0.1, seed=self.seed_)
        return self.envs[name]

    def set_terrains(self, names):
        self.allowed = list(names)

    def _obs(self, o):
        ph = 2 * np.pi * self.cpg.phase
        return np.concatenate([o, [np.sin(ph), np.cos(ph)]]).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        name = self.allowed[self.rng.integers(len(self.allowed))]
        self.env = self._get(name)
        self.env.fault_list, self.env.push_list = [], []
        if self.rng.random() < self.p_fault:
            self.env.fault_list = [Fault(FAULT_TYPES[self.rng.integers(4)], float(self.rng.uniform(1.5, 5.0)),
                                         leg=int(self.rng.integers(6)), joint=int(self.rng.integers(3)), severity=float(self.rng.uniform(0.03, 0.3)))]
        if self.rng.random() < self.p_push:
            self.env.push_list = [(float(self.rng.uniform(1.5, 6.0)), float(self.rng.uniform(-15, 15)), float(self.rng.uniform(-30, 30)), 0.15)]
        o, _ = self.env.reset(seed=int(self.rng.integers(1 << 30)))
        self.cpg.reset()
        return self._obs(o), {}

    def step(self, a):
        base = self.cpg.act(self.env)
        o, r, te, tr, info = self.env.step(np.clip(base + RES_SCALE * np.asarray(a), -1, 1))
        return self._obs(o), r, te, tr, info


class PPOController:
    name = "ppo_residual"

    def __init__(self, model_path, params=None):
        from stable_baselines3 import PPO
        self.model = PPO.load(model_path, device="cpu")
        self.cpg = TripodController(params)
        self.rt_ms = []

    def reset(self):
        self.cpg.reset()

    def act(self, env, **kw):
        import time
        t0 = time.perf_counter()
        base = self.cpg.act(env)
        o = env._obs()
        ph = 2 * np.pi * self.cpg.phase
        obs = np.concatenate([o, [np.sin(ph), np.cos(ph)]]).astype(np.float32)
        a, _ = self.model.predict(obs, deterministic=True)
        self.rt_ms.append((time.perf_counter() - t0) * 1000)
        return np.clip(base + RES_SCALE * a, -1, 1)
