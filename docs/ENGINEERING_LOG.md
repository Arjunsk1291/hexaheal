# Engineering log

Decisions, deviations and measured findings, appended per phase. Environment for all measurements unless stated:
2 vCPU Linux sandbox, 1.5 GB RAM, no GPU, no Docker, Python 3.10, MuJoCo 3.14. **Nothing was run on the owner's GTX 1660 Ti laptop.**

## Phase 0 - preflight and scaffold
- Preflight (`scripts/preflight.py`, `results/preflight.json`): Docker and nvidia-smi absent in the build sandbox, so the Docker/ROS 2 layer is written but **not executed** here (see Phase 7).
- Headless GL: EGL fails (no device), so rendering uses OSMesa. `render.pick_gl_backend()` tries EGL, then OSMesa, then GLFW.
- Core package has no ROS dependency.

## Phase 1 - simulation core
- Procedural MJCF: 6 legs x (coxa, femur, tibia), position actuators (kp=8, kv=0.4, +-2.5 N m), IMU, touch sensors, joint encoders.
- Terrains: flat, heightfield rough L1/L2/L3 (noise amplitude 1.2/2.2/3.5 cm), slopes 10/15/20 deg. Faults: disable_leg, lock_joint, reduce_torque, sensor_dropout, triggered at a chosen time. Pushes: force pulses on the torso.
- Measured: ~3,500-4,900 control steps/s (0.02 s each), i.e. 70-100x real time for the bare physics.
- Fall detection uses torso-geom contact or up-vector z < 0.5 (an absolute height check gave false falls on downhill slopes).

## Phase 2 - tripod baseline
- Tuned by a small grid (freq 1-2 Hz, stride 0.2-0.4, lift 0.3-0.5). Defaults: 1.5 Hz, stride 0.35, lift 0.35, duty 0.55.
- Finding (not hidden): the tripod gait walks flat, rough L1-L3 and a 10 deg slope, but **falls on 15 and 20 deg slopes** in most seeds.
