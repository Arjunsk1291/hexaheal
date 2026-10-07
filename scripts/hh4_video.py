"""HexaHeal v4 Stage 5: assemble the explainer video from deterministic renders and result files. Simulation only.
Usage: hh4_video.py hero            -> render the single-robot hero clip (R2+L3, seed 0, final controller) at 960x720 (needs osmesa env)
       hh4_video.py land|vert       -> docs/media_v4/hexaheal_v4_{landscape,vertical}.mp4 + .srt (land only), burned-in captions
       hh4_video.py gif             -> docs/media_v4/hero.gif (< 10 MB) and stills
Inputs: /tmp/hh4hero.npy(+.json), docs/media_v4/grid_R2_L3_{tripod,final}.mp4, results/v4/*.json, results/v3/latency_stats.json."""
import importlib.util
import json
import subprocess
import sys

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "scripts")
BG, TEAL, ALERT, FG, DIM, PANEL = (13, 17, 23), (45, 212, 191), (255, 93, 93), (230, 237, 243), (139, 148, 158), (22, 27, 34)
FR = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"; FB = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
F = lambda sz, b=False: ImageFont.truetype(FB if b else FR, sz)  # noqa: E731
FPS = 30
CAP = "Simulation only (MuJoCo, seeds 0-9). No hardware."


def load_r():
    spec = importlib.util.spec_from_file_location("r", "scripts/hh4_render.py"); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r); return r


def text_c(d, xy, s, font, fill, anchor="mm"): d.text(xy, s, font=font, fill=fill, anchor=anchor)


def new(): im = Image.new("RGB", (1920, 1080), BG); return im, ImageDraw.Draw(im)


# ---- segment generators: g(u, N) -> PIL 1920x1080, u in [0,1]
def seg_title(hero, meta):
    def g(u):
        im, d = new()
        lo = next(i for i, m in enumerate(meta) if m[0] >= 3.5); hi = next(i for i, m in enumerate(meta) if m[0] >= 4.5)
        i = lo + int(u * (hi - lo - 1)); fr = Image.fromarray(np.asarray(hero[i])).resize((1440, 1080))
        im.paste(fr, (240, 0)); d = ImageDraw.Draw(im, "RGBA")
        d.rectangle([0, 0, 1920, 230], fill=BG + (225,))
        text_c(d, (960, 85), "A robot loses a leg mid-step.", F(64, True), FG); text_c(d, (960, 165), "How long does it have to react?", F(54), TEAL)
        text_c(d, (1640, 900), "0.25x slow motion", F(34), ALERT)
        return im
    return g


def seg_hud(hero, meta):
    def g(u):
        im, d = new(); t = u * 14.0; i = int(np.argmin([abs(m[0] - t) for m in meta]))
        fr = Image.fromarray(np.asarray(hero[i])).resize((1440, 1080)); im.paste(fr, (60, 0)); d = ImageDraw.Draw(im, "RGBA")
        _, sp, st = meta[i]; col = ALERT if st == "FAULT" else (TEAL if st in ("NORMAL", "WALKING") else (255, 200, 80))
        d.rounded_rectangle([1540, 120, 1880, 700], radius=18, fill=PANEL + (255,), outline=(48, 54, 61))
        d.text((1570, 150), "STATE", font=F(26), fill=DIM); d.text((1570, 190), st.replace(" + ", "\n+ "), font=F(40, True), fill=col)
        d.text((1570, 340), "SPEED", font=F(26), fill=DIM); d.text((1570, 380), f"{sp:5.2f} m/s", font=F(52, True), fill=FG)
        d.text((1570, 480), "TIMER", font=F(26), fill=DIM); d.text((1570, 520), f"{meta[i][0]:4.1f} s", font=F(52, True), fill=FG)
        d.text((1570, 610), "FAILED  R2 + L3" if meta[i][0] >= 4 else "no fault yet", font=F(30), fill=ALERT if meta[i][0] >= 4 else DIM)
        d.text((60, 1000), "playback 1.75x", font=F(30), fill=DIM)
        return im
    return g


