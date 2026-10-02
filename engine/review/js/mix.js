// The Mix panel: the mixer, ported. vs mix makes every stem (the voice, the effects, each music take; a reel: its own
// track and the effects); here they all play at once through WebAudio, so a take switch is instant and in sync, and the
// picture follows their clock. The human picks the take, sets the music and effects levels (the voice is the reference
// the whole mix is measured against, so it has no slider), turns the effects on or off, and Saves: mix.json, which
// vs mix --final bakes and the diary logs as mix.saved. In a round, Save waits with the rest of your feedback (Undo takes
// it back) and reaches mix.json when you send; with no round open (vs mixer straight after vs mix) it's written at once.
// Every number moves as you drag, while it plays, and "Right now" shows the music's level at the playhead (it dips while
// the voice speaks). While the Mix section is open the stems are the sound; fold it and the video's own sound is back.
import { app, $, toast, esc, post, round } from "./core.js";
import { player } from "./player.js";

const el = $("#tab-mix");
let CFG = null,
  ctx = null,
  bufs = {},
  gains = {},
  DUCK = null, // the ducking envelope (vs mix's duck.json): the music stems come un-ducked, and ducking plays live
  duckNode = null,
  NAMES = [],
  ready = null, // the stems, decoding (a promise), once the panel is first opened
  open = false;
const S = { take: 0, mus: 0, fx: 0, fxOn: true, duck: 6 };
const signed = (d) => `${d > 0 ? "+" : ""}${d}`;

// the stems' clock: the player follows it while the panel is open
const clock = {
  running: false,
  t0: 0,
  offset: 0,
  srcs: [],
  start(t) {
    if (!ctx || !NAMES.every((n) => bufs[n])) return;
    ctx.resume();
    this.srcs.forEach((s) => s.stop?.());
    this.srcs = NAMES.map((n) => {
      const s = ctx.createBufferSource();
      s.buffer = bufs[n];
      s.connect(gains[n]);
      return s;
    });
    this.t0 = ctx.currentTime + 0.05;
    this.offset = t;
    this.srcs.forEach((s) => s.start(this.t0, Math.max(0, t)));
    this.running = true;
    ducking();
  },
  time() {
    return this.running ? this.offset + Math.max(0, ctx.currentTime - this.t0) : this.offset;
  },
  stop() {
    const t = this.time();
    this.srcs.forEach((s) => {
      try {
        s.stop();
      } catch {}
    });
    this.srcs = [];
    this.running = false;
    this.offset = t;
    ducking();
    return t;
  },
};

// ── ducking, live: the music dips under the voice by S.duck dB along vs mix's envelope (0 = silence, 1 = speech), and
//    rises for the end card the way vs mix does it (back to full over 0.6 s, then up 5 dB) ──
const db = (d) => Math.pow(10, d / 20);
function duckAt(t) {
  const D = DUCK,
    i = Math.max(0, Math.min(D.env.length - 1, t * D.rate)),
    k = Math.floor(i),
    e = D.env[k] + (D.env[Math.min(k + 1, D.env.length - 1)] - D.env[k]) * (i - k);
  let g = db(-S.duck * e);
  if (t >= D.end_t) g = Math.min(1, g + (t - D.end_t) / 0.6) * db(Math.min(1, (t - D.end_t) / 0.6) * 5);
  return g;
}
function ducking() {
  if (!duckNode) return;
  const p = duckNode.gain,
    now = ctx.currentTime;
  p.cancelScheduledValues(0);
  if (!clock.running) return p.setValueAtTime(duckAt(clock.offset), now);
  // from the moment the sound is at (or will be, if it hasn't started) to the end, as one curve
  const from = Math.max(now, clock.t0),
    t = clock.offset + (from - clock.t0),
    n = Math.max(2, Math.ceil((DUCK.end - t) * DUCK.rate));
  if (t >= DUCK.end - 0.02) return p.setValueAtTime(duckAt(t), now);
  const curve = new Float32Array(n);
  for (let i = 0; i < n; i++) curve[i] = duckAt(t + i / DUCK.rate);
  p.setValueAtTime(curve[0], from);
  p.setValueCurveAtTime(curve, from + 1e-3, (n - 1) / DUCK.rate);
}

