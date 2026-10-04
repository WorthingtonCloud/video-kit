// Pointing. The composition that made this version loads hidden in the page and seeks with the player; a click asks it
// what's under that point (elementsFromPoint, as vs inspect does) and the smallest named thing on screen wins, with a
// breadcrumb up through what holds it. When the build has moved on since this version was rendered (or there's no
// composition), the element map answers instead, and the page says so.
//
// Three tools, no modes to think about: Point (click = an element, drag = a box), Arrow (drag: "this, there"; it keeps
// what sits under each end), Keep clear (drag: "nothing goes here"). A note with no mark is just words at a moment.
// Everything is stored as fractions of the frame (and of the target's own box), so it fits any size.
// A time is the playhead, or a range: drag along the ruler, or I and O.
import { app, $, esc, toast, cuts } from "./core.js";
import { player } from "./player.js";
import { element, onAt, boxAt, segmentAt, visibleAt, stackAt, findingsAt } from "./maps.js";

const stage = $("#stage");
const listeners = new Set();
let comp = null, // { win, doc, tl, names, elOf: Map(addr → el), W, H, t }
  tool = "point";
// what the human is pointing at, before it becomes a note
export const draft = (app.draft = { range: null, inAt: null, target: null, crumbs: [], mark: { type: "none" }, also: [], findings: [], follows: null, frame: null, sound: null });

// ── the composition, hidden ──
function loadComp(url, size) {
  comp = null;
  let f = $("#comp");
  if (!url) return f?.remove();
  if (!f) {
    f = document.createElement("iframe");
    f.id = "comp";
    f.title = "the composition (hidden; answers what's under a click)";
    f.setAttribute("aria-hidden", "true");
    f.tabIndex = -1;
    document.body.appendChild(f);
  }
  const [W, H] = size;
  f.style.cssText = `position:fixed;left:-${W + 4000}px;top:0;width:${W}px;height:${H}px;border:0;pointer-events:none`;
  f.onload = async () => {
    const win = f.contentWindow,
      doc = f.contentDocument;
    try {
      await doc.fonts?.ready;
      const s = doc.createElement("style");
      s.textContent = "*{pointer-events:auto !important}"; // as vs inspect does: hit-test everything that paints
      doc.head.appendChild(s);
      doc.querySelectorAll("video,audio").forEach((m) => ((m.muted = true), m.pause()));
      const tl = win.__timelines?.main;
      tl?.pause?.();
      comp = { win, doc, tl, names: win.__names, elOf: new Map(win.__names.all().map(({ addr, el }) => [addr, el])), W, H, t: null };
      notice();
    } catch (e) {
      comp = null;
      notice(`The composition didn't load (${e.message}): pointing from the element map.`);
    }
  };
  f.src = url;
}
function seekComp(t) {
  if (comp && comp.t !== t) {
    comp.tl.seek(t, false);
    comp.t = t;
  }
}

// ── what's under a point: the smallest named thing on screen, and what holds it ──
const real = (a) => a && a.includes("/") && !a.startsWith("frame/");
const shown = (a, t) => !element(a) || onAt(element(a), t);
export function hit([x, y], t = player.t()) {
  const seg = segmentAt(t)?.name;
  if (comp) {
    seekComp(t);
    const stack = [];
    for (const n of comp.doc.elementsFromPoint(x * comp.W, y * comp.H)) {
      const a = comp.names.addr(n);
      if (real(a) && !stack.includes(a) && shown(a, t)) stack.push(a);
    }
    const top = stack[0] || null,
      chain = [];
    for (let n = top && comp.elOf.get(top)?.parentElement; n && n.nodeType === 1; n = n.parentElement) {
      const a = comp.names.addr(n);
      if (!real(a)) break;
      if (a !== chain.at(-1) && a !== top && shown(a, t)) chain.push(a);
    }
    return { stack, top, crumbs: top ? [seg, ...chain.reverse(), top] : [] };
  }
  const stack = stackAt([x, y], t); // smallest first
  const top = stack[0] || null;
  // what holds it, by containment (a backdrop that fills the frame holds everything, so it isn't a level up)
  const up = stack.slice(1).filter((id) => {
    const b = boxAt(element(id), t);
    return b && (b[2] - b[0]) * (b[3] - b[1]) < 0.6;
  });
  return { stack, top, crumbs: top ? [seg, ...up.reverse(), top] : [] };
}
// an element's box at a moment: the map's (what vs inspect measured), else the composition's own
export function boxOf(id, t = player.t()) {
  const b = boxAt(element(id), t);
  if (b || !comp) return b;
  seekComp(t);
  const el = comp.elOf.get(id);
  const r = el?.getBoundingClientRect();
  return r && r.width ? [r.left / comp.W, r.top / comp.H, r.right / comp.W, r.bottom / comp.H].map((v) => +v.toFixed(4)) : null;
}
const r4 = (v) => +v.toFixed(4);
const overlapping = (b, t) =>
  visibleAt(t)
    .map((e) => [e.id, boxAt(e, t)])
    .filter(([, x]) => x && x[0] < b[2] && x[2] > b[0] && x[1] < b[3] && x[3] > b[1] && (x[2] - x[0]) * (x[3] - x[1]) < 0.6)
    .map(([id]) => id);
