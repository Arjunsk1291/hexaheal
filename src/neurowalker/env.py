"""Gymnasium environment around the generated hexapod MJCF."""
from __future__ import annotations

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from .faults import Fault
from .hexapod import JOINT_NAMES, LEG_NAMES, HexapodParams, generate_mjcf, hfield_data

TERRAINS = {
    "flat": {"kind": "flat"},
    "rough1": {"kind": "rough", "level": 1},
    "rough2": {"kind": "rough", "level": 2},
    "rough3": {"kind": "rough", "level": 3},
    "slope10": {"kind": "slope", "deg": 10},
    "slope15": {"kind": "slope", "deg": 15},
    "slope20": {"kind": "slope", "deg": 20},
}
N_J = 18


class HexapodEnv(gym.Env):
    """Action: 18 normalized joint-position targets in [-1,1] (0 = nominal stance).
    Control period 0.02 s (4 physics steps at dt=0.005)."""

    metadata = {"render_modes": ["rgb_array"]}

    def __init__(self, terrain: str = "flat", max_time: float = 10.0, target_speed: float = 0.2,
                 faults: list[Fault] | None = None, pushes: list[tuple] | None = None,
                 rand: float = 0.0, seed: int = 0, substeps: int = 4):
        super().__init__()
        self.terrain_name = terrain
        self.params = HexapodParams(terrain=TERRAINS[terrain])
        self.model = mujoco.MjModel.from_xml_string(generate_mjcf(self.params))
        self.data = mujoco.MjData(self.model)
        self.substeps = substeps
        self.dt = self.params.dt * substeps
        self.max_time = max_time
        self.target_speed = target_speed
        self.fault_list = list(faults or [])
        self.push_list = list(pushes or [])  # (time, fx, fy, duration)
        self.rand = rand
        self._seed = seed
        self.rng = np.random.default_rng(seed)
        nom = np.array(self.params.nominal)
        self.q_nom = np.tile(nom, 6)
        self.q_lo = np.tile([r[0] for r in self.params.ranges], 6)
        self.q_hi = np.tile([r[1] for r in self.params.ranges], 6)
        self.scale = np.tile([0.5, 0.7, 0.8], 6)
        self.action_space = spaces.Box(-1, 1, (N_J,), np.float32)
        self.obs_dim = 2 + 3 + 3 + N_J * 2 + 6 + 1
        self.observation_space = spaces.Box(-np.inf, np.inf, (self.obs_dim,), np.float32)
        m = self.model
        self._qadr = np.array([m.joint(f"{l}_{j}").qposadr[0] for l in LEG_NAMES for j in JOINT_NAMES])
        self._dadr = np.array([m.joint(f"{l}_{j}").dofadr[0] for l in LEG_NAMES for j in JOINT_NAMES])
        self._base_gain = m.actuator_gainprm[:, 0].copy()
        self._base_bias = m.actuator_biasprm[:, 1].copy()
        self._base_kv = m.actuator_biasprm[:, 2].copy()
        self._base_frc = m.actuator_forcerange.copy()
        self._base_fric = m.geom_friction.copy()
        self._base_tmass = float(m.body_mass[m.body('torso').id])
        self._mass = float(np.sum(m.body_mass))
        self._torso_geom = m.geom('torso_geom').id
        self._torso = m.body("torso").id
        self.sensor_dropout_legs: set[int] = set()
        self.locked: dict[int, float] = {}
        self.active_faults: list[Fault] = []
        self._last_q = None
        self.t = 0.0

    # ---- helpers
    def action_to_q(self, a):
        return np.clip(self.q_nom + np.asarray(a) * self.scale, self.q_lo, self.q_hi)

    def q_to_action(self, q):
        return np.clip((np.asarray(q) - self.q_nom) / self.scale, -1, 1)

    @property
    def q(self):
        return self.data.qpos[self._qadr].copy()

    @property
    def qd(self):
        return self.data.qvel[self._dadr].copy()

    def contacts(self):
        return np.array([self.data.sensor(f"{l}_contact").data[0] for l in LEG_NAMES])

    def euler(self):
        q = self.data.qpos[3:7]
        w, x, y, z = q
        roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
        yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return roll, pitch, yaw

    def body_vel(self):
        return self.data.sensor("body_vel").data.copy()  # body frame

    def world_xy(self):
        return self.data.qpos[:2].copy()

    # ---- gym API
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._seed = seed
            self.rng = np.random.default_rng(seed)
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        t = self.params.terrain
        if t["kind"] == "rough":
            nrow, ncol = m.hfield_nrow[0], m.hfield_ncol[0]
            m.hfield_data[:] = hfield_data(t["level"], self._seed, nrow, ncol).ravel()
        # restore actuator params
        m.actuator_gainprm[:, 0] = self._base_gain
        m.actuator_biasprm[:, 1] = -self._base_gain
        m.actuator_biasprm[:, 2] = self._base_kv
        m.actuator_forcerange[:] = self._base_frc
        m.geom_friction[:] = self._base_fric
        m.body_mass[self._torso] = self._base_tmass
        if self.rand > 0:  # per-episode randomization, scaled by `rand` (0.1 = +-10%-ish)
            r = self.rand
            m.geom_friction[:, 0] = self._base_fric[:, 0] * self.rng.uniform(1 - 2 * r, 1 + 2 * r)
            g = self.rng.uniform(1 - 1.5 * r, 1 + 1.5 * r)
            m.actuator_gainprm[:, 0] = self._base_gain * g
            m.actuator_biasprm[:, 1] = -self._base_gain * g
            m.body_mass[self._torso] = self._base_tmass * self.rng.uniform(1 - r, 1 + r)
        d.qpos[2] = self.params.spawn_height + 0.02
        if t["kind"] == "slope":
            th = np.radians(t["deg"])
            d.qpos[2] += 0.0
            # tilt body to match slope: rotation about y by -th
            d.qpos[3:7] = [np.cos(-th / 2), 0, np.sin(-th / 2), 0]
        d.qpos[self._qadr] = self.q_nom + (self.rng.normal(0, 0.03 * self.rand * 10, N_J) if self.rand > 0 else 0)
        if self.rand > 0:
            yaw = self.rng.normal(0, 0.05)
            q0 = d.qpos[3:7].copy(); qz = np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)])
            mujoco.mju_mulQuat(d.qpos[3:7], q0, qz)
        d.ctrl[:] = self.q_nom
        mujoco.mj_forward(m, d)
        self.t = 0.0
        self.sensor_dropout_legs = set()
        self.locked = {}
        self.active_faults = []
        self._pending = sorted(self.fault_list, key=lambda f: f.time)
        self._pushes = sorted(self.push_list)
        self.energy = 0.0
        self.x0 = d.qpos[0]
        self.fell = False
        self._last_q = self.q.copy()
        self._hold = self.q_nom.copy()
        return self._obs(), {}

    def inject_fault(self, f: Fault):
        m = self.model
        self.active_faults.append(f)
        legs = [f.leg]
        if f.kind == "disable_leg":
            for j in range(3):
                a = f.leg * 3 + j
                m.actuator_gainprm[a, 0] = 0.0
                m.actuator_biasprm[a, 1] = 0.0
                m.actuator_biasprm[a, 2] = 0.02 * self._base_kv[a]
                m.actuator_forcerange[a] = [0, 0]
        elif f.kind == "lock_joint":
            self.locked[f.leg * 3 + f.joint] = float(self.q[f.leg * 3 + f.joint]) if f.angle is None else float(f.angle)
        elif f.kind == "reduce_torque":
            for j in range(3):
                a = f.leg * 3 + j
                m.actuator_forcerange[a] = self._base_frc[a] * f.severity
        elif f.kind == "sensor_dropout":
            self.sensor_dropout_legs.add(f.leg)
        return legs

    def _obs(self):
        roll, pitch, _ = self.euler()
        gyro = self.data.sensor("imu_gyro").data
        q, qd, c = self.q, self.qd, self.contacts()
        vx = self.body_vel()[0]
        for l in self.sensor_dropout_legs:
            q[l * 3:l * 3 + 3] = self._last_q[l * 3:l * 3 + 3]
            qd[l * 3:l * 3 + 3] = 0.0
            c[l] = 0.0
        self._last_q = q.copy()
        self.last_sensed_q = q
        self.last_contacts = c
        o = np.concatenate([[roll, pitch], gyro * 0.3, [vx, 0, 0], (q - self.q_nom), qd * 0.1,
                            (c > 0.01).astype(float), [self.target_speed]])
        return o.astype(np.float32)

    def step(self, action):
        d, m = self.data, self.model
        q_cmd = self.action_to_q(action)
        for k, v in self.locked.items():
            q_cmd[k] = v
        while self._pending and self.t >= self._pending[0].time:
            self.inject_fault(self._pending.pop(0))
        x_before = d.qpos[0]
        e = 0.0
        for _ in range(self.substeps):
            d.ctrl[:] = q_cmd
            d.xfrc_applied[self._torso, :] = 0
            for (pt, fx, fy, dur) in self._pushes:
                if pt <= self.t < pt + dur:
                    d.xfrc_applied[self._torso, 0] = fx
                    d.xfrc_applied[self._torso, 1] = fy
            mujoco.mj_step(m, d)
            e += float(np.sum(np.abs(d.actuator_force * d.qvel[self._dadr])) * self.params.dt)
            self.t += self.params.dt
        self.energy += e
        roll, pitch, _ = self.euler()
        up_z = np.cos(roll) * np.cos(pitch)
        torso_hit = any(self._torso_geom in (c.geom1, c.geom2) for c in d.contact[:d.ncon])
        self.fell = bool(up_z < 0.5 or torso_hit or np.isnan(d.qpos).any())
        vx = (d.qpos[0] - x_before) / self.dt
        cmd = np.asarray(action)
        r_vel = np.exp(-4 * (vx - self.target_speed) ** 2)
        r_energy = -0.002 * e / self.dt
        r_stab = -0.5 * (roll ** 2 + pitch ** 2) - 0.02 * abs(d.qpos[1])
        r_smooth = -0.01 * float(np.sum((cmd - getattr(self, "_prev_a", cmd)) ** 2))
        self._prev_a = cmd.copy()
        reward = 1.0 * r_vel + r_energy + r_stab + r_smooth - (5.0 if self.fell else 0.0)
        terminated = self.fell
        truncated = self.t >= self.max_time
        info = {"vx": vx, "roll": roll, "pitch": pitch, "x": d.qpos[0], "t": self.t, "energy": self.energy,
                "fell": self.fell, "faults": [f.describe() for f in self.active_faults]}
        return self._obs(), float(reward), terminated, truncated, info

    def distance(self):
        return float(self.data.qpos[0] - self.x0)

    def cot(self):
        dist = max(self.distance(), 1e-3)
        return self.energy / (self._mass * 9.81 * dist)