async function load(M) {
  CFG = await (await fetch(M.config, { cache: "no-store" })).json();
  NAMES = ["voice", "fx", ...CFG.takes.map((k) => `music${k.n}`)];
  ctx = new AudioContext({ sampleRate: 44100 });
  const master = ctx.createDynamicsCompressor(); // a safety limiter, so a loud setting never clips
  master.threshold.value = -2;
  master.ratio.value = 20;
  master.attack.value = 0.003;
  master.release.value = 0.1;
  master.connect(ctx.destination);
  if (CFG.duck) {
    const r = await fetch(`${M.media}${CFG.duck}`, { cache: "no-store" });
    if (r.ok) DUCK = await r.json();
  }
  if (DUCK) {
    duckNode = ctx.createGain();
    duckNode.connect(master);
  }
  await Promise.all(
    NAMES.map(async (n) => {
      const r = await fetch(`${M.media}${n}.m4a`);
      if (!r.ok) throw new Error(`${n}.m4a: HTTP ${r.status}`);
      bufs[n] = await ctx.decodeAudioData(await r.arrayBuffer());
      gains[n] = ctx.createGain();
      gains[n].connect(n.startsWith("music") && duckNode ? duckNode : master);
    }),
  );
  // start from what's saved (mix.json), as levels relative to what vs mix mixed at
  const sv = M.saved || {};
  S.take = CFG.narrated === false ? 0 : sv.take && CFG.takes.some((k) => k.n === sv.take) ? sv.take : CFG.takes[0]?.n || 0;
  if (sv.music_db != null) S.mus = Math.round(sv.music_db - (CFG.music_db ?? -16));
  if (sv.sfx_db != null) S.fx = Math.round(sv.sfx_db - (CFG.sfx_db ?? 0));
  if (sv.fx_on != null) S.fxOn = sv.fx_on;
  S.duck = sv.duck_db ?? CFG.duck_db ?? 6;
  apply(true);
  ducking();
}

function apply(instant) {
  if (ctx) {
    const at = ctx.currentTime,
      set = (g, x) => (instant ? g.gain.setValueAtTime(x, at) : g.gain.setTargetAtTime(x, at, 0.04));
    set(gains.voice, 1);
    for (const k of CFG.takes) set(gains[`music${k.n}`], S.take === k.n ? db(S.mus) : 0);
    set(gains.fx, S.fxOn ? db(S.fx) : 0);
  }
  refresh();
}

// the parts that change as the human plays with it, updated in place (a slider being dragged is never redrawn)
function refresh() {
  if (!CFG || !el.querySelector(".summary")) return render();
  const k = CFG.takes.find((x) => x.n === S.take);
  el.querySelectorAll("[data-take]").forEach((b) => b.classList.toggle("on", +b.dataset.take === S.take));
  const mv = el.querySelector("#m-mus + .val");
  if (mv) mv.textContent = k ? `${-Math.round(under(k))} dB under` : "—";
  meter();
  const dv = el.querySelector("#m-duck + .val");
  if (dv) dv.textContent = `${S.duck} dB`;
  el.querySelector("#m-fx + .val").textContent = `${signed(S.fx)} dB`;
  const fb = el.querySelector("#m-fxon");
  fb.classList.toggle("on", S.fxOn);
  fb.textContent = S.fxOn ? "On" : "Off";
  el.querySelector(".summary").textContent = summary();
  const same = !!saved() && JSON.stringify(levels()) === JSON.stringify(savedLevels());
  el.querySelectorAll("#m-save, #m-reset").forEach((b) => (b.disabled = same));
}
// the music's level right now, against the voice: the take's measured level, moved by the slider, dipping by the
// ducking amount wherever vs mix's envelope says the voice is speaking
function meter() {
  const o = el.querySelector("#m-now"),
    bar = el.querySelector("#m-bar");
  if (!o || !CFG) return;
  const k = CFG.takes.find((x) => x.n === S.take);
  if (!k) return (o.textContent = "no music"), (bar.style.width = "0");
  const t = player.t(),
    e = DUCK ? DUCK.env[Math.max(0, Math.min(DUCK.env.length - 1, Math.round(t * DUCK.rate)))] : 1,
    lvl = under(k) + (DUCK ? S.duck * (1 - e) : 0);
  o.textContent = `${-Math.round(lvl)} dB under${DUCK && e < 0.5 ? " (a pause)" : ""}`;
  bar.style.width = `${Math.max(3, Math.min(100, 100 + lvl * 3))}%`;
}
player.on(() => open && meter());
// the levels as the page holds them, and as last saved (your held save, or mix.json)
const levels = () => ({ take: S.take, music_db: (CFG?.music_db ?? -16) + S.mus, duck_db: DUCK ? S.duck : CFG?.duck_db ?? 6, sfx_db: (CFG?.sfx_db ?? 0) + S.fx, fx_on: S.fxOn });
const saved = () => app.state?.mix || app.ctx?.mixer?.saved || null;
function savedLevels() {
  const v = saved() || {};
  return { take: v.take ?? S.take, music_db: v.music_db ?? CFG?.music_db ?? -16, duck_db: DUCK ? v.duck_db ?? CFG?.duck_db ?? 6 : CFG?.duck_db ?? 6, sfx_db: v.sfx_db ?? CFG?.sfx_db ?? 0, fx_on: v.fx_on ?? true };
}