// what a keep-clear zone protects: what sits mostly inside it (the phone it was drawn around), never something that only
// pokes in (the label fighting the phone): vs inspect lets these stay in the zone and flags anything else that enters
const within = (b, t) =>
  visibleAt(t)
    .map((e) => [e.id, boxAt(e, t)])
    .filter(([, x]) => {
      const a = x && (x[2] - x[0]) * (x[3] - x[1]);
      if (!a || a >= 0.6) return false;
      const w = Math.max(0, Math.min(x[2], b[2]) - Math.max(x[0], b[0])),
        h = Math.max(0, Math.min(x[3], b[3]) - Math.max(x[1], b[1]));
      return (w * h) / a >= 0.6;
    })
    .map(([id]) => id);

// ── the marks ──
// the target as the agent will need it later: its box now (where the click fell inside it), and its words and time on
// screen, so the next version can be measured against them
function setTarget(id, at) {
  const t = player.t(),
    b = id && boxOf(id, t),
    e = id && element(id),
    h = (app.maps?.elements?.step || 0.15) / 2 + 1e-3,
    on = e?.on.find(([a, z]) => t >= a - h && t <= z + h);
  draft.target = id
    ? { el: id, box: b, ...(at && b ? { at: [r4((at[0] - b[0]) / (b[2] - b[0] || 1)), r4((at[1] - b[1]) / (b[3] - b[1] || 1))] } : {}),
        ...(e ? { text: e.text } : {}), ...(on ? { on } : {}) }
    : null;
}
function pin() {
  draft.frame = player.frame();
}
export function select(pt) {
  const h = hit(pt);
  draft.crumbs = h.crumbs;
  setTarget(h.top, pt);
  draft.mark = { type: "click", at: pt.map(r4) };
  pin();
  changed();
}
export function crumb(id) {
  setTarget(id);
  changed();
}
// a follow-up to an answered note: same moment, same target (under its new name if it was renamed)
export function followUp(n) {
  const id = n.resolution?.renamed || n.target?.el,
    e = id && element(id);
  draft.crumbs = e ? [e.segment, e.id] : [];
  setTarget(e ? e.id : null);
  draft.follows = n.id;
  pin();
  changed();
}
// a note about one sound effect (the timeline's Sound row): the cue is the target, at its own moment
export function soundOf(cue) {
  Object.assign(draft, { crumbs: [], mark: { type: "none" }, also: [], findings: [], follows: null, range: null, inAt: null });
  draft.target = { el: cue.el };
  draft.sound = { el: cue.el, t: cue.t, sound: cue.sound, db: cue.db };
  pin();
  changed();
}
// a note about a finding: its element (if the map knows it) is the target, and the finding rides along
export function about(fid, el) {
  const e = el && element(el);
  draft.crumbs = e ? [e.segment, e.id] : [];
  setTarget(e ? e.id : null);
  draft.findings = [fid];
  pin();
  changed();
}
function finish(a, b) {
  const t = player.t();
  const box = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])].map(r4);
  if (tool === "arrow") {
    const from = hit(a),
      to = hit(b);
    draft.mark = { type: "arrow", from: a.map(r4), to: b.map(r4), under_from: from.stack, under_to: to.stack };
    if (from.top) {
      draft.crumbs = from.crumbs;
      setTarget(from.top, a);
    }
  } else if (tool === "keep-clear") draft.also = [...draft.also, { type: "keep-clear", box, over: overlapping(box, t), keeps: within(box, t) }];
  else draft.mark = { type: "box", box, over: overlapping(box, t) };
  pin();
  changed();
}
export function clear(all = true) {
  Object.assign(draft, { target: null, crumbs: [], mark: { type: "none" }, also: [], findings: [], follows: null, frame: null, sound: null }, all ? { range: null, inAt: null } : {});
  changed();
}
export function setTool(k) {
  tool = k;
  document.querySelectorAll("#tools button").forEach((b) => b.classList.toggle("on", b.dataset.tool === k));
  stage.dataset.tool = k;
  const d = $("#drawbtn");
  d.textContent = `${{ point: "Draw", arrow: "Arrow", "keep-clear": "Keep clear" }[k]} ▾`;
  d.classList.toggle("on", k !== "point");
}
// a range: I and O at the playhead (either order), or a drag on the ruler
export function mark(which) {
  const t = +player.t().toFixed(3);
  if (which === "in") {
    draft.inAt = t;
    draft.range = draft.range && draft.range[1] > t ? [t, draft.range[1]] : null;
  } else {
    const a = draft.inAt ?? draft.range?.[0];
    if (a == null) return toast("Press I first: it marks where the range starts.");
    draft.range = t !== a ? [Math.min(a, t), Math.max(a, t)] : null;
  }
  changed();
}
export function setRange(a, b) {
  draft.range = Math.abs(b - a) >= 0.1 ? [+Math.min(a, b).toFixed(3), +Math.max(a, b).toFixed(3)] : null;
  changed();
}

