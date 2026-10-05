# ruff: noqa: E402
"""Story run: one connectome-inspired + healing episode (seed 0, flat) with TWO sequential leg faults.
Fault 1 (leg 2, t=4 s) is the benchmarked scenario. Fault 2 (leg 5, t=13 s) is injected after recovery to show what the
unmodified v0.1 healing controller does with a second fault. Writes docs/story/story_run.mp4 (960x540) and story_run.npz."""
try:
    import torch  # noqa: F401
    import torch._dynamo  # noqa: F401
except ImportError:
    pass
import json
import os
import sys

import imageio.v2 as iio
import numpy as np

sys.path.insert(0, "scripts")
from neurowalker.benchmark import FAULT_T, TARGET_SPEED
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.healing import HealingController
from neurowalker.hexapod import LEG_NAMES
from neurowalker.render import EpisodeRecorder

from make_media import make_ctrl

T_END, FAULT2_T, LEG1, LEG2 = 24.0, 13.0, 2, 5
OUT = "docs/story"; os.makedirs(OUT, exist_ok=True)
ctrl = make_ctrl("connectome"); SEED = int(os.environ.get("STORY_SEED", "0")); ctrl.seed = SEED
env = HexapodEnv("flat", max_time=T_END, faults=[Fault("disable_leg", FAULT_T, leg=LEG1), Fault("disable_leg", FAULT2_T, leg=LEG2)],
                 pushes=[], rand=0.1, seed=SEED, target_speed=TARGET_SPEED)
c = HealingController(ctrl, terrain="flat", seed=SEED)
env.reset(seed=SEED); c.reset()
rec = EpisodeRecorder(env, 960, 540, 30, cam_dist=1.0)
rec._overlay = lambda img, speed, extra: img
import mujoco
m = env.model
def tint(leg):
    pre = LEG_NAMES[leg] + "_"
    for b in range(m.nbody):
        if mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b).startswith(pre):
            for g in range(m.ngeom):
                if m.geom_bodyid[g] == b and m.geom_contype[g] == 0 and m.geom_conaffinity[g] == 0 and m.geom_rgba[g][3] > 0:
                    m.geom_matid[g] = -1; m.geom_rgba[g] = [1.0, 0.12, 0.08, 1.0]
tinted = 0
w = iio.get_writer(f"{OUT}/story_run.mp4", fps=30, codec="libx264", quality=None, ffmpeg_params=["-crf", "22", "-pix_fmt", "yuv420p", "-preset", "veryfast"])
T, X, ST, NF, SP, NEU = [], [], [], [], [], []
acc = None; last_x, last_t, v = 0.0, 0.0, 0.0
while True:
    a = c.act(env)
    _, _, te, tr, info = env.step(a)
    if env.t - last_t >= 0.2:
        v = (env.data.qpos[0] - last_x) / (env.t - last_t); last_x, last_t = env.data.qpos[0], env.t
    for i in range(tinted, len(env.active_faults)):
        tint(env.active_faults[i].leg)
    tinted = len(env.active_faults)
    acc = ctrl.last_counts.astype(np.int32) if acc is None else acc + ctrl.last_counts
    if int(round(env.t / env.dt)) % 5 == 0:
        NEU.append(np.minimum(acc, 99).astype(np.int8)); acc = None
    if env.t + 1e-9 >= rec._next_t:
        rec._next_t += 1.0 / 30
        rec.cam.lookat[:] = env.data.qpos[:3]
        rec.renderer.update_scene(env.data, rec.cam)
        w.append_data(rec.renderer.render().copy())
        T.append(env.t); X.append(float(env.data.qpos[0])); ST.append(c.state); NF.append(len(env.active_faults)); SP.append(v)
    if te or tr: break
w.close()
np.savez_compressed(f"{OUT}/story_run.npz", t=np.array(T), x=np.array(X), speed=np.array(SP), nfaults=np.array(NF), state=np.array(ST), neural=np.array(NEU))
json.dump({"log": c.log, "fell": bool(env.fell), "t_end": float(env.t), "t_detect": c.t_detect, "t_recover": c.t_recover, "adapt_info": {k: (v if isinstance(v, (int, float, str)) else str(v)) for k, v in getattr(c, "adapt_info", {}).items()},
           "faults": [f.describe() for f in env.active_faults]}, open(f"{OUT}/story_run_log.json", "w"), indent=1, default=str)
print("story run done", len(T), "frames, fell", env.fell, flush=True)
