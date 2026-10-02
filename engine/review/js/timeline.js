// The timeline: read-only. It shows what the video is made of, moment by moment, and points at the frame; nothing on it
// can be dragged (a range is a highlight to comment on, never a trim). Rows: the scenes, the voice's words (a reel: its
// beats), the titles, the current scene's elements, the sound cues, the findings, the notes. The playhead drives it
// all; hovering an element's row outlines it in the frame, and hovering the frame lights up the row of what's under
// the pointer.
import { app, $, fmt, esc, liveNotes } from "./core.js";
import { player, sceneJump } from "./player.js";
import { element, onAt, boxAt, segmentAt, findings } from "./maps.js";
import { hit, boxOf, draft, point, setRange } from "./point.js";

const rows = $("#tl-rows"),
  tip = $("#tip");
let ZOOM = 20,
  W0 = 0,
  W1 = 20,
  seg = null,
  hoverEl = null;

const M = () => app.maps || {};
const end = () => player.end() || 1;
const pct = (t) => ((t - W0) / (W1 - W0)) * 100;
const inWin = (a, b) => b >= W0 && a <= W1;
const short = (id) => id.slice(id.indexOf("/") + 1);

// the elements of one segment on screen inside the window: what a note is most likely about first (named ones, then
// words, then pictures, then bare shapes like dust motes), each group in the order it arrives
const RANK = { title: 1, text: 2, picture: 3, group: 4, box: 5, shape: 6 };
function elementsOf(name) {
  const rank = (e) => (e.named ? 0 : RANK[e.kind] ?? 5) - (e.text && !e.named ? 0.5 : 0);
  return (M().elements?.items || [])
    .filter((e) => e.segment === name && e.on.length && e.on.some(([a, b]) => inWin(a, b)))
    .sort((a, b) => rank(a) - rank(b) || a.on[0][0] - b.on[0][0] || a.id.localeCompare(b.id));
}

// ── the window the rows show ──
function frame(t, force) {
  if (!ZOOM || ZOOM >= end()) [W0, W1] = [0, end()];
  else if (force || t < W0 || t > W1 - ZOOM * 0.04) {
    W0 = Math.max(0, Math.min(end() - ZOOM, t - ZOOM * 0.15));
    W1 = W0 + ZOOM;
  }
}

