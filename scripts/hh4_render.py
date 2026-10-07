"""HexaHeal v4 Stage 4: deterministic re-render (seeds 0-9 IN ORDER, no selection). MuJoCo simulation only.
Fixed 3/4 camera with a slow orbit, failed legs red after the fault, 0.25x slow motion for 1 s of sim time around the fault (3.5-4.5 s), HUD per robot: state, live speed (1 s window), failed legs, timer, FELL label.
Usage: hh4_render.py CASE CTRL   (CTRL: tripod | v1 | final)  -> docs/media_v4/grid_<case>_<ctrl>.mp4 (5x2, 1920x600), results/v4/grid_<case>_<ctrl>.json
Needs LD_LIBRARY_PATH=~/osm/usr/lib/x86_64-linux-gnu MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa. Frames stream through /tmp memmaps."""
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

FPS, W, H = 15, 384, 300
SLOW = (FAULT_T - 0.5, FAULT_T + 0.5)
BG, TEAL, ALERT, FG, DIM = (13, 17, 23), (45, 212, 191), (255, 93, 93), (230, 237, 243), (139, 148, 158)
LEGN = ["R1", "R2", "R3", "L1", "L2", "L3"]
NAME = {"tripod": "plain tripod", "v1": "healing v1", "final": "final controller (Tier B)"}
font = {k: _font(k) for k in (13, 16, 22)}


def build(name, seed):
    if name == "tripod": return TripodController()
    if name == "v1": return HealingController(tuned(), terrain="flat", seed=seed)
    return make("B", **json.load(open("results/v3/v2_config_final.json"))["B"])


def hud_state(ctrl, name, t, t_diag):
    if t < FAULT_T: return "NORMAL"
    if name == "tripod": return "FAULT"
    s = getattr(ctrl, "state", "NORMAL")
    if s == "PLAN": return "DIAGNOSED" if t - t_diag < 0.5 else "STANDING + REPLANNING"
    if s == "RUN": return "WALKING"
    return "FAULT"


def episode(name, seed, path, legs):
    ctrl = build(name, seed)
    if hasattr(ctrl, "seed"): ctrl.seed = seed
    env = HexapodEnv("flat", max_time=T_END, faults=[Fault("disable_leg", FAULT_T, leg=lg) for lg in legs], rand=0.1, seed=seed, target_speed=TARGET_SPEED)
    env.reset(seed=seed); ctrl.reset()
    m = env.model
    leg_geoms = [g for g in range(m.ngeom) for lg in legs if (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.geom_bodyid[g]) or "").startswith(LEGN[lg] + "_")]
    rend = mujoco.Renderer(m, H, W); cam = mujoco.MjvCamera(); cam.distance, cam.elevation = 1.25, -24
    n_max = int((T_END + 1.0) * FPS * 1.2) + 20
    mm = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8, shape=(n_max, H, W, 3))
    meta, nxt, k, hist, red, t_diag = [], 0.0, 0, [], False, 1e9
    while True:
        _, _, te, tr, _ = env.step(ctrl.act(env))
        t = env.t; hist.append((t, env.data.qpos[0]))
        if getattr(ctrl, "state", "") == "PLAN" and t_diag > 1e8: t_diag = t
        if t >= FAULT_T and not red:
            for g in leg_geoms: m.geom_rgba[g] = [1.0, 0.25, 0.25, 1.0]
            red = True
        if t + 1e-9 >= nxt or te or tr:
            dt = (1.0 / FPS) * (0.25 if SLOW[0] <= t < SLOW[1] else 1.0)
            nxt += dt
            cam.azimuth = 120 + 5.0 * t; cam.lookat[:] = env.data.qpos[:3]
            rend.update_scene(env.data, cam); mm[k] = rend.render()
            t0 = [h for h in hist if h[0] >= t - 1.0][0]
            sp = float((env.data.qpos[0] - t0[1]) / max(t - t0[0], 1e-6)) if t >= 1.0 else 0.0  # forward (x) speed over the last 1 s, same axis as the recovered metric
            meta.append((t, sp, hud_state(ctrl, name, t, t_diag))); k += 1
        if te or tr: break
    rend.close(); mm.flush(); json.dump(meta, open(path + '.json', 'w'))
    return meta, bool(env.fell), float(env.t), k


def tile(fr, seed, meta, fell, t_end, legs, slow):
    t, sp, st = meta
    im = Image.fromarray(np.asarray(fr)); d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 0, W, 44], fill=BG + (215,))
    d.text((6, 3), f"seed {seed}", font=font[16], fill=FG)
    col = ALERT if st in ("FAULT",) else (TEAL if st in ("WALKING", "NORMAL") else (255, 200, 80))
    d.text((6, 24), st, font=font[13], fill=col)
    d.text((W - 150, 3), f"{sp:5.2f} m/s", font=font[16], fill=FG)
    d.text((W - 150, 24), f"t = {min(t, T_END):4.1f} s" + ("  0.25x" if slow else ""), font=font[13], fill=DIM)
    d.rectangle([0, H - 22, W, H], fill=BG + (215,))
    d.text((6, H - 19), ("failed: " + "+".join(LEGN[lg] for lg in legs) if t >= FAULT_T else "no fault yet") + "   |   Simulation", font=font[13], fill=ALERT if t >= FAULT_T else DIM)
    if fell: d.rectangle([0, 44, W, H - 22], fill=(160, 0, 0, 70)); d.text((W // 2 - 55, H // 2 - 14), f"FELL {t_end:.1f} s", font=font[22], fill=(255, 255, 255))
    return np.asarray(im)


if __name__ == "__main__":
    CASE, name = sys.argv[1], sys.argv[2]
    legs = case_legs(CASE); tag = case_name(CASE).replace("+", "_")
    os.makedirs("docs/media_v4", exist_ok=True)
    paths = [f"/tmp/hh4grid_{name}_{sd}.npy" for sd in range(10)]
    eps = [episode(name, sd, paths[sd], legs) if not os.path.exists(paths[sd] + '.json') else None for sd in range(10)]
    mms = [np.load(p, mmap_mode="r") for p in paths]
    json.dump([dict(seed=sd, fell=e[1], t_end=e[2], final_speed=e[0][-1][1]) for sd, e in enumerate(eps)], open(f"results/v4/grid_{tag}_{name}.json", "w"), indent=1)
    nfr = max(e[3] for e in eps)
    with imageio.get_writer(f"docs/media_v4/grid_{tag}_{name}.mp4", fps=FPS, codec="libx264", quality=None, ffmpeg_params=["-crf", "22", "-pix_fmt", "yuv420p", "-preset", "veryfast"]) as w:
        for f in range(nfr):
            tiles = []
            for sd, (meta, fell, tend, n) in enumerate(eps):
                i = min(f, n - 1)
                tiles.append(tile(mms[sd][i], sd, meta[i], fell and f >= n - 1, tend, legs, SLOW[0] <= meta[i][0] < SLOW[1]))
            w.append_data(np.vstack([np.hstack(tiles[:5]), np.hstack(tiles[5:])]))
    print("done", name)