def seg_arch():
    steps = [("FAULT", "leg torque lost\nat t = 4 s", ALERT), ("DETECT", "failed-leg set\nin about 0.34 s", TEAL), ("STAND", "hold still,\nstay upright", TEAL), ("RE-PLAN", "CMA-ES search,\n60 gait trials", TEAL), ("GAIT SWITCH", "new gait starts\n~5 s after fault", TEAL)]
    def g(u):
        im, d = new(); text_c(d, (960, 140), "Fault response pipeline", F(60, True), FG)
        for i, (t, s, c) in enumerate(steps):
            on = u * 5.4 >= i + 0.2; x0 = 110 + i * 340
            d.rounded_rectangle([x0, 380, x0 + 300, 640], radius=22, fill=PANEL, outline=c if on else (48, 54, 61), width=4)
            if on:
                text_c(d, (x0 + 150, 440), t, F(36, True), c); text_c(d, (x0 + 150, 560), s, F(30), FG)
            if i < 4 and u * 5.4 >= i + 1.2: d.polygon([(x0 + 308, 490), (x0 + 330, 510), (x0 + 308, 530)], fill=DIM)
        text_c(d, (960, 800), "Standing lasts a fixed 4.6 s of simulated time in every planning run (measured).", F(32), DIM)
        return im
    return g


def seg_grids(gt, gf, nt, nf):
    def g(u):
        im, d = new(); text_c(d, (960, 60), "R2 + L3 lost: seeds 0-9 in order, no selection", F(44, True), FG)
        a = Image.fromarray(gt.get_data(min(nt - 1, int(u * (nt - 1))))).resize((1216, 380)); b = Image.fromarray(gf.get_data(min(nf - 1, int(u * (nf - 1))))).resize((1216, 380))
        im.paste(a, (352, 145)); im.paste(b, (352, 575))
        d.text((352, 105), "plain tripod: net progress about 0", font=F(30, True), fill=ALERT); d.text((352, 536), "final controller (Tier B)", font=F(30, True), fill=TEAL)
        return im
    return g


def seg_latency():
    L = json.load(open("results/v3/latency_stats.json")); ds = L["delays"]; P = L["pooled"]
    def g(u):
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.family": "Noto Sans", "text.color": "#e6edf3", "axes.labelcolor": "#e6edf3", "xtick.color": "#8b949e", "ytick.color": "#8b949e", "axes.edgecolor": "#8b949e", "font.size": 20})
        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100); fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#0d1117")
        n = u * (len(ds) - 1); k = int(n); frac = n - k
        xs = ds[:k + 1] + ([ds[k] + (ds[k + 1] - ds[k]) * frac] if k + 1 < len(ds) else [])
        def interp(key):
            ys = [P[str(t)][key] / 100 for t in ds[:k + 1]]
            if k + 1 < len(ds): ys.append(P[str(ds[k])][key] / 100 + (P[str(ds[k + 1])][key] - P[str(ds[k])][key]) / 100 * frac)
            return ys
        r_, up = interp("recovered"), interp("upright")
        ax.plot(xs, up, "o--", color="#8b949e", lw=3, label="upright (no fall)"); ax.plot(xs, r_, "o-", color="#2dd4bf", lw=5, label="recovered (walking)")
        ax.plot([0, 1.5], [0, 0], color="#e6edf3", lw=3, label="plain tripod (recovered: 0)")
        Td = L["mean_detect_s_delay0"]; ax.axvline(Td, color="#ff5d5d", lw=3); ax.text(Td + 0.02, 0.97, f"detection {Td:.2f} s", color="#ff5d5d", fontsize=24, va="top")
        ax.set_xlim(-0.05, 1.6); ax.set_ylim(-0.03, 1.0); ax.set_xlabel("response delay after diagnosis (s)"); ax.set_ylabel("share of runs")
        ax.set_yticks([0, .25, .5, .75, 1]); ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"]); ax.grid(color="#21262d")
        [ax.spines[s].set_visible(False) for s in ("top", "right")]; ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.9), fontsize=22)
        ax.set_title("How long can the robot wait?", loc="left", fontsize=34, color="#e6edf3")
        fig.text(0.03, 0.145, "Simulation only. 10 cases chosen from tuning-seed results where healing can work (stated bias).", color="#8b949e", fontsize=18)
        fig.subplots_adjust(left=0.07, right=0.97, top=0.92, bottom=0.21); fig.canvas.draw()
        im = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3]); plt.close(fig); return im
    return g


def seg_matrix():
    M = Image.open("docs/media_v4/recovered_matrix.png").convert("RGB"); W0 = 1920; M = M.resize((W0, int(M.height * W0 / M.width)))
    rows_y = [0.30, 0.46, 0.62, 0.78]
    def g(u):
        im, d = new(); im.paste(M, (0, 250)); d = ImageDraw.Draw(im)
        text_c(d, (960, 90), "Recovered cases out of 21", F(52, True), FG)
        shown = int(u * 5.2)
        for i, yf in enumerate(rows_y):
            if i >= shown: d.rectangle([0, 250 + int(M.height * (yf - 0.1)), 1920, 250 + int(M.height * (yf + 0.075))], fill=BG)
        return im
    return g


