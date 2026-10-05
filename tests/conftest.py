import os

# Headless CI runners have no GL; the physics tests never render.
os.environ.setdefault("MUJOCO_GL", "disable")
