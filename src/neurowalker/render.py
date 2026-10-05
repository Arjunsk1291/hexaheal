"""Headless rendering to mp4 with overlays. Backend order: EGL -> OSMesa (GLFW on desktop if MUJOCO_GL unset)."""
from __future__ import annotations

import os

import numpy as np


def pick_gl_backend() -> str:
    """Try EGL then OSMesa in a subprocess-safe way; honours MUJOCO_GL if already set."""
    if os.environ.get("MUJOCO_GL"):
        return os.environ["MUJOCO_GL"]
    import subprocess
    import sys
    for b in ("egl", "osmesa"):
        code = ("import mujoco;m=mujoco.MjModel.from_xml_string('<mujoco><worldbody><geom size=\".1\"/></worldbody></mujoco>');"
                "mujoco.Renderer(m,32,32)")
        env = dict(os.environ, MUJOCO_GL=b, PYOPENGL_PLATFORM=b)
        if subprocess.run([sys.executable, "-c", code], env=env, capture_output=True).returncode == 0:
            return b
    return "glfw"


def _font(size):
    from PIL import ImageFont
    try:
        import matplotlib
        p = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data/fonts/ttf/DejaVuSans-Bold.ttf")
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()


class EpisodeRecorder:
    def __init__(self, env, width=640, height=480, fps=25, cam_dist=1.1, label=""):
        import mujoco
        self.env, self.w, self.h, self.fps = env, width, height, fps
        self.renderer = mujoco.Renderer(env.model, height, width)
        self.cam = mujoco.MjvCamera()
        self.cam.distance, self.cam.elevation, self.cam.azimuth = cam_dist, -22, 125
        self.label = label
        self.frames = []
        self._next_t = 0.0
        self.font, self.small = _font(max(14, height // 22)), _font(max(11, height // 30))

    def maybe_capture(self, speed=0.0, extra=""):
        env = self.env
        if env.t + 1e-9 < self._next_t:
            return
        self._next_t += 1.0 / self.fps
        self.cam.lookat[:] = env.data.qpos[:3] + np.array([0.0, 0, 0.0])
        self.renderer.update_scene(env.data, self.cam)
        img = self.renderer.render().copy()
        self.frames.append(self._overlay(img, speed, extra))

    def _overlay(self, img, speed, extra):
        from PIL import Image, ImageDraw
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im, "RGBA")
        dr.rectangle([0, 0, self.w, int(self.h * 0.13)], fill=(5, 8, 20, 170))
        dr.text((10, 6), self.label, font=self.font, fill=(120, 240, 215))
        faults = self.env.active_faults
        fs = "FAULT: " + ", ".join(f.kind for f in faults) if faults else "no fault"
        dr.text((10, int(self.h * 0.13) + 6), f"t={self.env.t:4.1f}s   speed={speed:4.2f} m/s", font=self.small, fill=(235, 240, 255))
        dr.text((10, int(self.h * 0.13) + 6 + self.small.size + 4), fs + (("  " + extra) if extra else ""), font=self.small,
                fill=(255, 120, 100) if faults else (160, 175, 200))
        dr.text((self.w - 10 - 9 * self.small.size, self.h - self.small.size - 8), "SIMULATION", font=self.small, fill=(255, 255, 255, 190))
        return np.asarray(im)

    def save(self, path, crf=26):
        import imageio.v2 as imageio
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with imageio.get_writer(path, fps=self.fps, codec="libx264", quality=None,
                                ffmpeg_params=["-crf", str(crf), "-pix_fmt", "yuv420p", "-preset", "veryfast"]) as w:
            for f in self.frames:
                w.append_data(f)
        return path