// the music under the voice while it speaks: what vs mix measured, moved by the level and by any change in ducking
const under = (k) => k.under + S.mus - (DUCK ? S.duck - (CFG.duck_db ?? 6) : 0);
function summary() {
  const k = CFG.takes.find((x) => x.n === S.take),
    lvl = k ? Math.round(under(k)) : null,
    kind = k ? k.label.replace(/^[A-Z] /, "") : "";
  return (CFG.narrated === false ? "The reel’s own track" : k ? `Take ${S.take} (${kind}), music ${-lvl} dB under the voice${DUCK ? (S.duck ? ` (it dips ${S.duck} dB while the voice speaks)` : " (no dip while the voice speaks)") : ""}` : "No music") +
    (S.fxOn ? `, effects ${S.fx === 0 ? "as mixed" : signed(S.fx) + " dB"}.` : ", no effects.");
}

function render() {
  const M = app.ctx?.mixer;
  if (!M) return (el.innerHTML = `<p class="empty">No mix yet: Claude runs vs mix, and its stems play here.</p>`);
  if (!CFG) return (el.innerHTML = `<p class="empty">${ready ? "Loading the voice, the effects and the music takes…" : ""}</p>`);
  const R = app.ctx.round,
    other = R && M.video && M.video !== R.video.replace(/-(take\d+|sfx|mixed)\.mp4$/, ".mp4") && M.video !== R.video;
  const k = CFG.takes.find((x) => x.n === S.take);
  el.innerHTML = `
    ${other ? `<p class="notice-mix">These stems were mixed against ${esc(M.video.split("/").pop())}, not this round's video: Claude re-mixes before you judge levels.</p>` : ""}
    ${CFG.narrated === false ? "" : `<div class="card"><div class="k">Music take</div>
      <div class="takes">${[{ n: 0, label: "Off voice" }, ...CFG.takes].map((t) => `<button data-take="${t.n}" class="${S.take === t.n ? "on" : ""}">${t.n || "Off"}<small>${esc(t.n ? t.label.replace(/^[A-Z] /, "").replace(/ · new$/, "") : "voice only")}</small></button>`).join("")}</div>
      <div class="k sub">Music under the voice</div>
      <div class="lvl"><input id="m-mus" type="range" min="-12" max="12" step="1" value="${S.mus}" aria-label="Music level"><span class="val">${k ? `${-Math.round(under(k))} dB under` : "—"}</span></div>
      ${DUCK ? `<div class="k sub">Ducking: how much the music dips while the voice speaks</div>
      <div class="lvl"><input id="m-duck" type="range" min="0" max="15" step="1" value="${S.duck}" aria-label="Ducking under speech"><span class="val">${S.duck} dB</span></div>` : ""}</div>`}
    <div class="card"><div class="lvl" style="margin:0"><div class="k" style="margin:0">Sound effects</div><button id="m-fxon" class="${S.fxOn ? "on" : ""}">${S.fxOn ? "On" : "Off"}</button></div>
      <div class="lvl"><input id="m-fx" type="range" min="-12" max="12" step="1" value="${S.fx}" aria-label="Effects level"><span class="val">${signed(S.fx)} dB</span></div></div>
    <div class="meter"><span>Music right now</span><span class="bar"><i id="m-bar"></i></span><output id="m-now">—</output></div>
    <div class="card"><div class="k">Your mix</div><div class="summary">${summary()}</div>
      <div class="btns" style="margin-top:10px"><button id="m-save" class="primary">Save these levels</button><button id="m-reset">Back to the saved mix</button></div>
      <div class="saved" id="m-saved">${saved() ? `Saved: ${esc(saved().summary || "the levels in mix.json")}${heldMix() ? ` <span class="held">not sent</span>` : ""}` : ""}</div></div>
    <p class="hint">Every track plays at once, so a take switch is instant and in sync; the picture follows the sound. <kbd>0</kbd>–<kbd>9</kbd> switch take while it plays. In a round, Save waits for your send like the rest of your feedback.</p>`;
  refresh();
}

el.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.take != null) {
    S.take = +b.dataset.take;
    apply();
  } else if (b.id === "m-fxon") {
    S.fxOn = !S.fxOn;
    apply();
  } else if (b.id === "m-save") save();
  else if (b.id === "m-reset") {
    const v = saved() || {};
    S.take = v.take ?? S.take;
    if (v.music_db != null) S.mus = Math.round(v.music_db - (CFG.music_db ?? -16));
    if (v.sfx_db != null) S.fx = Math.round(v.sfx_db - (CFG.sfx_db ?? 0));
    if (v.fx_on != null) S.fxOn = v.fx_on;
    S.duck = v.duck_db ?? CFG.duck_db ?? 6;
    ducking();
    render();
    apply(true);
  }
});
const heldMix = () => app.state?.steps.some((s) => s.pending && s.kind === "mix.saved");
el.addEventListener("input", (e) => {
  if (e.target.id === "m-mus") S.mus = +e.target.value;
  else if (e.target.id === "m-fx") S.fx = +e.target.value;
  else if (e.target.id === "m-duck") {
    S.duck = +e.target.value;
    ducking();
  } else return;
  apply();
});

async function save() {
  const body = { ...levels(), summary: summary(), saved: new Date().toISOString() };
  const R = round();
  if (R && R.status !== "closed") await post([{ type: "mix.saved", mix: body }]); // waits for your send, with Undo
  else {
    const r = await fetch("/mix.json", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) return toast(`Couldn't save (HTTP ${r.status}).`, true);
    app.ctx.mixer.saved = body;
    toast(app.ctx?.waiting ? "Saved to the project." : "Saved to the project. Tell Claude “saved”.");
  }
  render();
}

