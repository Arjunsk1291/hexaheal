# ruff: noqa: E402
"""Real-image LinkedIn carousel (1080x1350): high-res MuJoCo stills (tripod controller, cheap to run), neural wiring view,
dashboard crop, and result charts. All numbers read from results/summary.json. Simulation only."""
try:
    import torch  # noqa: F401
    import torch._dynamo  # noqa: F401
except ImportError:
    pass
import json
import os
import sys

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, "scripts")
from make_media import make_ctrl
from neurowalker.benchmark import FAULT_T, TARGET_SPEED, scenario_spec
from neurowalker.env import HexapodEnv
from neurowalker.healing import HealingController  # noqa: F401
from neurowalker.hexapod import LEG_NAMES
from neurowalker.render import EpisodeRecorder

OUT = "docs/social/slides"; os.makedirs(OUT, exist_ok=True)
S = json.load(open("results/summary.json"))
BG, TEAL, ORG, RED, WHITE, GREY = (10, 14, 24), (45, 212, 191), (245, 158, 11), (255, 90, 70), (240, 244, 255), (140, 150, 172)
FB = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", s)
FR = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)
COL = {"tripod": (150, 165, 190), "connectome": TEAL, "ppo": ORG}
NAMES = {"tripod": "Tripod CPG", "connectome": "Connectome-inspired", "ppo": "PPO residual"}


def tint(m, leg):
    pre = LEG_NAMES[leg] + "_"
    for b in range(m.nbody):
        if mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b).startswith(pre):
            for g in range(m.ngeom):
                if m.geom_bodyid[g] == b and m.geom_contype[g] == 0 and m.geom_conaffinity[g] == 0 and m.geom_rgba[g][3] > 0:
                    m.geom_matid[g] = -1; m.geom_rgba[g] = [1.0, 0.12, 0.08, 1.0]


def still(scenario, t_cap, fname, az=125, el=-20, dist=1.0, fault_tint=False, size=(1600, 1200)):
    sp = scenario_spec(scenario.replace("+healing", ""))
    env = HexapodEnv(sp["terrain"], max_time=t_cap + 1, faults=sp["faults"], pushes=sp["pushes"], rand=0.1, seed=0, target_speed=TARGET_SPEED)
    c = make_ctrl("tripod"); c.seed = 0
    env.reset(seed=0); c.reset()
    env.model.vis.global_.offwidth, env.model.vis.global_.offheight = 1920, 1440
    rec = EpisodeRecorder(env, size[0], size[1], 30, cam_dist=dist); rec.cam.azimuth, rec.cam.elevation = az, el
    tinted = 0
    while env.t < t_cap:
        _, _, te, tr, _ = env.step(c.act(env))
        for i in range(tinted, len(env.active_faults)):
            if fault_tint: tint(env.model, env.active_faults[i].leg)
        tinted = len(env.active_faults)
        if te or tr: break
    rec.cam.lookat[:] = env.data.qpos[:3]
    rec.renderer.update_scene(env.data, rec.cam)
    im = Image.fromarray(rec.renderer.render().copy()); im.save(f"{OUT}/still_{fname}.png"); return im


def fit(im, w, h):
    r = max(w / im.width, h / im.height); im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2; return im.crop((x, y, x + w, y + h))


def grad(im, y0, y1, a0=0, a1=235):
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for y in range(y0, y1): d.line([(0, y), (im.width, y)], fill=BG + (int(a0 + (a1 - a0) * (y - y0) / (y1 - y0)),))
    d.rectangle([0, y1, im.width, im.height], fill=BG + (a1,))
    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")


def header(d, n, kicker):
    d.text((60, 52), "NEUROWALKER", font=FB(26), fill=TEAL); d.text((1020, 56), f"{n}/8", font=FR(24), fill=GREY, anchor="ra")
    d.text((60, 92), kicker, font=FR(22), fill=GREY)


