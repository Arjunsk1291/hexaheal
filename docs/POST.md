# LinkedIn post kit (HexaHeal v4)

All numbers: MuJoCo simulation, 2 vCPU sandbox, no hardware. Sources in section (b). Placeholders: [GITHUB LINK], [NAME], [ROLE LINE]. Nothing here is posted. The older template caption was reference only; the drafts below are different shapes.

## (a) Hooks and caption drafts

Hook options:
- A: "A robot loses a leg mid-step. How long does it have to react?"
- B: "Would you trust a robot that 'passed' by standing perfectly still?"
- C: "75 of 75 'successful' robot runs weren't walking. Can you spot why?"

### Draft 1 - the question first (hook A, short)
A robot loses a leg mid-step. How long does it have to react?

In my MuJoCo hexapod simulation I delayed the repair by 0 to 1.5 s and measured how often it still ended up walking. 55% at 0 s. 15% at 1.5 s. If the lost leg is a front one, even 0.2 s is already too late.

The controller finds the failed legs in about 0.34 s, stands still, then re-plans the gait with CMA-ES. It recovers 6 of 21 two-leg and one-leg fault cases. The plain tripod gait recovers 0. An oracle that knows the fault from t=0 reaches 15.

Simulation only, flat ground, no hardware. 9 cases no controller recovered.

What response time do you design for?

#robotics #MuJoCo #simulation

### Draft 2 - the correction story (hook C)
75 of 75 "successful" robot runs weren't walking.

My first version counted a hexapod as OK after a broken leg if it didn't fall. Then I added one more condition: it has to still move at 0.125 m/s over the last 8 s. The plain tripod gait went from "OK" to 0 of 21 cases. It was standing still.

With the stricter metric, my re-planning controller recovers 6 of 21, the oracle 15. The warm-start idea I added later did not pass its pre-registered test (+3 cases, CI touching zero). I'm reporting that too.

All of this is MuJoCo simulation. Seeds for tuning and for evaluation were kept apart.

How do you score "the robot is fine" in your own tests?

#robotics #MuJoCo #simulation

### Draft 3 - quiet technical (no hook, results-first)
Small simulation study, hexapod, MuJoCo: fault tolerance depends on reaction time more than on the repair itself.

- detect the failed leg set: ~0.34 s
- stand still while CMA-ES searches 60 candidate gaits
- switch gait

Result on held-out seeds: 6 of 21 fault cases recovered vs 0 for the plain gait, 15 for the oracle. Add a delay before the diagnosis and the recovered share falls from 55% to 15% by 1.5 s.

Limits: simulation only, disabled-leg faults, flat ground, 9 cases not recovered by any controller.

Looking for working-student or internship roles in robotics simulation and validation. M.Eng. at Deggendorf.

#robotics #MuJoCo #simulation

### Draft 4 - failure-first (hook B)
Would you trust a robot that "passed" by standing perfectly still?

I didn't, after I looked at my own numbers. Of the upright runs of my plain gait, every one was frozen in place. Of my re-planning controller's upright runs, about half were still standing at the end.

So I report two things: upright (no fall) and recovered (no fall and moving). Recovered: 6 of 21 cases. Upright: 12 of 21.

Why the gap? The controller stands for 4.6 s of simulated time while it searches, and that is a fixed budget I haven't beaten yet.

Simulation, not hardware.

#robotics #MuJoCo #simulation

### Draft 5 - one-liner plus video (hook A, for a native video post)
Lost a leg at 4 s. Back to walking at ~9 s, in simulation. When the loss is a front leg and the repair starts 0.2 s late, it doesn't make it. Video: plain gait vs re-planned gait, same 10 seeds, falls included.

Only simulation. Details in the first comment.

#robotics #MuJoCo #simulation

Choose one; do not reuse the same skeleton across several posts. No closing "please hire me" paragraph (your earlier decision: it reads desperate). No "aspiring/incoming" tags.

## (b) Claim to source

