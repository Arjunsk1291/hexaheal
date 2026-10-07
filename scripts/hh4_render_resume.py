"""Resumable per-seed rendering and HUD encoding. Simulation only; no controller changes."""
import json
import sys
import os
import numpy as np
import imageio.v2 as imageio
sys.path.insert(0,'scripts')
import hh4_render as r
name=sys.argv[1];seed=int(sys.argv[2])
p=f'/tmp/hh4grid_{name}_{seed}.npy';out=f'results/v4/render_{name}_{seed}.json'
clip=f'docs/media_v4/tile_{name}_{seed}.mp4'
if not os.path.exists(out):
 if os.path.exists(p+'.json') and name=='tripod':
  meta=json.load(open(p+'.json'));e=(meta,False,meta[-1][0],len(meta))
 else:e=r.episode(name,seed,p,r.case_legs('dl_1_5'))
 json.dump(dict(fell=e[1],t_end=e[2],n=e[3]),open(out,'w'))
if not os.path.exists(clip):
 e=json.load(open(out));meta=json.load(open(p+'.json'));mm=np.load(p,mmap_mode='r')
 # Freeze earlier-ending seeds to the same 258-frame timeline, with FELL visible.
 with imageio.get_writer(clip,fps=r.FPS,codec='libx264',quality=None,ffmpeg_params=['-crf','20','-pix_fmt','yuv420p','-preset','veryfast']) as w:
  for f in range(258):
   i=min(f,e['n']-1);t=meta[i][0]
   w.append_data(r.tile(mm[i],seed,meta[i],e['fell'] and f>=e['n']-1,e['t_end'],r.case_legs('dl_1_5'),r.SLOW[0]<=t<r.SLOW[1]))
print(name,seed,'encoded',flush=True)
