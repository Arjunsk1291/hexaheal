# V3 Stage 5: video evidence plan (plan only, nothing rendered)

Selection rule (fixed in advance): every seed 0-9 of a chosen cell is shown, in seed order, no cherry-picking. A 10-robot grid = the same cell, 10 seeds, one controller per grid; two grids side by side compare controllers. Each row below is the recorded outcome for that seed so you can check it before anything is rendered. T = time of fall in s (episode length 14 s unless stated); OK = no fall.

## Candidate A (clearest single story): single disabled leg, plain tripod, with vs without healing

### A1 without healing
- tripod  / fault_disable_leg: falls 10/10, mean distance 1.70 m
- per seed 0-9: s0:T=11.86, s1:T=11.26, s2:T=12.40, s3:T=12.90, s4:T=11.04, s5:T=10.42, s6:T=11.74, s7:T=11.00, s8:T=11.76, s9:T=11.22

### A2 with healing
- tripod  / fault_disable_leg+healing: falls 3/10, mean distance 2.42 m
- per seed 0-9: s0:OK, s1:OK, s2:T=9.90, s3:OK, s4:T=9.18, s5:OK, s6:OK, s7:T=10.28, s8:OK, s9:OK

## Candidate B: same cell, connectome (healing does NOT help it)

### B1 connectome no healing
- connectome  / fault_disable_leg: falls 10/10, mean distance 1.31 m
- per seed 0-9: s0:T=6.12, s1:T=6.30, s2:T=7.38, s3:T=6.02, s4:T=7.34, s5:T=6.92, s6:T=5.60, s7:T=6.32, s8:T=6.46, s9:T=6.74

### B2 connectome with healing
- connectome  / fault_disable_leg+healing: falls 10/10, mean distance 1.32 m
- per seed 0-9: s0:T=6.12, s1:T=6.30, s2:T=7.08, s3:T=6.02, s4:T=7.46, s5:T=6.78, s6:T=5.60, s7:T=6.32, s8:T=6.50, s9:T=6.74

## Candidate C: tuned tripod single leg

### C1 tuned no healing
- tuned_tripod  / fault_disable_leg: falls 7/10, mean distance 2.65 m
- per seed 0-9: s0:T=8.36, s1:T=10.14, s2:OK, s3:T=13.18, s4:OK, s5:T=9.74, s6:T=10.54, s7:T=8.80, s8:T=12.14, s9:OK

### C2 tuned with healing
- tuned_tripod  / fault_disable_leg+healing: falls 4/10, mean distance 2.85 m
- per seed 0-9: s0:OK, s1:OK, s2:T=8.94, s3:OK, s4:T=9.88, s5:T=8.44, s6:OK, s7:T=8.22, s8:OK, s9:OK

## Candidate D: 15 degree slope, connectome vs tuned tripod

### D1 connectome slope15
- connectome  / slope15: falls 10/10, mean distance -0.09 m
- per seed 0-9: s0:T=0.66, s1:T=0.58, s2:T=0.96, s3:T=0.80, s4:T=1.24, s5:T=0.70, s6:T=0.86, s7:T=0.58, s8:T=0.66, s9:T=0.62

### D2 tuned tripod slope15
- tuned_tripod  / slope15: falls 0/10, mean distance 1.96 m
- per seed 0-9: s0:OK, s1:OK, s2:OK, s3:OK, s4:OK, s5:OK, s6:OK, s7:OK, s8:OK, s9:OK

## Candidate E: hybrid on the same single-leg cell and slope

### E1 hybrid disable_leg+healing
- hybrid h_half_pg / fault_disable_leg+healing: falls 8/10, mean distance 1.94 m
- per seed 0-9: s0:T=8.66, s1:T=6.28, s2:T=8.62, s3:OK, s4:T=6.14, s5:T=7.46, s6:T=6.26, s7:T=7.30, s8:OK, s9:T=6.56

### E2 hybrid slope15
- hybrid h_half_pg / slope15: falls 0/10, mean distance 1.99 m
- per seed 0-9: s0:OK, s1:OK, s2:OK, s3:OK, s4:OK, s5:OK, s6:OK, s7:OK, s8:OK, s9:OK

## Recommendation

- Best 10-robot comparison on current evidence: A1 vs A2 (the only cell where healing visibly changes the plain tripod: 10/10 falls to 3/10). It must be described as 'healing helps the plain tripod on one leg loss' and NOT 'healing helps the connectome' (B2 falls 10/10) and NOT generally (Stage 3 map: it hurts in several double-fault cases).
- D1 vs D2 shows the simple tuned tripod beating the connectome on slopes; it is an honest-negative clip, not a promotional one.
- Anything about the hybrid waits for the final Stage 4 table (docs/v3_stage4_tables.md).
- Every clip must carry an on-screen label: 'MuJoCo simulation, connectome-inspired controller, seeds 0-9 shown in order'. No claims about real hardware, ROS 2 or Docker.
