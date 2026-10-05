"""'Measurable' showcase video: side-by-side clips (seed 0) with a 10-seed benchmark scoreboard under each scene.
Every number is read from results/summary.json. Stream frames to keep RAM low."""
import json
import os

import imageio.v2 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

S = json.load(open("results/summary.json")); M = "docs/media"; OUT = "docs/social/measurable_benchmark.mp4"
NAMES = {"tripod": "Tripod CPG", "connectome": "Connectome-inspired", "ppo": "PPO residual"}
COL = {"tripod": (150, 165, 190), "connectome": (45, 212, 191), "ppo": (245, 158, 11)}
F = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", s)


def stat(sc, c):
    d = S[c].get(sc)
    if not d: return "n/a"
    fr = d["fall_rate"]
    if sc.startswith("fault_"):
        base = sc.replace("+healing", "")
        h = S[c].get(base + "+healing")
        a, b = d["fault_retained"]["mean"], (h["fault_retained"]["mean"] if h else float("nan"))
        return f"speed kept {a*100:.0f}% -> {b*100:.0f}% with healing"
    return f"{d['distance']['mean']:.2f} m in 10 s | falls {fr['falls']}/{fr['n']}"


def reader(fn):
    r = iio.get_reader(f"{M}/{fn}")
    for f in r: yield Image.fromarray(f)
    r.close()


def scene(sc, title, sbkey, secs=9, fps=30):
    its = {c: reader(f"{c}__{sc}.mp4") for c in NAMES}; last = {}
    for i in range(secs * fps):
        for c in NAMES:
            try: last[c] = next(its[c])
            except StopIteration: pass
        W, H = last["tripod"].size; im = Image.new("RGB", (W * 3, H + 150), (12, 16, 26))
        d = ImageDraw.Draw(im)
        for k, c in enumerate(NAMES):
            im.paste(last[c], (k * W, 0)); d.rectangle([k * W, H, k * W + W, H + 150], outline=(40, 48, 66))
            d.text((k * W + 14, H + 12), NAMES[c], font=F(20), fill=COL[c]); d.text((k * W + 14, H + 50), stat(sbkey, c), font=F(17), fill=(235, 240, 255))
            d.text((k * W + 14, H + 112), "benchmark mean, 10 seeds", font=F(13), fill=(140, 150, 170))
        d.rectangle([0, H - 30, 1100, H], fill=(5, 8, 20)); d.text((10, H - 26), title + "  (video: seed 0)", font=F(16), fill=(255, 235, 120))
        yield im


def card(lines, size, secs=3, fps=30):
    im = Image.new("RGB", size, (12, 16, 26)); d = ImageDraw.Draw(im); y = size[1] // 3
    for t, sz, col in lines: d.text((60, y), t, font=F(sz), fill=col); y += int(sz * 1.6)
    for _ in range(secs * fps): yield im


def all_frames():
    yield from card([("NeuroWalker: measured, not claimed", 54, (255, 255, 255)), ("Simulation only. 10 seeds per scenario. Sandbox: 2 vCPU CPU.", 24, (150, 200, 255))], (1920, 518), 3)
    for sc, title, key in [("flat", "Flat ground", "flat"), ("slope15", "15 degree slope", "slope15"), ("push", "48 N push", "push"), ("fault_disable_leg", "Leg disabled at t=4 s (video shows self-healing on)", "fault_disable_leg"), ("fault_lock_joint", "Joint locked at t=4 s (video shows self-healing on)", "fault_lock_joint")]:
        yield from scene(sc, title, key)
    yield from card([("Source: results/summary.json, docs/BENCHMARK.md", 30, (255, 255, 255)), ("Not an emulated fly brain. No hardware.", 24, (150, 200, 255))], (1920, 518), 3)


w = iio.get_writer(OUT, fps=30, codec="libx264", pixelformat="yuv420p", macro_block_size=2, quality=7)
n = 0
for f in all_frames():
    w.append_data(np.asarray(f)); n += 1
w.close(); print("ok", n, os.path.getsize(OUT) // 1024, "KB")
