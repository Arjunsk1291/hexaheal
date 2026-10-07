"""Assemble ten sequential-seed HUD tiles. Simulation only."""
import subprocess
import sys
import json
name=sys.argv[1];cmd=['ffmpeg','-loglevel','error','-y','-threads','1']
for s in range(10):cmd+=['-i',f'docs/media_v4/tile_{name}_{s}.mp4']
filt=';'.join(f'[{s}:v]scale=384:300[v{s}]' for s in range(10))+';'+''.join(f'[v{s}]' for s in range(10))+'xstack=inputs=10:layout=0_0|384_0|768_0|1152_0|1536_0|0_300|384_300|768_300|1152_300|1536_300[v]'
cmd+=['-filter_complex_threads','1','-filter_complex',filt,'-map','[v]','-an','-c:v','libx264','-crf','22','-preset','veryfast','-pix_fmt','yuv420p',f'docs/media_v4/grid_R2_L3_{name}.mp4'];subprocess.run(cmd,check=True)
out=[]
for s in range(10):
 e=json.load(open(f'results/v4/render_{name}_{s}.json'));m=json.load(open(f'/tmp/hh4grid_{name}_{s}.npy.json'));out.append(dict(seed=s,fell=e['fell'],t_end=e['t_end'],final_speed=m[-1][1]))
json.dump(out,open(f'results/v4/grid_R2_L3_{name}.json','w'),indent=1)