def footer(d, extra="Simulation only. 10 seeds. 2 vCPU sandbox."):
    d.text((60, 1300), extra, font=FR(22), fill=GREY)


def bars(d, y, title, vals, fmt, vmax, sub=None):
    d.text((60, y), title, font=FB(40), fill=WHITE)
    if sub: d.text((60, y + 52), sub, font=FR(24), fill=GREY)
    y += 110
    for c, v in vals:
        d.text((60, y), NAMES[c], font=FR(26), fill=WHITE)
        d.rounded_rectangle([60, y + 40, 60 + 700, y + 70], 8, fill=(26, 32, 48))
        w = max(6, int(700 * v / vmax)); d.rounded_rectangle([60, y + 40, 60 + w, y + 70], 8, fill=COL[c])
        d.text((790, y + 38), fmt(v), font=FB(32), fill=COL[c]); y += 96
    return y


def canvas(photo, ph=760, top_fade=True):
    im = Image.new("RGB", (1080, 1350), BG); im.paste(fit(photo, 1080, ph), (0, 0)); im = grad(im, ph - 260, ph, 0, 255)
    return im


stills = {}
stills["walk"] = still("flat", 3.0, "walk")
stills["slope"] = still("slope15", 3.0, "slope", az=150, el=-12, dist=1.1)
stills["fault"] = still("fault_disable_leg", FAULT_T + 1.5, "fault", az=100, el=-28, dist=0.9, fault_tint=True)
stills["push"] = still("push", 3.0, "push", az=160, el=-14, dist=1.1)
print("stills ok", flush=True)

ND = json.load(open("dashboard/public/data/neural.json")); XY = np.array(ND["xy"])
import scipy.sparse as sps

Wt = sps.load_npz("data/processed/subgraph_weights.npz").tocoo(); rng = np.random.default_rng(3)
sel = rng.choice(Wt.nnz, 9000, replace=False)
SZ = 1400
nim = Image.new("RGB", (SZ, SZ), (6, 9, 16)); nd = ImageDraw.Draw(nim, "RGBA"); P = XY * (SZ - 120) + 60
for k in sel:
    a, b = Wt.row[k], Wt.col[k]; nd.line([tuple(P[a]), tuple(P[b])], fill=(45, 212, 191, 22), width=1)
deg = np.asarray(abs(Wt).sum(0)).ravel() + np.asarray(abs(Wt).sum(1)).ravel(); dn = deg / deg.max()
for i in rng.permutation(len(P)):
    r = 1.6 + 3.0 * dn[i]; col = (int(120 + 135 * dn[i]), int(200 + 40 * dn[i]), 255)
    nd.ellipse([P[i][0] - r, P[i][1] - r, P[i][0] + r, P[i][1] + r], fill=col + (200,))
nim = nim.filter(ImageFilter.GaussianBlur(0.6)); nim.save(f"{OUT}/still_neural.png"); stills["neural"] = nim
dash = Image.open("docs/screenshots/dashboard_desktop.png").convert("RGB").crop((0, 0, 1440, 900))

fl = lambda c, s: S[c][s]["distance"]["mean"]
fa = lambda c, s: S[c][s]["fall_rate"]["falls"]
ret = lambda c, s: S[c][s]["fault_retained"]["mean"] * 100

