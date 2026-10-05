"""Build demo.gif, hero.mp4, reel, cover, carousel, vertical clips from rendered clips and results files."""
import json, os, shutil
import imageio.v2 as iio, numpy as np
from PIL import Image, ImageDraw, ImageFont
M = "docs/media"; OUT = "docs/social"; os.makedirs(OUT, exist_ok=True)
S = json.load(open("results/summary.json"))
def font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()
def frames(fn, step=1):
    r = iio.get_reader(f"{M}/{fn}"); out = [Image.fromarray(f) for i, f in enumerate(r) if i % step == 0]; r.close(); return out
def label(img, text, sub=""):
    im = img.copy(); d = ImageDraw.Draw(im); d.rectangle([0, 0, im.width, 34], fill=(16, 20, 28)); d.text((10, 6), text, fill=(240, 240, 240), font=font(18))
    if sub: d.text((im.width - 10 - 9 * len(sub), 8), sub, fill=(150, 200, 255), font=font(14))
    return im
def write(fn, fr, fps=30):
    w = iio.get_writer(fn, fps=fps, codec="libx264", pixelformat="yuv420p", macro_block_size=2, quality=7)
    for f in fr: w.append_data(np.asarray(f.convert("RGB")))
    w.close()
def side(sc):
    names = {"tripod": "Tripod CPG", "connectome": "Connectome-inspired", "ppo": "PPO residual"}
    cl = {c: frames(f"{c}__{sc}.mp4") for c in names}; n = max(len(v) for v in cl.values()); W, H = cl["tripod"][0].size
    out = []
    for i in range(n):
        row = Image.new("RGB", (W * 3, H))
        for k, c in enumerate(names):
            f = cl[c][min(i, len(cl[c]) - 1)]; row.paste(label(f, names[c], "fell" if i >= len(cl[c]) - 1 and len(cl[c]) < n else ""), (k * W, 0))
        out.append(row)
    return out
