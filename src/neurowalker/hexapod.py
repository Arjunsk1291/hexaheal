"""Procedural MJCF generation for a parameterized 18-DOF hexapod (6 legs x 3 joints)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LEG_NAMES = ["R1", "R2", "R3", "L1", "L2", "L3"]  # right front/mid/rear, left front/mid/rear
JOINT_NAMES = ["coxa", "femur", "tibia"]
TRIPOD_A = (0, 2, 4)  # R1, R3, L2
TRIPOD_B = (1, 3, 5)  # R2, L1, L3


@dataclass
class HexapodParams:
    body_half: tuple = (0.16, 0.07, 0.025)  # torso box half extents
    leg_x: tuple = (0.12, 0.0, -0.12)  # leg mount x positions (front, mid, rear)
    coxa_len: float = 0.04
    femur_len: float = 0.09
    tibia_len: float = 0.14
    torso_mass: float = 1.0
    kp: float = 8.0
    kv: float = 0.4
    torque_limit: float = 2.5
    dt: float = 0.005
    foot_friction: float = 1.2
    nominal: tuple = (0.0, 0.2, 1.2)  # coxa, femur, tibia nominal angles (rad)
    ranges: tuple = ((-0.7, 0.7), (-0.8, 1.4), (0.2, 2.3))
    terrain: dict = field(default_factory=lambda: {"kind": "flat"})

    @property
    def spawn_height(self) -> float:
        a, b = self.nominal[1], self.nominal[2]
        return self.femur_len * np.sin(a) + self.tibia_len * np.sin(a + b) + 0.02


def _leg_xml(i: int, p: HexapodParams) -> str:
    side = -1 if i < 3 else 1  # right legs point -y
    x = p.leg_x[i % 3]
    yaw = side * np.pi / 2
    zax = "0 0 1" if side < 0 else "0 0 -1"  # positive coxa = swing forward on both sides
    n = LEG_NAMES[i]
    r = p.ranges
    return f"""
    <body name="{n}_coxa" pos="{x} {side * p.body_half[1]} 0" euler="0 0 {yaw}">
      <joint name="{n}_coxa" axis="{zax}" range="{r[0][0]} {r[0][1]}" damping="0.05" armature="0.004"/>
      <geom type="capsule" fromto="0 0 0 {p.coxa_len} 0 0" size="0.012" mass="0.03" rgba="0.2 0.5 0.9 1" contype="0" conaffinity="0"/>
      <body name="{n}_femur" pos="{p.coxa_len} 0 0">
        <joint name="{n}_femur" axis="0 1 0" range="{r[1][0]} {r[1][1]}" damping="0.05" armature="0.004"/>
        <geom type="capsule" fromto="0 0 0 {p.femur_len} 0 0" size="0.011" mass="0.05" rgba="0.3 0.6 0.95 1" contype="0" conaffinity="0"/>
        <body name="{n}_tibia" pos="{p.femur_len} 0 0">
          <joint name="{n}_tibia" axis="0 1 0" range="{r[2][0]} {r[2][1]}" damping="0.05" armature="0.004"/>
          <geom type="capsule" fromto="0 0 0 {p.tibia_len} 0 0" size="0.009" mass="0.05" rgba="0.9 0.9 0.95 1" contype="0" conaffinity="0"/>
          <geom name="{n}_foot" type="sphere" pos="{p.tibia_len} 0 0" size="0.013" mass="0.01" friction="{p.foot_friction} 0.02 0.002" rgba="0.95 0.5 0.2 1"/>
          <site name="{n}_foot_site" pos="{p.tibia_len} 0 0" size="0.02" rgba="1 0 0 0.0"/>
        </body>
      </body>
    </body>"""


def terrain_xml(t: dict) -> tuple[str, str]:
    """Return (asset_xml, worldbody_xml) for a terrain spec."""
    kind = t.get("kind", "flat")
    if kind == "rough":
        return ('<hfield name="terrain" nrow="160" ncol="640" size="8 2 0.1 0.05"/>',
                '<geom name="floor" type="hfield" hfield="terrain" pos="7.5 0 0" material="grid"/>')
    if kind == "slope":
        deg = float(t.get("deg", 10))
        return ("", f'<geom name="floor" type="plane" size="40 6 0.1" euler="0 {-np.radians(deg)} 0" material="grid"/>')
    return ("", '<geom name="floor" type="plane" size="40 6 0.1" material="grid"/>')


def hfield_data(level: int, seed: int, nrow: int = 160, ncol: int = 640) -> np.ndarray:
    """Heightfield samples in [0,1] (scaled by elevation_max=0.1 m). Flat start pad then rising roughness."""
    amp = {1: 0.012, 2: 0.022, 3: 0.035}[level] / 0.1
    rng = np.random.default_rng(seed)
    coarse = rng.random((nrow // 8 + 1, ncol // 8 + 1))
    from scipy.ndimage import zoom
    h = zoom(coarse, 8, order=1)[:nrow, :ncol]
    xs = (np.arange(ncol) / ncol) * 16.0 - 0.5  # world x of each column
    ramp = np.clip((xs - 0.6) / 0.8, 0, 1)[None, :]
    return np.clip(h * amp * ramp, 0, 1)


def generate_mjcf(p: HexapodParams | None = None) -> str:
    p = p or HexapodParams()
    assets, floor = terrain_xml(p.terrain)
    legs = "".join(_leg_xml(i, p) for i in range(6))
    act, sens = [], []
    for n in LEG_NAMES:
        for j in JOINT_NAMES:
            act.append(f'<position name="{n}_{j}_act" joint="{n}_{j}" kp="{p.kp}" kv="{p.kv}" '
                       f'forcerange="-{p.torque_limit} {p.torque_limit}" ctrlrange="-3.2 3.2"/>')
            sens.append(f'<jointpos name="{n}_{j}_enc" joint="{n}_{j}"/>')
            sens.append(f'<jointvel name="{n}_{j}_vel" joint="{n}_{j}"/>')
    for n in LEG_NAMES:
        sens.append(f'<touch name="{n}_contact" site="{n}_foot_site"/>')
    bh = p.body_half
    return f"""<mujoco model="neurowalker_hexapod">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{p.dt}" integrator="implicitfast" gravity="0 0 -9.81"/>
  <visual><global offwidth="1280" offheight="1280"/><quality shadowsize="2048"/><headlight ambient="0.35 0.35 0.4" diffuse="0.7 0.7 0.7"/></visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.12 0.14 0.19" rgb2="0.17 0.19 0.26" width="256" height="256" mark="edge" markrgb="0.3 0.35 0.5"/>
    <material name="grid" texture="grid" texrepeat="40 40" reflectance="0.05"/>
    <texture name="sky" type="skybox" builtin="gradient" rgb1="0.1 0.12 0.2" rgb2="0.02 0.02 0.05" width="64" height="64"/>
    {assets}
  </asset>
  <worldbody>
    <light pos="2 -2 5" dir="-0.3 0.3 -1" diffuse="0.9 0.9 0.9" castshadow="true"/>
    {floor}
    <body name="torso" pos="0 0 {p.spawn_height}">
      <freejoint name="root"/>
      <geom name="torso_geom" type="box" size="{bh[0]} {bh[1]} {bh[2]}" mass="{p.torso_mass}" rgba="0.1 0.75 0.65 1"/>
      <geom name="head" type="sphere" pos="{bh[0] + 0.01} 0 0.005" size="0.02" mass="0.001" rgba="1 0.8 0.2 1" contype="0" conaffinity="0"/>
      <site name="imu" pos="0 0 0" size="0.01"/>
      {legs}
    </body>
  </worldbody>
  <actuator>{"".join(act)}</actuator>
  <sensor>
    <framequat name="imu_quat" objtype="site" objname="imu"/>
    <gyro name="imu_gyro" site="imu"/>
    <accelerometer name="imu_acc" site="imu"/>
    <velocimeter name="body_vel" site="imu"/>
    {"".join(sens)}
  </sensor>
</mujoco>"""
