// Reading the round's maps: when an element is on screen and where its box is, from build/elements.json (vs inspect
// kept a box whenever one moved; a box holds until the next). Shared by the timeline and the pointer.
import { app, cutPrefix } from "./core.js";

const M = () => app.maps || {};
let index = null,
  indexed = null;

export function element(id) {
  const items = M().elements?.items || [];
  if (indexed !== items) {
    index = new Map(items.map((e) => [e.id, e]));
    indexed = items;
  }
  return index.get(id) || null;
}
export function onAt(e, t) {
  const h = (M().elements?.step || 0.15) / 2 + 1e-3;
  return !!e && e.on.some(([a, b]) => t >= a - h && t <= b + h);
}
export function boxAt(e, t) {
  let b = null;
  for (const x of e?.boxes || []) {
    if (x[0] > t + 1e-3) break;
    b = x;
  }
  return (b || e?.boxes?.[0])?.slice(1) || null;
}
export const segmentAt = (t) => (M().timeline?.segments || []).find((s) => t >= s.t0 && t < s.t1) || M().timeline?.segments?.at(-1);
// every element on screen at a moment (what a note carries as "visible"), minus the backdrop: the frame, its light and
// its dust are on every frame, so a note on empty ground listed "~ex-spot, ~ex-mote, ~ex-mote#2 …" (an explainer, Oct 4,
// 2026), and a click on empty ground could land on a speck. The same set as review.py's BACKDROP and mapchecks' AMBIENT.
export const BACKDROP = /^frame\/|\/~ex-(spot|mote|glow|dust)(#\d+)?$/;
export const visibleAt = (t) => (M().elements?.items || []).filter((e) => !BACKDROP.test(e.id) && onAt(e, t));
const inside = (b, [x, y]) => b && x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3];
// the map's own answer to "what's under this point": every element on screen whose box holds it, smallest first
export function stackAt(pt, t) {
  return visibleAt(t)
    .map((e) => [e, boxAt(e, t)])
    .filter(([, b]) => inside(b, pt))
    .sort((p, q) => (p[1][2] - p[1][0]) * (p[1][3] - p[1][1]) - (q[1][2] - q[1][0]) * (q[1][3] - q[1][1]))
    .map(([e]) => e.id);
}

// The findings a round shows: vs inspect's warnings (things that can be by design: the human confirms or dismisses
// them), its errors only when they were put to the human (errors never reach a round otherwise), and qa.py's warnings on
// this render. Each carries where it came from.
// With both shapes in a round, these are the shape on screen's, named as vs review names them (the other shape's ids
// carry its cut: "16x9:f-…"), so an answer about one shape never answers the other.
export function findings() {
  const asked = new Set(app.state?.rounds.at(-1)?.asked || []),
    pre = cutPrefix(),
    named = (f, source) => ({ ...f, id: pre + f.id, source });
  return [
    ...(M().findings?.items || []).filter((f) => asked.has(pre + f.id) || f.severity === "warning").map((f) => named(f, "inspect")),
    ...(M().qa?.items || []).map((f) => named(f, "qa")),
  ].sort((a, b) => a.t0 - b.t0);
}
// the ones live at a moment (and touching an element, when there is one)
export const findingsAt = (t, el) =>
  findings().filter((f) => t >= f.t0 - 0.05 && t <= f.t1 + 0.05 && (!el || !f.elements.length || f.elements.includes(el)));
