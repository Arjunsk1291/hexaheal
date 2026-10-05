import React, { useEffect, useMemo, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const CTRL = { tripod: "Tripod CPG", connectome: "Connectome-inspired", ppo: "PPO residual" };
const COL = { tripod: "#94a3b8", connectome: "#2dd4bf", ppo: "#f59e0b" };
const base = import.meta.env.BASE_URL;
const useJson = (f) => { const [d, setD] = useState(null); useEffect(() => { fetch(`${base}data/${f}`).then((r) => r.json()).then(setD).catch(() => setD(null)); }, [f]); return d; };
const fmt = (x, n = 2) => (x == null || Number.isNaN(x) ? "n/a" : Number(x).toFixed(n));
const Section = ({ id, title, sub, children }) => (
  <section id={id} className="mx-auto max-w-6xl px-4 py-14 sm:py-20">
    <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-white">{title}</h2>
    {sub && <p className="mt-2 max-w-3xl text-slate-400">{sub}</p>}
    <div className="mt-8">{children}</div>
  </section>
);
const Video = ({ src, label, sync }) => (
  <figure className="overflow-hidden rounded-xl border border-line bg-black">
    <video src={`${base}media/${src}`} muted loop playsInline autoPlay preload="metadata" className="w-full aspect-video" aria-label={label} data-sync={sync} />
    <figcaption className="px-3 py-2 text-sm text-slate-400">{label}</figcaption>
  </figure>
);

function Hero({ manifest, summary }) {
  const h = manifest?.headline || [];
  return (
    <header className="relative overflow-hidden border-b border-line">
      <video src={`${base}media/hero.mp4`} muted loop playsInline autoPlay className="absolute inset-0 h-full w-full object-cover opacity-30" aria-hidden="true" />
      <div className="relative mx-auto max-w-6xl px-4 py-20 sm:py-32">
        <p className="mb-3 inline-block rounded-full border border-teal/40 px-3 py-1 text-xs tracking-widest text-teal">SIMULATION ONLY</p>
        <h1 className="text-4xl sm:text-6xl font-semibold tracking-tight text-white">NeuroWalker</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-300">A six-legged robot, in simulation, whose walking is steered by a spiking network built from the published fruit-fly connectome. It is a connectome-inspired controller, not a copy of a brain.</p>
        <div className="mt-10 grid gap-3 sm:grid-cols-3">
          {h.map((x) => (<div key={x.label} className="card"><div className="text-3xl font-semibold text-teal">{x.value}</div><div className="mt-1 text-sm text-slate-400">{x.label}</div></div>))}
        </div>
        <p className="mt-4 text-xs text-slate-500">Headline numbers are read from results/summary.json at build time.</p>
      </div>
    </header>
  );
}

function Arena({ manifest, summary }) {
  const scen = manifest?.arena_scenarios || [];
  const [s, setS] = useState(scen[0]);
  useEffect(() => { if (!s && scen.length) setS(scen[0]); }, [scen]);
  const rows = useMemo(() => Object.keys(CTRL).filter((c) => summary?.[c]?.[s]).map((c) => ({ c, d: summary[c][s] })).sort((a, b) => b.d.distance.mean - a.d.distance.mean), [s, summary]);
  return (
    <Section id="arena" title="Arena" sub="Same scenario, same seed, three controllers. Pick a scenario.">
      <div className="mb-4 flex flex-wrap gap-2">{scen.map((x) => <button key={x} className="chip" aria-pressed={x === s} onClick={() => setS(x)}>{x.replace(/_/g, " ")}</button>)}</div>
      <div className="grid gap-3 md:grid-cols-3">{Object.keys(CTRL).map((c) => manifest?.videos?.[s]?.[c] && <Video key={c} src={manifest.videos[s][c]} label={`${CTRL[c]} - ${s}`} />)}</div>
      <div className="card mt-6 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-slate-400"><tr><th className="py-1">Rank</th><th>Controller</th><th>Distance (m)</th><th>Falls</th><th>CoT</th></tr></thead>
        <tbody>{rows.map((r, i) => (<tr key={r.c} className="border-t border-line"><td className="py-2">{i + 1}</td><td style={{ color: COL[r.c] }}>{CTRL[r.c]}</td><td>{fmt(r.d.distance.mean)} +- {fmt(r.d.distance.ci95)}</td><td>{r.d.fall_rate.falls}/{r.d.fall_rate.n}</td><td>{fmt(r.d.cot.mean)}</td></tr>))}</tbody></table>
        <p className="mt-2 text-xs text-slate-500">Mean +- 95% CI over seeds. Leaderboard is by mean distance in the selected scenario.</p></div>
    </Section>
  );
}

function Neural({ neural }) {
  const ref = useRef(null); const [lesion, setLesion] = useState("none"); const [t, setT] = useState(0);
  useEffect(() => { if (!neural) return; const id = setInterval(() => setT((x) => (x + 1) % neural.frames.length), 1000 / neural.fps); return () => clearInterval(id); }, [neural]);
  useEffect(() => {
    if (!neural || !ref.current) return; const cv = ref.current; const g = cv.getContext("2d"); const W = cv.width, H = cv.height;
    g.fillStyle = "#070b14"; g.fillRect(0, 0, W, H);
    const fr = neural.frames[t]; const lz = neural.lesions[lesion];
    neural.xy.forEach((p, i) => { const a = Math.min(1, fr[i] / 6); g.fillStyle = lz && lz.mask[i] ? "#475569" : `rgba(45,212,191,${0.08 + 0.92 * a})`; g.fillRect(p[0] * W, p[1] * H, 2 + 2 * a, 2 + 2 * a); });
  }, [neural, t, lesion]);
  if (!neural) return <Section id="neural" title="Neural view" sub="Run scripts/make_media.py to precompute neural activity."><div className="card text-slate-400">Neural activity data not found.</div></Section>;
  return (
    <Section id="neural" title="Neural view" sub="Each dot is a neuron of the 10,000-neuron subgraph, laid out by a spectral embedding of the wiring. Brightness is its recent firing rate while the robot walks.">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card"><canvas ref={ref} width={640} height={640} className="w-full rounded-lg" role="img" aria-label="Spiking activity of the connectome subgraph" /></div>
        <div className="space-y-4">
          <Video src="neural_walk.mp4" label="Walking clip for the same run (connectome-inspired controller)" />
          <div className="card"><div className="mb-2 text-sm text-slate-400">Lesion comparison (precomputed). Gray neurons are silenced.</div>
            <div className="flex flex-wrap gap-2">{["none", ...Object.keys(neural.lesions)].map((k) => <button key={k} className="chip" aria-pressed={k === lesion} onClick={() => setLesion(k)}>{k}</button>)}</div>
            {lesion !== "none" && <p className="mt-3 text-sm">Distance {fmt(neural.lesions[lesion].distance)} m vs {fmt(neural.baseline_distance)} m intact (mean over seeds, flat ground).</p>}
          </div></div></div>
    </Section>
  );
}

function Healing({ healing }) {
  const kinds = healing ? Object.keys(healing) : []; const [k, setK] = useState(null); const sel = k || kinds[0];
  if (!healing) return <Section id="healing" title="Self-healing"><div className="card text-slate-400">No decision logs found.</div></Section>;
  const d = healing[sel];
  return (
    <Section id="healing" title="Self-healing" sub="A health monitor watches joint tracking and sensor signals. A state machine diagnoses the fault, searches gait parameters in a model rollout, and verifies the result.">
      <div className="mb-4 flex flex-wrap gap-2">{kinds.map((x) => <button key={x} className="chip" aria-pressed={x === sel} onClick={() => setK(x)}>{x.replace(/_/g, " ")}</button>)}</div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card"><ol className="relative space-y-4 border-l border-line pl-5">{d.decisions.map((e, i) => (<li key={i}><span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-teal" /><div className="text-xs text-slate-500">t = {fmt(e.t)} s</div><div className="font-medium text-white">{e.from} to {e.to}</div><div className="text-sm text-slate-400">{e.action?.decision || ""}</div></li>))}</ol></div>
        <div className="card text-sm text-slate-300"><p className="mb-2 text-slate-400">Evidence logged per decision (raw JSON, controller {d.controller}):</p><pre className="max-h-80 overflow-auto rounded bg-black/40 p-3 text-xs">{JSON.stringify(d.decisions.map((e) => ({ t: e.t, to: e.to, evidence: e.evidence })), null, 1)}</pre></div>
      </div>
    </Section>
  );
}

