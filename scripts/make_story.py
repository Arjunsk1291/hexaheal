"""LinkedIn story video (1920x1080, 30 fps). Every number is read from results/summary.json or the story run log/telemetry
(docs/story/story_run.*). Seed-0 video, 10-seed benchmark numbers, labelled as such. Simulation only."""
import json
import os

import imageio.v2 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
S = json.load(open("results/summary.json")); L = json.load(open("docs/story/story_run_log.json"))
R = np.load("docs/story/story_run.npz"); ND = json.load(open("dashboard/public/data/neural.json"))
INFO = json.load(open("data/processed/subgraph_info.json"))
OUT = "docs/social/story_linkedin.mp4"
BG, TEAL, ORG, RED, WHITE, GREY = (10, 14, 24), (45, 212, 191), (245, 158, 11), (255, 90, 70), (240, 244, 255), (140, 150, 172)
FB = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", s)
FR = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)
NAMES = {"tripod": "Tripod CPG", "connectome": "Connectome-inspired", "ppo": "PPO residual"}
COL = {"tripod": (150, 165, 190), "connectome": TEAL, "ppo": ORG}
LEGN = ["R1", "R2", "R3", "L1", "L2", "L3"]

T, X, SP, NF, ST, NEU = R["t"], R["x"], R["speed"], R["nfaults"], R["state"], R["neural"]
log = L["log"]; FT1, FT2 = 4.0, 13.0
t_susp = next((e["t"] for e in log if e["to"] == "FAULT_SUSPECTED"), None)
diag = next((e for e in log if e["to"] == "ADAPT"), None)
t_ver = next((e for e in log if e["to"] == "VERIFY"), None)
t_ok = next((e for e in log if e["decision" if False else "to"] == "NORMAL" and e["action"].get("decision") == "recovery verified"), None)
leg1 = diag["evidence"]["diagnosis"]["leg"] if diag else 2

# neural layout (spectral embedding from the data build) and a sparse edge sample for the wiring look
XY = np.array(ND["xy"]); rng = np.random.default_rng(1)
import scipy.sparse as sp  # noqa: E402
Wt = sp.load_npz("data/processed/subgraph_weights.npz").tocoo()
sel = rng.choice(Wt.nnz, 2600, replace=False); EDG = np.stack([Wt.row[sel], Wt.col[sel]], 1)


def neural_img(sz, k, glow=1.0):
    """Wiring view: faint synapse sample + neurons brightened by recent spike counts (frame k of the story run)."""
    im = Image.new("RGB", (sz, sz), (8, 11, 20)); d = ImageDraw.Draw(im, "RGBA")
    p = XY * (sz - 20) + 10
    for a, b in EDG: d.line([tuple(p[a]), tuple(p[b])], fill=(60, 110, 150, 34), width=1)
    cnt = NEU[min(k, len(NEU) - 1)].astype(float)
    for i in range(len(p)):
        c = cnt[i]
        if c > 0:
            a = min(1.0, 0.35 + c * 0.18 * glow); r = 2 + min(c, 6) * 0.5
            d.ellipse([p[i][0] - r, p[i][1] - r, p[i][0] + r, p[i][1] + r], fill=(60, 235, 205, int(255 * a)))
        else:
            d.point(tuple(p[i]), fill=(70, 100, 140, 150))
    return im


def frame_at(t):
    return int(np.clip(np.searchsorted(T, t), 0, len(T) - 1))


def video_img(i):
    r = vid[i] if i < len(vid) else vid[-1]
    return Image.fromarray(r)


vid = None


def txt(d, xy, s, f, fill=WHITE, anchor="la"): d.text(xy, s, font=f, fill=fill, anchor=anchor)


def chip(d, x, y, s, on, col=TEAL):
    f = FB(24); w = int(d.textlength(s, font=f)) + 36
    d.rounded_rectangle([x, y, x + w, y + 46], 12, fill=(col if on else (24, 30, 46)), outline=(col if on else (60, 70, 92)))
    txt(d, (x + 18, y + 8), s, f, (8, 12, 20) if on else GREY); return x + w + 14


def trace(d, box, t, fault_marks, vmax=0.5):
    x0, y0, x1, y1 = box; d.rectangle(box, outline=(46, 56, 78), fill=(14, 19, 32))
    tt = T[T <= t]; vv = SP[:len(tt)]
    tmax = T[-1]
    for ft in fault_marks:
        if ft <= t:
            xx = x0 + (x1 - x0) * ft / tmax; d.line([(xx, y0), (xx, y1)], fill=RED, width=2); txt(d, (xx + 6, y0 + 4), "fault", FR(18), RED)
    pts = [(x0 + (x1 - x0) * a / tmax, y1 - (y1 - y0) * min(max(b, 0), vmax) / vmax) for a, b in zip(tt, vv)]
    if len(pts) > 1: d.line(pts, fill=TEAL, width=3)
    txt(d, (x0 + 8, y1 - 26), "speed (m/s)", FR(18), GREY)


