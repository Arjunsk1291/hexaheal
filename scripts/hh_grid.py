"""HexaHeal Stage 6: 10-robot grid, one fault case, healing v1 vs v2 Tier B, seeds 0-9 IN ORDER (no selection). Simulation only.
Case chosen by a fixed rule: the case with the largest (v2 Tier B - v1) survivor difference on seeds 0-9, ties broken by lowest case index (see docs/media_hh/README.md).
Output: docs/media_hh/grid_<case>.mp4 (local, for review) and results/hh_grid_outcomes.json."""
import imageio.v2 as imageio
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "scripts")
import mujoco
from hh_common import CASES, make, tuned

from neurowalker.benchmark import FAULT_T, TARGET_SPEED
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.healing import HealingController
from neurowalker.hh_eval import T_END, case_legs, case_name
from neurowalker.render import _font

FPS, W, H = 15, 256, 192


def surv(path):
    d = {}
    for line in open(path):
        r = json.loads(line); d.setdefault(r["case"], []).append(not r["fell"])
    return {c: sum(v) for c, v in d.items()}


s1, s2 = surv("results/hh_final_v1_0-9.jsonl"), surv("results/hh_final_v2B_0-9.jsonl")
CASE = max(CASES, key=lambda c: (s2[c] - s1[c], -CASES.index(c)))
legs = case_legs(CASE)
font, small = _font(15), _font(12)


def episode(name, seed):
    ctrl = HealingController(tuned(), terrain="flat", seed=seed) if name == "v1" else make("B", **json.load(open("results/hh_v2_config.json"))["B"])
    ctrl.seed = seed
    env = HexapodEnv("flat", max_time=T_END, faults=[Fault("disable_leg", FAULT_T, leg=lg) for lg in legs], rand=0.1, seed=seed, target_speed=TARGET_SPEED)
    env.reset(seed=seed); ctrl.reset()
    rend = mujoco.Renderer(env.model, H, W); cam = mujoco.MjvCamera(); cam.distance, cam.elevation, cam.azimuth = 1.3, -22, 125
    frames, nxt = [], 0.0
    while True:
        _, _, te, tr, _ = env.step(ctrl.act(env))
        if env.t + 1e-9 >= nxt or te or tr:
            nxt += 1.0 / FPS
            cam.lookat[:] = env.data.qpos[:3]; rend.update_scene(env.data, cam)
            frames.append((np.asarray(rend.render()).copy(), env.t, bool(env.fell)))
        if te or tr: break
    return frames, bool(env.fell), float(env.t)


def tile(fr, seed, t, fell, fell_t):
    im = Image.fromarray(fr); d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 0, W, 22], fill=(5, 8, 20, 190)); d.text((6, 3), f"seed {seed}", font=small, fill=(255, 255, 255))
    d.text((W - 62, 3), f"t={min(t, T_END):4.1f}s", font=small, fill=(200, 210, 230))
    if t > FAULT_T: d.rectangle([0, H - 20, W, H], fill=(120, 20, 10, 150)); d.text((6, H - 17), "leg lost", font=small, fill=(255, 200, 190))
    if fell: d.rectangle([0, 22, W, H], fill=(160, 0, 0, 90)); d.text((W // 2 - 55, H // 2 - 10), f"FELL {fell_t:.1f}s", font=font, fill=(255, 255, 255))
    return np.asarray(im)


out, grids = {}, {}
for name in ("v1", "v2B"):
    eps = [episode(name, sd) for sd in range(10)]
    out[name] = [dict(seed=sd, fell=e[1], t_end=e[2]) for sd, e in enumerate(eps)]
    n = int(T_END * FPS) + 1
    seq = []
    for k in range(n):
        t = k / FPS; row = []
        for sd, (frames, fell, tend) in enumerate(eps):
            idx = min(range(len(frames)), key=lambda i: abs(frames[i][1] - t)) if t <= tend else len(frames) - 1
            row.append(tile(frames[idx][0], sd, t if t <= tend else tend, fell and t >= tend - 1e-9, tend))
        seq.append(np.vstack([np.hstack(row[:5]), np.hstack(row[5:])]))
    grids[name] = seq
label = lambda im, txt: (lambda i: (ImageDraw.Draw(i).rectangle([0, 0, im.shape[1], 26], fill=(10, 14, 30)), ImageDraw.Draw(i).text((8, 4), txt, font=font, fill=(120, 240, 215)), np.asarray(i))[2])(Image.fromarray(im))
frames = []
for a, b in zip(grids["v1"], grids["v2B"]):
    frames.append(np.vstack([label(a, f"tuned tripod + healing v1: {sum(not o['fell'] for o in out['v1'])}/10 survive"),
                             label(b, f"healing v2 Tier B: {sum(not o['fell'] for o in out['v2B'])}/10 survive"),
                             np.asarray(Image.new("RGB", (a.shape[1], 24), (10, 14, 30)))]))
    ImageDraw.Draw(img := Image.fromarray(frames[-1])).text((8, frames[-1].shape[0] - 20), f"MuJoCo simulation | case {case_name(CASE)} | leg lost at 4 s | seeds 0-9 in order", font=small, fill=(255, 255, 255))
    frames[-1] = np.asarray(img)
os.makedirs("docs/media_hh", exist_ok=True)
path = f"docs/media_hh/grid_{case_name(CASE).replace('+', '_')}.mp4"
with imageio.get_writer(path, fps=FPS, codec="libx264", quality=None, ffmpeg_params=["-crf", "24", "-pix_fmt", "yuv420p", "-preset", "veryfast"]) as w:
    for f in frames: w.append_data(f)
json.dump(dict(case=CASE, case_name=case_name(CASE), rule="largest (v2B - v1) survivors on seeds 0-9, ties -> lowest case index", v1_survivors=s1[CASE], v2B_survivors=s2[CASE], outcomes=out), open("results/hh_grid_outcomes.json", "w"), indent=1)
print("saved", path, CASE, out)