function Metrics({ summary }) {
  const [m, setM] = useState("distance");
  const scen = useMemo(() => (summary ? Object.keys(summary.tripod || {}).filter((s) => !s.includes("fault")) : []), [summary]);
  const data = scen.map((s) => { const r = { s }; Object.keys(CTRL).forEach((c) => { const x = summary?.[c]?.[s]?.[m]; r[c] = x?.mean; r[c + "_err"] = x?.ci95; }); return r; });
  const opts = { distance: "Distance (m)", cot: "Cost of transport", roll_rms: "Roll RMS (rad)", latency_ms: "Latency (ms/step)" };
  return (
    <Section id="metrics" title="Metrics" sub="Mean with 95% confidence intervals. Every number comes from results/summary.json.">
      <div className="mb-4 flex flex-wrap gap-2">{Object.entries(opts).map(([k, v]) => <button key={k} className="chip" aria-pressed={k === m} onClick={() => setM(k)}>{v}</button>)}</div>
      <div className="card h-96"><ResponsiveContainer><BarChart data={data}><CartesianGrid stroke="#1e2a40" /><XAxis dataKey="s" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><Tooltip contentStyle={{ background: "#0e1524", border: "1px solid #1e2a40" }} /><Legend />
        {Object.keys(CTRL).map((c) => <Bar key={c} dataKey={c} name={CTRL[c]} fill={COL[c]}><ErrorBar dataKey={c + "_err"} stroke="#e2e8f0" /></Bar>)}</BarChart></ResponsiveContainer></div>
    </Section>
  );
}