def live(t, title, sub, banner=None, banner_col=RED, show_state=True, notes=(), fault_marks=(FT1, FT2)):
    i = frame_at(t); im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    v = video_img(i).resize((1280, 720)); im.paste(v, (0, 0))
    k = int(t * 10); im.paste(neural_img(620, k).resize((620, 620)), (1290, 10))
    txt(d, (1300, 640), "10,000-neuron connectome subgraph, live spikes", FR(20), GREY)
    d.rectangle([0, 0, 1280, 70], fill=(5, 8, 20)); txt(d, (22, 14), title, FB(34), WHITE)
    txt(d, (1250, 20), "SIMULATION", FB(20), (255, 255, 255), "ra") if False else None
    txt(d, (1258, 726 - 38), "SIMULATION", FB(20), (255, 255, 255, 200), "ra")
    if banner:
        d.rounded_rectangle([30, 90, 30 + int(d.textlength(banner, font=FB(36))) + 40, 150], 14, fill=(120, 20, 14, 230), outline=banner_col)
        txt(d, (50, 98), banner, FB(36), WHITE)
    y = 735
    txt(d, (30, y), sub, FB(30), TEAL); y += 52
    spd = SP[i]
    txt(d, (30, y), f"t = {T[i]:5.1f} s", FB(30), WHITE); txt(d, (330, y), f"speed {max(spd, 0):.2f} m/s", FB(30), WHITE)
    txt(d, (680, y), f"distance {X[i]:.2f} m", FB(30), WHITE); y += 58
    if show_state:
        x = 30; cur = str(ST[i])
        for s_ in ["NORMAL", "FAULT_SUSPECTED", "DIAGNOSE", "ADAPT", "VERIFY"]:
            x = chip(d, x, y, s_.replace("_", " "), cur == s_)
    trace(d, (30, 910, 1260, 1070), t, fault_marks)
    for n, s_ in enumerate(notes): txt(d, (1300, 690 + 0 + n * 34), s_, FR(26), WHITE)
    return im