def card(text_lines, size, bg=(16, 20, 28)):
    im = Image.new("RGB", size, bg); d = ImageDraw.Draw(im); y = size[1] // 3
    for t, sz, col in text_lines:
        f = font(sz); d.text((size[0] // 12, y), t, fill=col, font=f); y += int(sz * 1.5)
    return im
def hold(im, s, fps=30): return [im] * int(s * fps)
sim = "Simulation only. 2 vCPU CPU sandbox measurements."
# hero + gif
hero = side("flat"); write(f"{M}/hero.mp4", hero); shutil.copy(f"{M}/hero.mp4", "dashboard/public/media/hero.mp4")
g = [f.resize((f.width // 2, f.height // 2)) for f in hero[::3]]; g[0].save(f"{M}/demo.gif", save_all=True, append_images=g[1:], duration=100, loop=0, optimize=True)
# reel 45s
parts = [("flat", "Flat ground: all three walk"), ("slope15", "15 deg slope: tripod and connectome-inspired fall, PPO survives"), ("push", "48 N push"), ("fault_disable_leg", "Fault: leg disabled")]
reel = hold(card([("NeuroWalker", 60, (255, 255, 255)), ("Connectome-inspired hexapod, simulated", 26, (150, 200, 255)), (sim, 18, (180, 180, 180))], hero[0].size), 3)
for sc, cap in parts:
    try: fr = side(sc)
    except Exception as e: print("skip", sc, e); continue
    fr = [label(f, cap) if False else f for f in fr]
    d = ImageDraw.Draw(fr[0]); reel += [ (lambda f: (ImageDraw.Draw(f).text((12, f.height - 28), cap, fill=(255, 255, 0), font=font(18)), f)[1])(f.copy()) for f in fr[:int(9 * 30)] ]
reel += hold(card([("All numbers from results/summary.json", 30, (255, 255, 255)), ("10 seeds per cell, simulation only", 22, (150, 200, 255))], hero[0].size), 3)
write(f"{OUT}/reel_showcase.mp4", reel)
# vertical clips 15s (1080x1920) per controller
for c in ["connectome", "ppo"]:
    fr = frames(f"{c}__flat.mp4")[:450]; v = []
    for f in fr:
        im = Image.new("RGB", (1080, 1920), (16, 20, 28)); big = f.resize((1080, 607)); im.paste(big, (0, 656)); ImageDraw.Draw(im).text((40, 520), {"connectome": "Connectome-inspired controller", "ppo": "PPO residual controller"}[c], fill=(255, 255, 255), font=font(44)); ImageDraw.Draw(im).text((40, 1300), "Simulation only", fill=(180, 180, 180), font=font(30)); v.append(im)
    write(f"{OUT}/vertical_{c}.mp4", v)
# cover + carousel
cover = card([("NeuroWalker", 110, (255, 255, 255)), ("Connectome-inspired hexapod", 48, (150, 200, 255)), ("Simulation only", 36, (200, 200, 200))], (1080, 1080)); cover.save(f"{OUT}/cover_1080x1080.png")
f1 = lambda x: f"{x:.2f} m"
def d(c, s): return S[c][s]["distance"]["mean"]
def falls(c, s): return f"{S[c][s]['fall_rate']['falls']}/{S[c][s]['fall_rate']['n']}"
slides = [
 [("NeuroWalker", 90, (255, 255, 255)), ("Connectome-inspired hexapod", 44, (150, 200, 255)), ("Simulation only", 34, (200, 200, 200))],
 [("What it is", 60, (255, 255, 255)), ("10,000-neuron piece of a published", 36, (230, 230, 230)), ("fruit-fly connectome, steering a", 36, (230, 230, 230)), ("simulated 18-DOF hexapod.", 36, (230, 230, 230))],
 [("Flat ground, 10 s", 60, (255, 255, 255)), (f"Tripod: {f1(d('tripod','flat'))}", 44, (230, 230, 230)), (f"Connectome-inspired: {f1(d('connectome','flat'))}", 44, (230, 230, 230)), (f"PPO residual: {f1(d('ppo','flat'))}", 44, (230, 230, 230))],
 [("15 deg slope, falls /10", 60, (255, 255, 255)), (f"Tripod: {falls('tripod','slope15')}", 44, (230, 230, 230)), (f"Connectome-inspired: {falls('connectome','slope15')}", 44, (230, 230, 230)), (f"PPO residual: {falls('ppo','slope15')}", 44, (230, 230, 230))],
 [("48 N push, falls /10", 60, (255, 255, 255)), (f"Tripod: {falls('tripod','push')}", 44, (230, 230, 230)), (f"Connectome-inspired: {falls('connectome','push')}", 44, (230, 230, 230)), (f"PPO residual: {falls('ppo','push')}", 44, (230, 230, 230))],
 [("Self-healing, leg disabled", 56, (255, 255, 255)), ("speed kept, without -> with healing", 30, (150, 200, 255))] + [(f"{n}: {S[c]['fault_disable_leg']['fault_retained']['mean']*100:.0f}% -> {S[c]['fault_disable_leg+healing']['fault_retained']['mean']*100:.0f}%", 40, (230, 230, 230)) for c, n in [("tripod", "Tripod"), ("connectome", "Connectome-inspired"), ("ppo", "PPO residual")]],
 [("Honest limits", 60, (255, 255, 255)), ("Simulation only, no hardware.", 34, (230, 230, 230)), ("Not an emulated fly brain.", 34, (230, 230, 230)), ("10 seeds, 2 vCPU sandbox timings.", 34, (230, 230, 230))],
 [("Code, data, results", 60, (255, 255, 255)), ("All numbers from results/summary.json", 34, (230, 230, 230)), ("Data: FlyWire, CC BY-NC 4.0", 34, (230, 230, 230))],
]
for i, s in enumerate(slides, 1): card(s, (1080, 1350)).save(f"{OUT}/carousel_{i}.png")
print("assets ok")
