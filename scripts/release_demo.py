"""Predeclared seed-0/first-case short simulation demo. Not a success-rate estimate."""
import json
from pathlib import Path
import sys
import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0,'scripts')
from release_run import controller
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.render import _font

out=Path('release/validation');out.mkdir(parents=True,exist_ok=True)
e=HexapodEnv('flat', max_time=14., faults=[Fault('disable_leg',4.,leg=0)], rand=.1,seed=0,target_speed=.25)
e.reset(seed=0);c=controller('tierB','dl_0');c.reset()
r=mujoco.Renderer(e.model,360,640);cam=mujoco.MjvCamera();cam.distance=1.4;cam.azimuth=125;cam.elevation=-25
font=_font(15);next_t=0.;fps=15;frames=0
with imageio.get_writer(out/'demo.mp4',fps=fps,codec='libx264',ffmpeg_params=['-crf','24','-pix_fmt','yuv420p']) as w:
 while True:
  _,_,te,tr,_=e.step(c.act(e))
  if e.t>=next_t or te or tr:
   next_t+=1/fps;cam.lookat[:]=e.data.qpos[:3]
   r.update_scene(e.data,cam);im=Image.fromarray(r.render());d=ImageDraw.Draw(im)
   d.rectangle((0,0,640,48),fill='#0d1117')
   d.text((10,5),'HexaHeal | MuJoCo simulation | Tier B | R1 loss | seed 0',font=font,fill='white')
   d.text((10,27),f't={e.t:.2f}s | state={c.state} | fault at 4.0s',font=font,fill='#45d5c5')
   d.rectangle((0,332,640,360),fill='#0d1117');d.text((10,339),'Predeclared first case/seed. See all 1470 runs, including failures.',font=font,fill='white')
   w.append_data(np.asarray(im));frames+=1
  if te or tr:break
r.close();(out/'demo.json').write_text(json.dumps({'case':'dl_0','seed':0,'controller':'tierB','simulation_only':True,'selection':'first case and seed, declared in code before rendering','fell':e.fell,'frames':frames},indent=2)+'\n')