const How = () => (
  <Section id="how" title="How it works">
    <div className="card overflow-x-auto"><svg viewBox="0 0 900 220" className="min-w-[640px] w-full" role="img" aria-label="Architecture: robot state to sensory neuron groups, spiking subgraph, descending readout, CPG gait, simulator">
      {[["Robot state", 20], ["Sensory groups", 190], ["10k-neuron LIF subgraph", 360], ["Descending readout", 560], ["Tripod CPG", 720]].map(([t, x], i) => (<g key={t}><rect x={x} y="80" width={i === 2 ? 170 : 140} height="60" rx="12" fill="#0e1524" stroke="#2dd4bf" /><text x={x + (i === 2 ? 85 : 70)} y="115" textAnchor="middle" fill="#e2e8f0" fontSize="14">{t}</text></g>))}
      {[160, 330, 530, 700].map((x) => <path key={x} d={`M${x} 110 h28`} stroke="#94a3b8" markerEnd="url(#a)" />)}
      <defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="#94a3b8" /></marker></defs>
      <text x="450" y="30" textAnchor="middle" fill="#94a3b8" fontSize="13">Input and output assignment is a design choice, not a biological claim.</text>
      <text x="450" y="190" textAnchor="middle" fill="#94a3b8" fontSize="13">Health monitor and state machine can re-plan the CPG after a fault.</text></svg></div>
    <p className="mt-4 text-sm text-slate-400">The ROS 2 layer (sim, brain, gait, health monitor, decision and metrics nodes) is written and syntax-checked but UNVERIFIED until it runs in the provided Docker image.</p>
  </Section>
);

const Limits = () => (
  <Section id="limits" title="Honest limitations and roadmap">
    <div className="grid gap-4 md:grid-cols-2">
      <div className="card"><h3 className="font-medium text-white">What this is not</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-slate-400"><li>Not an uploaded or emulated brain. The robot does not think like a fly.</li><li>Not hardware. Everything is simulation.</li><li>The mapping between robot state and neurons is engineered.</li><li>Measured on a 2-core CPU sandbox, not a GTX 1660 Ti laptop.</li><li>Single PPO seed. The ROS 2 layer is UNVERIFIED.</li></ul></div>
      <div className="card"><h3 className="font-medium text-white">Roadmap</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-slate-400"><li>System identification of a real hexapod, actuator models</li><li>Domain randomization sweep, then sim-to-real on flat ground</li><li>Run the ROS 2 path in Docker and compare against the pure-Python results</li><li>More PPO seeds, more fault locations</li></ul></div>
    </div>
    <p className="mt-6 text-xs text-slate-500">Data: FlyWire (CC BY-NC 4.0). Model constants follow Shiu et al. 2024. See the repository for citations and licenses.</p>
  </Section>
);

export default function App() {
  const summary = useJson("summary.json"), manifest = useJson("manifest.json"), neural = useJson("neural.json"), healing = useJson("healing.json");
  return (<><Hero manifest={manifest} summary={summary} /><nav className="sticky top-0 z-10 border-b border-line bg-ink/80 backdrop-blur"><div className="mx-auto flex max-w-6xl gap-4 overflow-x-auto px-4 py-3 text-sm text-slate-400">{["arena", "neural", "healing", "metrics", "how", "limits"].map((x) => <a key={x} href={`#${x}`} className="hover:text-white">{x}</a>)}</div></nav>
    <Arena manifest={manifest} summary={summary} /><Neural neural={neural} /><Healing healing={healing} /><Metrics summary={summary} /><How /><Limits /><footer className="border-t border-line py-8 text-center text-xs text-slate-500">NeuroWalker - simulation only - MIT licensed</footer></>);
}