// ── drawing: the target in red, an arrow or a click in red, a box or a keep-clear zone in amber ──
function draw(live) {
  const shapes = [],
    t = draft.target,
    m = live || draft.mark;
  if (t?.box) shapes.push({ x: t.box[0], y: t.box[1], width: t.box[2] - t.box[0], height: t.box[3] - t.box[1], class: "tgt" });
  const rect = (b, cls) => shapes.push({ x: b[0], y: b[1], width: b[2] - b[0], height: b[3] - b[1], class: cls });
  for (const k of [m, ...draft.also]) {
    if (k.type === "box") rect(k.box, "box");
    else if (k.type === "keep-clear") rect(k.box, "keep");
    else if (k.type === "click") shapes.push({ tag: "ellipse", cx: k.at[0], cy: k.at[1], rx: 0.012, ry: 0.012 * aspect(), class: "dot" });
    else if (k.type === "arrow") shapes.push(...arrow(k.from, k.to));
  }
  player.draw("draft", shapes);
  const tag = $("#tag");
  if (t?.box) {
    tag.textContent = t.el.slice(t.el.indexOf("/") + 1);
    tag.style.cssText = `left:${t.box[0] * 100}%;top:${t.box[1] * 100}%`;
    tag.hidden = false;
  } else tag.hidden = true;
}
const aspect = () => {
  const r = stage.getBoundingClientRect();
  return r.width / (r.height || 1);
};
// an arrowhead that stays a true arrowhead on a frame of any shape: worked out in pixels, stored back in fractions
function arrow(a, b) {
  const r = stage.getBoundingClientRect(),
    A = [a[0] * r.width, a[1] * r.height],
    B = [b[0] * r.width, b[1] * r.height],
    ang = Math.atan2(B[1] - A[1], B[0] - A[0]),
    L = 14;
  const head = [ang + 2.6, ang - 2.6].map((d) => [(B[0] + L * Math.cos(d)) / r.width, (B[1] + L * Math.sin(d)) / r.height]);
  return [
    { tag: "line", x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: "arr" },
    { tag: "polygon", points: `${b[0]},${b[1]} ${head[0]} ${head[1]}`, class: "head" },
    { tag: "ellipse", cx: a[0], cy: a[1], rx: 0.008, ry: 0.008 * aspect(), class: "dot" },
  ];
}

function changed() {
  draw();
  listeners.forEach((fn) => fn(draft));
}

// the line under the picture: what the pointer would answer, and where the answers come from
function notice(msg) {
  const R = app.ctx?.round,
    n = $("#notice");
  const text =
    msg ??
    (!R?.elements
      ? `No element map for v${R?.version}: box, arrow and keep-clear still work; clicks find nothing (vs inspect makes the map).`
      : comp
        ? ""
        : R.exact?.elements
          ? R.video?.startsWith("/@") || (cuts() && R.cut !== app.state?.rounds.at(-1)?.cut)
            ? `Pointing from the ${R.cut === "16x9" ? "widescreen" : "vertical"} v${R.version}'s own element map.`
            : `Pointing from v${R.version}'s own element map (its composition isn't here: the build has moved on).`
          : `Pointing from the nearest element map: the build has changed since v${R.version}, so outlines may be off.`);
  n.textContent = text;
  n.hidden = !text;
}