def seg_end():
    def g(u):
        im, d = new()
        text_c(d, (960, 330), "Limits", F(40, True), TEAL)
        for i, s in enumerate(["Simulation only. Disabled-leg faults on flat ground. No hardware.", "9 of 21 cases are never recovered by any controller.", "The warm-start idea did not pass its pre-registered test."]):
            text_c(d, (960, 420 + i * 60), s, F(34), FG)
        if u > 0.5: text_c(d, (960, 760), "[NAME]", F(54, True), FG); text_c(d, (960, 840), "[ROLE LINE]", F(34), DIM)
        return im
    return g


def stamp(im, cap):
    d = ImageDraw.Draw(im, "RGBA"); d.rectangle([0, 960, 1920, 1080], fill=BG + (235,))
    text_c(d, (960, 1000), cap, F(32), FG); text_c(d, (960, 1050), CAP, F(24), DIM); return im


def build(kind):
    hero = np.load("/tmp/hh4hero.npy", mmap_mode="r"); meta = json.load(open("/tmp/hh4hero.npy.json"))
    gt = imageio.get_reader("docs/media_v4/grid_R2_L3_tripod.mp4"); gf = imageio.get_reader("docs/media_v4/grid_R2_L3_final.mp4")
    nt, nf = gt.count_frames(), gf.count_frames()
    land = [(4, seg_title(hero, meta), "Lose a leg at 4 s: how long can the robot wait before it reacts?"), (8, seg_hud(hero, meta), "One robot: NORMAL, FAULT, DIAGNOSED, STANDING + REPLANNING, WALKING"),
            (10, seg_arch(), "Detect the failed legs, stand, search a new gait with CMA-ES, switch"), (12, seg_grids(gt, gf, nt, nf), "Same fault, same 10 seeds: plain tripod makes no net progress, re-planned gait walks in 7 of 10 and falls in 2"),
            (10, seg_latency(), "Recovered share falls from 55% at 0 s delay to 15% at 1.5 s"), (8, seg_matrix(), "Recovered: plain tripod 0, final controller 6, offline oracle 15 of 21"), (6, seg_end(), "")]
    vert = [(4, land[0][1], land[0][2]), (6, land[1][1], land[1][2]), (8, land[3][1], land[3][2]), (8, land[4][1], land[4][2]), (7, land[5][1], land[5][2]), (7, land[6][1], "")]
    segs = land if kind == "land" else vert
    out = f"docs/media_v4/hexaheal_v4_{'landscape' if kind == 'land' else 'vertical'}.mp4"
    size = "1920x1080" if kind == "land" else "1080x1350"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", size, "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast", out], stdin=subprocess.PIPE)
    t0, srt = 0.0, []
    for k, (dur, g, cap) in enumerate(segs):
        n = int(dur * FPS)
        for i in range(n):
            im = g(i / max(n - 1, 1)); im = stamp(im, cap) if kind == "land" else vframe(im, cap)
            p.stdin.write(np.asarray(im).tobytes())
        if cap: srt.append((t0, t0 + dur, cap + ("  " + CAP if k == 0 else "")))
        t0 += dur
    p.stdin.close(); p.wait()
    if kind == "land":
        ts = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round((x % 1) * 1000)):03d}"  # noqa: E731
        open("docs/media_v4/hexaheal_v4.srt", "w").write("\n".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{c}\n" for i, (a, b, c) in enumerate(srt)))
    print(out, t0)


def vframe(im, cap):
    v = Image.new("RGB", (1080, 1350), BG); body = im.resize((1080, 608)); v.paste(body, (0, 370)); d = ImageDraw.Draw(v)
    text_c(d, (540, 120), "HexaHeal", F(64, True), TEAL); text_c(d, (540, 200), "robot fault response, in simulation", F(34), DIM)
    import textwrap
    for i, line in enumerate(textwrap.wrap(cap, 40)[:4]): text_c(d, (540, 1040 + i * 46), line, F(36), FG)
    text_c(d, (540, 1290), CAP, F(26), DIM); return v


if __name__ == "__main__":
    k = sys.argv[1]
    if k == "hero":
        r = load_r(); r.W, r.H = 960, 720
        r.episode("final", 0, "/tmp/hh4hero.npy", r.case_legs("dl_1_5"))
    elif k in ("land", "vert"): build(k)
