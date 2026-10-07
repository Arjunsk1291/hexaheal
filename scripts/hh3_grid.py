"""HexaHeal v3 Stage 6: 10-robot grid clips for ONE case, seeds 0-9 IN ORDER (no selection), MuJoCo simulation. Usage: hh3_grid.py CASE CTRL [CTRL ...]  (tripod|v1|v2B)
Case is fixed by the order's storyboard (R2+L3 = dl_1_5). Frames stream to /tmp memmaps (2 GB RAM limit). Output: docs/media_v3/grid_<case>_<ctrl>.mp4 (5x2 tiles, 1600x480) and results/v3/grid_<case>_<ctrl>.json (outcomes).
Needs: LD_LIBRARY_PATH=~/osm/usr/lib/x86_64-linux-gnu MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa (and NOT for PPO)."""
import json
import os
import sys

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "scripts")
from hh_common import make, tuned

from neurowalker.benchmark import FAULT_T, TARGET_SPEED
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.healing import HealingController
from neurowalker.hh_eval import T_END, case_legs, case_name
from neurowalker.render import _font
from neurowalker.tripod import TripodController

FPS, W, H = 15, 320, 240
CASE = sys.argv[1]
legs = case_legs(CASE)
font, small = _font(20), _font(15)
NAME = {"tripod": "plain tripod", "v1": "tuned tripod + healing v1", "v2B": "healing v2 Tier B (online)"}


def build(name, seed):
    if name == "tripod": return TripodController()
    if name == "v1": return HealingController(tuned(), terrain="flat", seed=seed)
    return make("B", **json.load(open("results/v3/v2_config_base.json"))["B"])


def episode(name, seed, path):
    ctrl = build(name, seed)
    if hasattr(ctrl, "seed"): ctrl.seed = seed
    env = HexapodEnv("flat", max_time=T_END, faults=[Fault("disable_leg", FAULT_T, leg=lg) for lg in legs], rand=0.1, seed=seed, target_speed=TARGET_SPEED)
    env.reset(seed=seed); ctrl.reset()
    rend = mujoco.Renderer(env.model, H, W); cam = mujoco.MjvCamera(); cam.distance, cam.elevation, cam.azimuth = 1.3, -22, 125
    n_max = int(T_END * FPS) + 2
    mm = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8, shape=(n_max, H, W, 3))
    times, nxt, k = [], 0.0, 0
    while True:
        _, _, te, tr, _ = env.step(ctrl.act(env))
        if env.t + 1e-9 >= nxt or te or tr:
            nxt += 1.0 / FPS
            cam.lookat[:] = env.data.qpos[:3]; rend.update_scene(env.data, cam)
            mm[k] = rend.render(); times.append(env.t); k += 1
        if te or tr: break
    mm.flush(); rend.close()
    return np.array(times), bool(env.fell), float(env.t), k


def tile(fr, seed, t, fell, fell_t):
    im = Image.fromarray(np.asarray(fr)); d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 0, W, 26], fill=(5, 8, 20, 190)); d.text((6, 4), f"seed {seed}", font=small, fill=(255, 255, 255))
    d.text((W - 92, 4), f"t={min(t, T_END):4.1f}s", font=small, fill=(200, 210, 230))
    if t > FAULT_T: d.rectangle([0, H - 24, W, H], fill=(120, 20, 10, 150)); d.text((6, H - 21), "leg lost  |  MuJoCo simulation", font=small, fill=(255, 215, 205))
    else: d.rectangle([0, H - 24, W, H], fill=(10, 10, 30, 150)); d.text((6, H - 21), "healthy  |  MuJoCo simulation", font=small, fill=(210, 220, 240))
    if fell: d.rectangle([0, 26, W, H - 24], fill=(160, 0, 0, 90)); d.text((W // 2 - 60, H // 2 - 14), f"FELL {fell_t:.1f}s", font=font, fill=(255, 255, 255))
    return np.asarray(im)


os.makedirs("docs/media_v3", exist_ok=True)
for name in sys.argv[2:]:
    paths = [f"/tmp/hh3grid_{name}_{sd}.npy" for sd in range(10)]
    eps = [episode(name, sd, paths[sd]) for sd in range(10)]
    mms = [np.load(p, mmap_mode="r") for p in paths]
    tag = case_name(CASE).replace("+", "_")
    json.dump([dict(seed=sd, fell=e[1], t_end=e[2]) for sd, e in enumerate(eps)], open(f"results/v3/grid_{tag}_{name}.json", "w"), indent=1)
    with imageio.get_writer(f"docs/media_v3/grid_{tag}_{name}.mp4", fps=FPS, codec="libx264", quality=None, ffmpeg_params=["-crf", "22", "-pix_fmt", "yuv420p", "-preset", "veryfast"]) as w:
        for k in range(int(T_END * FPS) + 1):
            t = k / FPS; tiles = []
            for sd, (times, fell, tend, n) in enumerate(eps):
                i = int(np.argmin(np.abs(times - min(t, tend)))) if t <= tend else n - 1
                tiles.append(tile(mms[sd][i], sd, min(t, tend), fell and t >= tend - 1e-9, tend))
            w.append_data(np.vstack([np.hstack(tiles[:5]), np.hstack(tiles[5:])]))
    for p in paths: os.remove(p)
    print(name, case_name(CASE), "upright", sum(not e[1] for e in eps), "of 10", flush=True)
