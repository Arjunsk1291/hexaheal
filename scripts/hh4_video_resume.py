"""Bounded scene encoding for the recovered simulation video."""
import sys
import json
import subprocess
import os
import numpy as np
import imageio.v2 as imageio
sys.path.insert(0,'scripts')
import hh4_video as v
kind=sys.argv[1];scene=int(sys.argv[2]);hero=np.load('/tmp/hh4hero.npy',mmap_mode='r');meta=json.load(open('/tmp/hh4hero.npy.json'))
gt=imageio.get_reader('docs/media_v4/grid_R2_L3_tripod.mp4');gf=imageio.get_reader('docs/media_v4/grid_R2_L3_final.mp4')
land=[(4,v.seg_title(hero,meta),'Lose a leg at 4 s: how long can the robot wait before it reacts?'),(8,v.seg_hud(hero,meta),'One robot: NORMAL, FAULT, DIAGNOSED, STANDING + REPLANNING, WALKING'),(10,v.seg_arch(),'Detect the failed legs, stand, search a new gait with CMA-ES, switch'),(12,v.seg_grids(gt,gf,gt.count_frames(),gf.count_frames()),'Same fault, same 10 seeds: plain tripod makes no net progress, re-planned gait walks in 7 of 10 and falls in 2'),(10,v.seg_latency(),'Recovered share falls from 55% at 0 s delay to 15% at 1.5 s'),(8,v.seg_matrix(),'Recovered: plain tripod 0, final controller 6, offline oracle 15 of 21'),(6,v.seg_end(),'')]
vert=[(4,land[0][1],land[0][2]),(6,land[1][1],land[1][2]),(8,land[3][1],land[3][2]),(8,land[4][1],land[4][2]),(7,land[5][1],land[5][2]),(7,land[6][1],'')]
dur,g,cap=(land if kind=='land' else vert)[scene];out=f'docs/media_v4/scene_{kind}_{scene}.mp4'
if os.path.exists(out+'.done'):sys.exit(0)
p=subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080' if kind=='land' else '1080x1350','-r','30','-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-preset','veryfast',out],stdin=subprocess.PIPE)
for i in range(dur*30):
 im=g(i/max(dur*30-1,1));im=v.stamp(im,cap) if kind=='land' else v.vframe(im,cap);p.stdin.write(np.asarray(im).tobytes())
p.stdin.close();assert p.wait()==0;open(out+'.done','w').write('verified encode complete\n');print(out,flush=True)