// 1:02, or 1:02.5 when the ticks are closer than a second
const clock = (t, tenths) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}${tenths ? "." + Math.round((t % 1) * 10) : ""}`;

function ticks() {
  const span = W1 - W0,
    step = [0.5, 1, 2, 5, 10, 15, 30, 60].find((s) => span / s <= 12) || 120;
  const out = [];
  for (let t = Math.ceil(W0 / step) * step; t <= W1; t += step)
    if (pct(t) > 1.5 && pct(t) < 98.5) out.push(`<span style="left:${pct(t)}%">${clock(t, step < 1)}</span>`);
  return out.join("");
}

// a block is clipped to the window (one that starts before it shows from the edge, its label still readable)
const block = (cls, a, b, label, data = "") => {
  if (!inWin(a, b)) return "";
  const l = Math.max(0, pct(a)),
    r = Math.min(100, pct(b));
  return `<span class="bl ${cls}${pct(a) < 0 ? " cut" : ""}" style="left:${l}%;width:${Math.max(0.25, r - l)}%" ${data}>${label ?? ""}</span>`;
};
const pip = (cls, t, label, data = "") => (inWin(t, t) ? `<i class="${cls}" style="left:${pct(t)}%" ${data}>${label ?? ""}</i>` : "");
const row = (label, track, cls = "", data = "") =>
  `<div class="row ${cls}" ${data}><div class="lb" title="${esc(label)}">${label}</div><div class="tr">${track}</div></div>`;

function draw() {
  const T = M().timeline;
  if (!T) return (rows.innerHTML = `<p class="empty">No timeline for this version.</p>`);
  const t = player.t();
  seg = segmentAt(t);
  const out = [row(`${clock(W0)} – ${clock(W1)}`, ticks(), "ruler")];
  const done = app.state?.done || {};
  out.push(row("Scenes", T.segments.map((s) => block(`seg${s === seg ? " act" : ""}${done[s.name] ? " done" : ""}`, s.t0, s.t1, (done[s.name] ? "✓ " : "") + esc(s.name), `data-t="${s.t0}" data-tip="${esc(s.name)} · ${esc(s.scene || s.kind || "")} · ${fmt(s.t0)}–${fmt(s.t1)}${done[s.name] ? ` · done in v${done[s.name].version}` : ""}"`)).join(""), "grp"));
  const words = M().words;
  if (words) {
    const fine = W1 - W0 <= 30;
    out.push(row("Voice", fine
      ? words.filter((w) => inWin(w.t0, w.t1)).map((w) => block("word", w.t0, Math.max(w.t1, w.t0 + 0.05), esc(w.w), `data-t="${w.t0}" data-tip="“${esc(w.w)}” · act ${w.act} · ${fmt(w.t0)}"`)).join("")
      : (T.voice || []).map((a) => block("voice", a.t0, a.t1, `act ${a.act}`, `data-t="${a.t0}" data-tip="${a.el} · ${fmt(a.t0)}–${fmt(a.t1)}"`)).join(""), "grp"));
  } else if (T.beat) {
    const b = +T.beat,
      h = +T.first_hit || 0,
      out2 = [];
    for (let k = Math.ceil((W0 - h) / b); h + k * b <= W1; k++) if (h + k * b >= 0) out2.push(pip(`beat${k === 0 ? " hit" : ""}`, h + k * b, "", `data-tip="${k === 0 ? "the first hit" : "beat " + k} · ${fmt(h + k * b)}"`));
    out.push(row("Beats", out2.join(""), "grp"));
  }
  out.push(row("Titles", T.titles.map((x) => block("title", x.t0, x.t1, esc(x.id), `data-t="${x.t0}" data-el="${esc(x.el)}" data-tip="${esc(x.el)} · ${fmt(x.t0)}–${fmt(x.t1)}"`)).join(""), "grp"));
  if (seg && M().elements) {
    const els = elementsOf(seg.name);
    out.push(`<div class="row grp seghead"><div class="lb">${esc(seg.name)} ▾ <small>${els.length}</small></div><div class="tr"></div></div>`);
    out.push(`<div class="els">${els.map((e) => row(`${e.named ? "" : "<i>"}${esc(short(e.id))}${e.named ? "" : "</i>"}`, e.on.map(([a, b]) => block("elb", a, b)).join(""), `el${e.id === hoverEl ? " hl" : ""}${e.id === draft.target?.el ? " sel" : ""}`, `data-el="${esc(e.id)}" data-tip-el="1"`)).join("")}</div>`);
  }
  if (M().cues) out.push(row("Sound", M().cues.map((c) => pip(`dia${c.el === draft.sound?.el ? " sel" : ""}`, c.t, "", `data-t="${c.t}" data-cue="${esc(c.el)}" data-tip="${esc(c.el)} · ${fmt(c.t)}${c.db != null ? " · " + c.db + " dB" : ""} · click: hear it, answer it"`)).join(""), "grp"));
  out.push(row("QA", findings().map((f) => block(`qa ${f.severity} ${app.state?.findings[f.id]?.status || "open"}`, f.t0, Math.max(f.t1, f.t0 + 0.1), "⚠", `data-t="${f.at ?? f.t0}" data-finding="${esc(f.id)}" data-tip="${esc(f.check)}: ${esc(f.elements.join(" × ") || f.text)} · ${fmt(f.t0)}–${fmt(f.t1)}"`)).join(""), "grp"));
  const CH = Object.values(app.state?.choices || {}).filter((c) => c.time);
  if (CH.length)
    out.push(row("Choices", CH.map((c) => {
      const a = "t" in c.time ? c.time.t : c.time.t0,
        b = "t" in c.time ? a + 0.3 : c.time.t1;
      return block(`ch${c.picked ? " picked" : ""}`, a, b, esc(c.id), `data-t="${a}" data-choice="${esc(c.id)}" data-tip="${esc(c.id)} · ${esc(c.question)}${c.picked ? " · picked " + esc(c.picked) : " · waiting"}"`);
    }).join(""), "grp"));
  const N = liveNotes();
  out.push(row("Notes", N.map((n) => ("t" in n.time
    ? pip(`pin ${n.status}`, n.time.t, "", `data-t="${n.time.t}" data-note="${n.id}" data-tip="${n.id} · ${esc((n.comment || "").slice(0, 60))}"`)
    : block(`rng ${n.status}`, n.time.t0, n.time.t1, "", `data-t="${n.time.t0}" data-note="${n.id}" data-tip="${n.id} · ${esc((n.comment || "").slice(0, 60))}"`))).join(""), "grp"));
  out.push(`<div class="playhead" id="tl-ph"></div><div class="band" id="tl-band" hidden></div>`);
  rows.innerHTML = out.join("");
  place(t);
  band();
  mini();
}

function band() {
  const b = $("#tl-band");
  if (!b) return;
  const r = draft.range,
    a = r ? r[0] : draft.inAt;
  b.hidden = a == null || (r ? !inWin(r[0], r[1]) : !inWin(a, a));
  if (b.hidden) return;
  const x = (v) => `calc(var(--lab) + (100% - var(--lab)) * ${Math.max(0, Math.min(1, (v - W0) / (W1 - W0)))})`;
  b.classList.toggle("in", !r);
  b.style.left = x(a);
  b.style.width = r ? `calc((100% - var(--lab)) * ${(Math.min(W1, r[1]) - Math.max(W0, r[0])) / (W1 - W0)})` : "0";
}

function place(t) {
  const ph = $("#tl-ph");
  if (ph) {
    const f = (t - W0) / (W1 - W0);
    ph.style.left = `calc(var(--lab) + (100% - var(--lab)) * ${Math.max(0, Math.min(1, f))})`;
    ph.style.display = f < 0 || f > 1 ? "none" : "";
  }
  $("#tl-mini-ph").style.left = `${(t / end()) * 100}%`;
}

function mini() {
  const T = M().timeline;
  if (!T) return;
  const m = $("#tl-mini");
  if (!m.dataset.drawn) {
    m.dataset.drawn = 1;
    m.insertAdjacentHTML("afterbegin", T.segments.map((s, i) => `<b style="left:${(s.t0 / end()) * 100}%;width:${((s.t1 - s.t0) / end()) * 100}%" class="${i % 2 ? "odd" : ""}"></b>`).join(""));
  }
  $("#tl-win").style.cssText = `left:${(W0 / end()) * 100}%;width:${((W1 - W0) / end()) * 100}%`;
}

// ── the playhead drives everything: the window pages along, the element group follows the scene ──
player.on((t) => {
  const [a, b] = [W0, W1];
  frame(t);
  if (a !== W0 || b !== W1 || segmentAt(t) !== seg) draw();
  else place(t);
  if (hoverEl) outline(hoverEl);
});

// ── pointing both ways: a row outlines its element in the frame; the frame lights up the row under the pointer ──
function outline(id) {
  const t = player.t(),
    e = id && element(id);
  const b = id && (!e || onAt(e, t)) && boxOf(id, t);
  player.draw("hover", b ? [{ x: b[0], y: b[1], width: b[2] - b[0], height: b[3] - b[1], class: "hl" }] : []);
}
function hover(id) {
  if (id === hoverEl) return;
  hoverEl = id;
  rows.querySelectorAll(".row.el").forEach((r) => r.classList.toggle("hl", r.dataset.el === id));
  const r = id && rows.querySelector(`.row.el[data-el="${CSS.escape(id)}"]`);
  if (r) r.scrollIntoView({ block: "nearest" });
  outline(id);
}
rows.addEventListener("mouseover", (e) => {
  const r = e.target.closest(".row.el");
  if (r) hover(r.dataset.el);
  const d = e.target.closest("[data-tip]") || (r && e.target.closest(".lb") && r);
  if (d) {
    tip.textContent = d.dataset.tip || r.dataset.el;
    tip.classList.add("on");
  }
});
rows.addEventListener("mousemove", (e) => {
  tip.style.left = `${Math.min(innerWidth - tip.offsetWidth - 8, e.clientX + 12)}px`;
  tip.style.top = `${e.clientY - tip.offsetHeight - 10}px`;
});
rows.addEventListener("mouseout", (e) => {
  if (!e.relatedTarget || !rows.contains(e.relatedTarget)) {
    hover(null);
    tip.classList.remove("on");
  } else if (!e.relatedTarget.closest("[data-tip]")) tip.classList.remove("on");
});
$("#stage").addEventListener("mousemove", (e) => {
  if (player.playing() || e.buttons || $("#stage").dataset.preview) return; // nothing to point at while it moves, while a mark is being drawn, or on an option
  hover(hit(player.at(e)).top);
});
$("#stage").addEventListener("mouseleave", () => hover(null));

// a drag along the ruler is a range (a highlight to comment on: no handles, nothing moves)
let drag = null,
  dragged = 0; // when the last ruler drag ended: the click that follows it is the drag's, not a seek
const timeAt = (e, tr) => {
  const r = tr.getBoundingClientRect();
  return Math.max(0, Math.min(end(), W0 + ((e.clientX - r.left) / r.width) * (W1 - W0)));
};
rows.addEventListener("mousedown", (e) => {
  const tr = e.target.closest(".row.ruler .tr");
  if (!tr) return;
  e.preventDefault();
  drag = { tr, a: timeAt(e, tr), moved: false };
});
addEventListener("mousemove", (e) => {
  if (!drag) return;
  const b = timeAt(e, drag.tr);
  if (Math.abs(b - drag.a) > 0.1) drag.moved = true;
  if (drag.moved) setRange(drag.a, b);
});
addEventListener("mouseup", (e) => {
  if (!drag) return;
  const d = drag;
  drag = null;
  player.seek(d.moved ? draft.range?.[0] ?? d.a : d.a);
  dragged = performance.now();
});
// the element a note will point at keeps its row marked
point.on(() => {
  band();
  rows.querySelectorAll(".dia").forEach((x) => x.classList.toggle("sel", x.dataset.cue === draft.sound?.el));
  rows.querySelectorAll(".row.el").forEach((r) => r.classList.toggle("sel", r.dataset.el === draft.target?.el));
  const r = draft.target && rows.querySelector(`.row.el[data-el="${CSS.escape(draft.target.el)}"]`);
  if (r) r.scrollIntoView({ block: "nearest" });
});

// clicks only move the playhead: a block to its start, empty track to that moment
rows.addEventListener("click", (e) => {
  if (performance.now() - dragged < 400) return;
  const d = e.target.closest("[data-t]");
  if (d) {
    player.seek(+d.dataset.t);
    if (d.dataset.note) document.dispatchEvent(new CustomEvent("note:select", { detail: d.dataset.note }));
    if (d.dataset.finding) document.dispatchEvent(new CustomEvent("finding:select", { detail: d.dataset.finding }));
    if (d.dataset.choice) document.dispatchEvent(new CustomEvent("choice:select", { detail: d.dataset.choice }));
    if (d.dataset.cue) document.dispatchEvent(new CustomEvent("cue:select", { detail: d.dataset.cue }));
    return;
  }
  const tr = e.target.closest(".tr");
  if (tr) {
    const r = tr.getBoundingClientRect();
    player.seek(W0 + ((e.clientX - r.left) / r.width) * (W1 - W0));
  }
});
$("#tl-mini").addEventListener("click", (e) => {
  const r = e.currentTarget.getBoundingClientRect();
  const t = ((e.clientX - r.left) / r.width) * end();
  player.seek(t);
  frame(t, true);
  draw();
});

export function zoom(z) {
  ZOOM = z;
  document.querySelectorAll("#tl-zoom button").forEach((b) => b.classList.toggle("on", +b.dataset.z === z));
  frame(player.t(), true);
  draw();
}
export function zoomStep(dir) {
  const Z = [6, 20, 60, 0],
    i = Z.indexOf(ZOOM);
  zoom(Z[Math.max(0, Math.min(Z.length - 1, i + dir))]);
}
$("#tl-zoom").onclick = (e) => {
  const b = e.target.closest("button");
  if (b) zoom(+b.dataset.z);
};

export const timeline = {
  render: draw, // the snapshot changed (notes)
  maps() {
    $("#tl-mini").removeAttribute("data-drawn");
    $("#tl-mini").querySelectorAll("b").forEach((b) => b.remove());
    frame(player.t(), true);
    draw();
  },
  // jump to the note after (or before) this moment
  noteJump(dir) {
    const t = player.t(),
      ts = liveNotes()
        .map((n) => ["t" in n.time ? n.time.t : n.time.t0, n.id])
        .sort((a, b) => a[0] - b[0]);
    const n = dir > 0 ? ts.find((x) => x[0] > t + 0.02) : ts.reverse().find((x) => x[0] < t - 0.02);
    if (n) {
      player.seek(n[0]);
      document.dispatchEvent(new CustomEvent("note:select", { detail: n[1] }));
    }
  },
  sceneJump,
};