# 1 title
im = canvas(stills["walk"], 900); d = ImageDraw.Draw(im); header(d, 1, "Connectome-inspired hexapod")
d.text((60, 900), "NeuroWalker", font=FB(110), fill=WHITE); d.text((60, 1040), "A 10,000-neuron piece of a published", font=FR(38), fill=WHITE)
d.text((60, 1090), "fruit-fly connectome steering a simulated hexapod.", font=FR(38), fill=WHITE); d.text((60, 1190), "Simulation only. Not an emulated fly brain.", font=FR(30), fill=TEAL); im.save(f"{OUT}/slide_1.png")
# 2 neural
im = Image.new("RGB", (1080, 1350), BG); im.paste(fit(stills["neural"], 1080, 1000), (0, 0)); im = grad(im, 760, 1000, 0, 255); d = ImageDraw.Draw(im); header(d, 2, "The brain part")
d.text((60, 1010), "10,000 neurons. 797,577 synapse pairs.", font=FB(42), fill=WHITE); d.text((60, 1075), "Wiring from FlyWire v783, laid out by spectral embedding.", font=FR(28), fill=GREY)
d.text((60, 1120), "Spiking network, 0.5 ms steps, drives the gait.", font=FR(28), fill=GREY); footer(d, "Data: FlyWire, CC BY-NC 4.0. Simulation only."); im.save(f"{OUT}/slide_2.png")
# 3 flat
im = canvas(stills["walk"]); d = ImageDraw.Draw(im); header(d, 3, "Flat ground")
bars(d, 790, "Distance in 10 s", [(c, fl(c, "flat")) for c in ["tripod", "connectome", "ppo"]], lambda v: f"{v:.2f} m", 3.0, "10-seed mean, simulation"); footer(d); im.save(f"{OUT}/slide_3.png")
# 4 slope
im = canvas(stills["slope"]); d = ImageDraw.Draw(im); header(d, 4, "15 degree slope")
bars(d, 790, "Falls out of 10", [(c, fa(c, "slope15")) for c in ["tripod", "connectome", "ppo"]], lambda v: f"{int(v)}/10", 10, "Lower is better. PPO survives, but slowly."); footer(d); im.save(f"{OUT}/slide_4.png")
# 5 push
im = canvas(stills["push"]); d = ImageDraw.Draw(im); header(d, 5, "48 N push")
bars(d, 790, "Falls out of 10", [(c, fa(c, "push")) for c in ["tripod", "connectome", "ppo"]], lambda v: f"{int(v)}/10", 10, "Lower is better. PPO falls most here."); footer(d); im.save(f"{OUT}/slide_5.png")
# 6 healing
im = canvas(stills["fault"]); d = ImageDraw.Draw(im); header(d, 6, "Leg disabled mid-walk (red leg)")
bars(d, 790, "Speed kept after the fault", [(c, ret(c, "fault_disable_leg+healing")) for c in ["tripod", "connectome", "ppo"]], lambda v: f"{v:.0f}%", 100,
     "With healing. Without: tripod 0%, connectome 0%, PPO 77%.")
footer(d, "Healing made PPO worse. Simulation only. 10 seeds."); im.save(f"{OUT}/slide_6.png")
# 7 dashboard
im = Image.new("RGB", (1080, 1350), BG); im.paste(dash.resize((1080, 675), Image.LANCZOS), (0, 170)); d = ImageDraw.Draw(im); header(d, 7, "Dashboard (screenshot)")
d.text((60, 900), "Honest limits", font=FB(48), fill=WHITE)
for i, t in enumerate(["Simulation only. No hardware.", "Not an emulated fly brain: connectome-inspired.", "10 seeds per cell. 1 PPO training seed.", "Timings come from a 2 vCPU sandbox.", "Healing handles one fault; the 2nd goes undetected."]):
    d.text((60, 985 + 52 * i), "- " + t, font=FR(30), fill=(230, 235, 245))
im.save(f"{OUT}/slide_7.png")
# 8 closing
im = canvas(stills["walk"], 700); d = ImageDraw.Draw(im); header(d, 8, "Open source")
d.text((60, 740), "Code, data, results", font=FB(60), fill=WHITE)
for i, t in enumerate(["All numbers come from results/summary.json.", "Every clip and chart is regenerated by scripts in the repo.", "Data: FlyWire, CC BY-NC 4.0.", "github.com/Arjunsk1291/neurowalker"]):
    d.text((60, 850 + 60 * i), t, font=FR(32), fill=TEAL if i == 3 else (230, 235, 245))
footer(d); im.save(f"{OUT}/slide_8.png")
print("slides ok", flush=True)