| claim | file | label |
|---|---|---|
| latency recovered 55% at 0 s, 15% at 1.5 s | results/v3/latency_stats.json, docs/V3_latency.md | MEASURED |
| front leg lost: 0.2 s is too late (R1, L1 0/10 at 0.2 s) | docs/V3_latency.md | MEASURED |
| failed-leg set found in about 0.34 s (mean) | docs/V3_latency.md | MEASURED |
| (removed) "0 false alarms" | only in docs/EXPLAINER.md (10 healthy runs); no results file found, and results/v3 logs 57 of 210 Tier B fault runs with false_alarm=true (definition not re-checked) | UNVERIFIED, removed from drafts |
| 60 CMA-ES trials, per-leg phase/duty/amplitude/lift | results/v3/v2_config_final.json, docs/PREREGISTRATION_V3.md | MEASURED (config) |
| stands 4.6 s while planning, gait starts ~5 s after fault | results/v4/hh4_final_v2B_0-9.jsonl, docs/RESULTS_V4.md | MEASURED |
| 6 of 21 recovered, plain 0, oracle 15 | results/v3/stage1_stats.json | MEASURED |
| 12 of 21 upright for Tier B | results/v3/stage1_stats.json | MEASURED |
| 75 of 75 plain-gait upright runs frozen | results/v3/stage1_stats.json | MEASURED |
| about half of Tier B's upright runs standing still (54 of 123) | results/v4/stage2_stats.json | MEASURED |
| warm start: 9 vs 6, +3, CI [0,+6], rule failed | results/v4/stage2_stats.json | MEASURED |
| tuning vs evaluation seeds separate | docs/PREREGISTRATION_V3.md, PREREGISTRATION_V4.md | MEASURED (design) |
| 9 cases not recovered by any controller | docs/RESULTS_V3.md | MEASURED |
| fixed 4.6 s stand is a budget I haven't beaten | docs/RESULTS_V4.md | GUESS (cause not tested) |
| "Back to walking at ~9 s" (draft 5) | docs/RESULTS_V4.md (switch time) | MEASURED switch time; walking after switch is not guaranteed per run, soften before use |
| M.Eng. at Deggendorf, role search | /memory profile | KNOWN from profile, confirm before posting |

Flag: the 0.33 s in the older docs vs 0.34 s in the latency run are both in files; use 0.34 (latency run). The false-alarm claim was removed: it is not traceable to a results file and the per-run log shows false_alarm=true in 57 of 210 Tier B runs (meaning not re-checked). Do not use it until checked.
Draft 4 claim "every one was frozen" refers to the plain tripod (75/75), which is true by file.
Draft 1 "2-leg and 1-leg cases": the 21 cases are 6 single and 15 double faults.

## (c) First comment
[GITHUB LINK]
Full numbers, seeds and the failure list are in docs/RESULTS_V4.md. One stated bias: the 10 cases in the latency sweep were picked from tuning-seed results where healing can work, so the curve is not an average over all faults. About half of the re-planning controller's upright runs (54 of 123) still end standing still; that is why I report "recovered" separately.

## (d) Posting guide
- Native video with burned-in captions, plus the .srt. Link only in the first comment, not in the post.
- 3 hashtags.
- Weekday morning, CET (Germany) and Gulf time: common advice, UNVERIFIED.
- Reply to every comment with substance in the first hour. Short, technical, a different shape each time.
- Update LinkedIn Featured and headline; add the repo to the profile. Headline guidance from your notes: keep industry-skill tags, no "incoming/aspiring"; location stays Abu Dhabi until you arrive in Germany.
- Test vertical vs landscape only if the platform allows; no platform rules are claimed here.
- If someone challenges a number: point to the file and the seed list; if they are right, say so in the thread and fix the doc.
- Pre-post checklist: [ ] numbers re-checked against the files [ ] the word "simulation" visible in post and video [ ] [NAME] and [ROLE LINE] filled [ ] repo pushed, LICENSE and docs/LICENSES.md present [ ] FlyWire history decision understood [ ] no AI-tool names in repo or commits [ ] repo link in first comment only.

## (e) Interview sheet
The five numbers: (1) recovered 6 of 21 vs plain 0 vs oracle 15 [KNOWN]; (2) latency 55% at 0 s to 15% at 1.5 s [KNOWN]; (3) detection about 0.34 s [KNOWN]; (4) 75 of 75 plain runs frozen [KNOWN]; (5) warm start +3, CI [0,+6], failed rule [KNOWN].
Hard questions:
1. Why recovered, not upright? Upright alone counted a frozen robot as fine. [KNOWN] Whether 0.125 m/s is the right bar for a real robot: UNKNOWN.
2. Why were the latency cases chosen that way? Picked from tuning seeds where healing can work, to see the delay effect; this is a bias and is stated. [KNOWN]
3. Why does the online search lag the library? Library gaits come from long offline searches; online gets 60 trials in 4.6 s of stand time. [KNOWN: budgets differ] Whether more trials would close the gap: UNKNOWN.
Also: the 9 never-recovered cases are not proven impossible [UNKNOWN physically]; nothing here is hardware.