def card(lines, t, tot):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im); y = 380
    for s_, sz, col in lines: txt(d, (W // 2, y), s_, FB(sz), col, "ma"); y += int(sz * 1.7)
    return im


def clipsrc(c, sc):
    r = iio.get_reader(f"docs/media/{c}__{sc}.mp4"); fr = [np.asarray(f) for f in r]; r.close(); return fr


def stat(sc, c):
    dd = S[c][sc]
    if sc.startswith("fault_"):
        h = S[c][sc + "+healing"]; return f"speed kept {dd['fault_retained']['mean']*100:.0f}% -> {h['fault_retained']['mean']*100:.0f}% with healing"
    return f"{dd['distance']['mean']:.2f} m in 10 s | falls {dd['fall_rate']['falls']}/{dd['fall_rate']['n']}"


def three(sc, sc_src, t, title, foot):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im); txt(d, (30, 24), title, FB(44), WHITE)
    for k, c in enumerate(NAMES):
        fr = srcs[(c, sc_src)]; f = fr[min(int(t * 30), len(fr) - 1)]
        im.paste(Image.fromarray(f).resize((620, 349)), (30 + k * 630, 110))
        d.rectangle([30 + k * 630, 110 + 349, 30 + k * 630 + 620, 110 + 349 + 190], outline=(46, 56, 78))
        txt(d, (48 + k * 630, 482), NAMES[c], FB(30), COL[c]); txt(d, (48 + k * 630, 530), stat(sc, c), FB(24), WHITE)
        txt(d, (48 + k * 630, 585), "10-seed benchmark mean", FR(20), GREY)
    txt(d, (30, 720), foot, FR(28), GREY)
    return im


def all_frames():
    global vid, srcs
    vid = [f for f in iio.get_reader("docs/story/story_run.mp4")]
    srcs = {(c, s): clipsrc(c, s) for c in NAMES for s in ("flat", "fault_disable_leg")}
    # 1 hook: the wiring (5 s)
    for n in range(5 * FPS):
        t = n / FPS; im = Image.new("RGB", (W, H), BG); ni = neural_img(1000, int(1.0 + t * 8), glow=1.4); im.paste(ni, (460, 40)); d = ImageDraw.Draw(im)
        txt(d, (40, 40), "This is a fly brain's wiring diagram.", FB(46), WHITE) if t < 2.6 else txt(d, (40, 40), "We gave a wiring-inspired controller a body.", FB(46), TEAL)
        txt(d, (40, 120), f"{INFO['n_neurons']:,} neurons, {INFO['n_synapse_pairs']:,} synapse pairs", FR(30), WHITE)
        txt(d, (40, 165), "FlyWire connectome subgraph (CC BY-NC 4.0)", FR(24), GREY)
        txt(d, (40, 1030), "Connectome-inspired. Not an emulated or uploaded fly. Simulation only.", FR(26), GREY)
        yield im
    # 2 walking (6 s of the run, t=0.6..3.6 then 3.6 at 1x)
    for n in range(6 * FPS):
        t = 0.6 + n / FPS * 0.5
        yield live(t, "Spikes in, leg commands out", "A hexapod in MuJoCo, steered by the spiking network", None, show_state=False, notes=("Sensors drive input neurons.", "Descending neurons set the gait.", "18 joints, 6 legs."))
    # 3 arena (7 s)
    for n in range(7 * FPS): yield three("flat", "flat", n / FPS, "Same robot, same ground. Three controllers.", "Video: seed 0. Scoreboard: mean of 10 seeds (results/summary.json).")
    # 4 fault (3.4 -> 9.4)
    msg = f"FAULT at t = {FT1:.1f} s: leg {LEGN[leg1]} disabled"
    for n in range(int(8.5 * FPS)):
        t = 3.4 + n / FPS * 0.9 if False else 3.4 + n / FPS * (6.0 / 8.5)
        ban = msg if t >= FT1 else None
        notes = []
        if t_susp and t >= t_susp: notes.append(f"Detected at t = {t_susp:.2f} s  (+{t_susp - FT1:.2f} s)")
        if diag and t >= diag["t"]: notes.append(f"Diagnosed: leg {LEGN[diag['evidence']['diagnosis']['leg']]}, {diag['evidence']['diagnosis']['kind'].replace('_', ' ')}")
        if t_ver and t >= t_ver["t"]: notes.append("New gait applied")
        if t_ok and t >= t_ok["t"]: notes.append(f"Recovery verified at t = {t_ok['t']:.1f} s")
        yield live(t, "Now we break it", "Self-healing: detect, diagnose, re-plan, verify", ban, notes=tuple(notes))
    # 5 recalibration payoff (9.4 -> 12.6 at 1x)
    for n in range(int(3.4 * FPS)):
        t = 9.4 + n / FPS
        r = (t_ok["evidence"] if t_ok else {})
        notes = [f"Re-plan: {L['adapt_info'].get('trials', '?')} gait candidates tried (CMA-ES)", f"Speed after recovery: {r.get('speed_m_s', 0):.2f} m/s", f"Pre-fault speed: {r.get('pre_fault_speed_m_s', 0):.2f} m/s", f"Seed-0 ratio: {r.get('ratio', 0)*100:.0f}%"]
        yield live(t, "It re-calibrated and kept walking", "Recovery verified by measuring speed and tilt", None, notes=tuple(notes))
    # 6 second fault (12.4 -> 21)
    leg2 = 5
    for n in range(int(8.0 * FPS)):
        t = 12.4 + n / FPS * (8.6 / 8.0)
        ban = f"SECOND FAULT at t = {FT2:.1f} s: leg {LEGN[leg2]} disabled" if t >= FT2 else None
        notes = ("v0.1 healing handles one fault.", "The second one is not detected:", "the monitor stays disarmed after a heal.") if t >= FT2 + 0.5 else ()
        yield live(t, "Then we break another leg", "What the unmodified v0.1 controller does", ban, notes=notes)
    # 7 same fault, three controllers (7 s)
    for n in range(7 * FPS): yield three("fault_disable_leg", "fault_disable_leg", n / FPS, "Same leg fault, three controllers (healing on)", "Seed-0 video. Numbers: 10-seed means. Healing helped the CPG-based controllers and made PPO worse.")
    # 8 outro
    for n in range(4 * FPS):
        yield card([("NeuroWalker", 70, WHITE), ("Connectome-inspired hexapod. Simulation only.", 34, TEAL), ("All numbers from results/summary.json. Sandbox: 2 vCPU. No hardware, no board claims.", 26, GREY)], n, 4 * FPS)


w = iio.get_writer(OUT, fps=FPS, codec="libx264", quality=None, ffmpeg_params=["-crf", "21", "-pix_fmt", "yuv420p", "-preset", "veryfast"])
n = 0
for f in all_frames(): w.append_data(np.asarray(f)); n += 1
w.close(); print("ok", n, os.path.getsize(OUT) // 1024, "KB", n / FPS, "s")