// ── the mouse on the picture: pausing is annotating ──
let down = null;
stage.addEventListener("mousedown", (e) => {
  if (e.button !== 0) return;
  e.preventDefault();
  if (stage.dataset.preview) return toast(`That's option ${stage.dataset.preview.toUpperCase()} on the stage, not the render: pick it, or press 0 to point at the render.`);
  if (player.playing()) player.pause();
  down = { p: player.at(e), x: e.clientX, y: e.clientY, moved: false };
});
addEventListener("mousemove", (e) => {
  if (!down) return;
  if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) down.moved = true;
  if (!down.moved) return;
  const b = player.at(e).map((v) => Math.max(0, Math.min(1, v)));
  const a = down.p;
  if (tool === "arrow") draw({ type: "arrow", from: a, to: b });
  else draw({ type: tool === "keep-clear" ? "keep-clear" : "box", box: [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])] });
});
addEventListener("mouseup", (e) => {
  if (!down) return;
  const d = down;
  down = null;
  const b = player.at(e).map((v) => Math.max(0, Math.min(1, v)));
  if (d.moved) finish(d.p, b);
  else if (tool === "point") select(d.p.map((v) => Math.max(0, Math.min(1, v))));
});
// the Draw menu: Point is what a click does; Arrow and Keep clear are one pick away (or V, A, K)
$("#drawbtn").onclick = () => ($("#tools").hidden = !$("#tools").hidden);
$("#tools").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (b?.dataset.tool) setTool(b.dataset.tool);
  else if (b?.id === "tool-clear") clear();
  $("#tools").hidden = true;
});
addEventListener("click", (e) => !e.target.closest(".drawmenu") && ($("#tools").hidden = true));

// a mark belongs to the frame it was made on: moving to another frame lets it go (a range stays)
player.on(() => {
  if (draft.frame != null && player.frame() !== draft.frame && !player.playing() && !draft.range && !draft.sound) clear(false); // a sound isn't a frame's
});

export const point = {
  on: (fn) => listeners.add(fn),
  maps() {
    const R = app.ctx.round;
    // the composition lays out at its own size (the timeline's), whatever size the render was encoded at
    loadComp(R.comp, app.maps.timeline?.size || R.size || [1080, 1920]);
    clear();
    notice();
  },
  // the note this draft becomes (notes.js adds the words)
  note() {
    const t = +player.t().toFixed(3),
      seg = segmentAt(draft.range ? draft.range[0] : t);
    return {
      time: draft.range ? { t0: draft.range[0], t1: draft.range[1] } : { t },
      ...(cuts() ? { cut: app.cut } : {}), // both shapes in this round: the note is about the one on screen
      segment: seg?.name ?? null,
      scene: seg ? seg.scene || seg.kind || null : null,
      target: draft.target,
      crumbs: draft.crumbs,
      mark: draft.mark,
      also: draft.also,
      visible: visibleAt(draft.range ? draft.range[0] : t).map((e) => e.id),
      // the findings live here, about this target: the agent sees the note and the finding together
      findings: [...new Set([...draft.findings, ...findingsAt(draft.range ? draft.range[0] : t, draft.target?.el).map((f) => f.id)])],
      ...(draft.follows ? { follows: draft.follows } : {}),
      ...(draft.sound ? { sound: draft.sound } : {}),
    };
  },
  describe() {
    const m = draft.mark,
      f = (p) => `(${p[0].toFixed(2)}, ${p[1].toFixed(2)})`;
    const parts = [];
    if (m.type === "arrow") parts.push(`arrow to ${f(m.to)}, over ${m.under_to.length ? esc(m.under_to[0].split("/").pop()) : "nothing"}`);
    else if (m.type === "box") parts.push(`box ${f(m.box.slice(0, 2))}–${f(m.box.slice(2))}`);
    for (const k of draft.also) parts.push(`keep-clear${k.over.length ? " over " + esc(k.over.map((x) => x.split("/").pop()).join(", ")) : ""}`);
    return parts.join(" · ");
  },
  get comp() {
    return comp;
  },
};
setTool("point");