document.addEventListener("keydown", (e) => {
  if (!open || e.target.closest?.("textarea, input:not([type=range])")) return;
  if (/^[0-9]$/.test(e.key) && CFG && (e.key === "0" || CFG.takes.some((k) => k.n === +e.key))) {
    S.take = +e.key;
    apply();
  }
});

// One effect, alone (a click on the timeline's Sound row): the sound at the gain vs mix placed it at, moved by this
// panel's effects level. Its own small audio context, so the stems needn't load to hear one sound.
let soloCtx = null,
  soloSrc = null;
const soloBufs = {};
export async function solo(cue) {
  const M = app.ctx?.mixer;
  if (!M || !cue?.file) throw new Error("no stems yet (vs mix makes them)");
  soloCtx = soloCtx || new AudioContext();
  await soloCtx.resume();
  if (!soloBufs[cue.file]) {
    const r = await fetch(`${M.media}${cue.file}`);
    if (!r.ok) throw new Error(`${cue.file}: HTTP ${r.status}`);
    soloBufs[cue.file] = await soloCtx.decodeAudioData(await r.arrayBuffer());
  }
  try {
    soloSrc?.stop();
  } catch {}
  const g = soloCtx.createGain();
  g.gain.value = Math.min(4, db((cue.gain_db ?? 0) + (CFG ? S.fx : 0)));
  g.connect(soloCtx.destination);
  soloSrc = soloCtx.createBufferSource();
  soloSrc.buffer = soloBufs[cue.file];
  soloSrc.connect(g);
  soloSrc.start();
  return soloSrc.buffer.duration;
}

// Decide borrows the stems to play a music take it offers: the same engine, the levels as set here. null hands the sound
// back (to this panel if it's open, else to the video) and this panel's own take comes back. Playing keeps playing.
let lent = null; // this panel's take while Decide has the stems
export const stems = {
  // what the panel's sound is doing right now (the tests read it: a gain can't be heard in a headless browser)
  now: () => ({ take: S.take, duck_db: S.duck, duck_gain: duckNode ? +duckNode.gain.value.toFixed(4) : null, running: clock.running, t: +clock.time().toFixed(3) }),
  async use(take) {
    const was = player.playing();
    if (take == null) {
      if (lent != null) {
        S.take = lent;
        lent = null;
        apply(true);
      }
      if (!open && player.clock === clock) {
        player.useClock(null);
        if (was) player.play();
      }
      return;
    }
    const M = app.ctx?.mixer;
    if (!M) throw new Error("no stems yet (vs mix makes them)");
    if (!ready)
      ready = load(M).catch((x) => {
        ready = null;
        throw x;
      });
    await ready;
    if (!CFG.takes.some((k) => k.n === take)) throw new Error(`no take ${take} in the stems`);
    if (lent == null) lent = S.take;
    S.take = take;
    apply(true);
    if (player.clock !== clock) {
      player.useClock(clock);
      if (was) player.play();
    }
  },
};

export const mix = {
  render() {
    if (open && !el.contains(document.activeElement)) render(); // a slider being dragged is never redrawn
  },
  // the Mix section opened or folded: the stems become the sound, or hand it back to the video
  async panel(on) {
    const M = app.ctx?.mixer;
    open = on && !!M;
    if (!open) return player.clock === clock && player.useClock(null);
    if (!ready) {
      ready = load(M).catch((x) => {
        el.innerHTML = `<p class="empty">Couldn't load the stems: ${esc(x.message)}</p>`;
        ready = null;
        throw x;
      });
      render();
    }
    await ready;
    if (open) player.useClock(clock);
    render();
  },
};
