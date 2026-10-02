// The scrubber under the video: the whole video at a glance, with the timeline folded away. The scenes shade it; the
// round's checks are amber ticks, your notes red dots, and an answer of Claude's waiting for your look a red ring. Drag
// to move; hover to see the moment and the scene.
import { app, $, esc, round, liveNotes } from "./core.js";
import { player } from "./player.js";
import { findings, segmentAt } from "./maps.js";

const bar = $("#scrub"),
  tip = $("#scrub-tip");
const end = () => player.end() || 1;
const pct = (t) => `${Math.max(0, Math.min(100, (t / end()) * 100))}%`;
const at = (n) => ("t" in n.time ? n.time.t : n.time.t0);
const short = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;

function segs() {
  $("#scrub-segs").innerHTML = (app.maps?.timeline?.segments || []).map((s) => `<i style="left:${pct(s.t0)};width:${((s.t1 - s.t0) / end()) * 100}%"></i>`).join("");
}
function marks() {
  if (!app.state) return;
  const R = round(),
    out = findings().map((f) => `<i style="left:${pct(f.at ?? f.t0)}"></i>`);
  for (const n of liveNotes()) {
    // an answer waiting for your look (made on an older version) is a ring; a note of this round a dot
    const ring = ["resolved", "wontdo"].includes(n.status) && R && n.version !== R.version;
    out.push(`<i class="${ring ? "c" : `n${n.status === "accepted" ? " done" : ""}`}" style="left:${pct(at(n))}" data-id="${esc(n.id)}"></i>`);
  }
  $("#scrub-marks").innerHTML = out.join("");
}
function place(t) {
  $("#scrub-ph").style.left = pct(t);
  $("#scrub-played").style.width = pct(t);
}
player.on(place);

const timeAt = (e) => {
  const r = bar.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * end();
};
let dragging = false;
bar.addEventListener("pointerdown", (e) => {
  dragging = true;
  bar.setPointerCapture(e.pointerId);
  player.seek(timeAt(e));
});
bar.addEventListener("pointermove", (e) => {
  const t = timeAt(e),
    s = segmentAt(t);
  tip.hidden = false;
  tip.style.left = pct(t);
  tip.textContent = `${short(t)}${s ? ` · ${s.name}` : ""}`;
  if (dragging) player.seek(t);
});
bar.addEventListener("pointerup", () => (dragging = false));
bar.addEventListener("pointerleave", () => (tip.hidden = true));

export const scrub = {
  render: marks,
  maps() {
    segs();
    marks();
    place(player.t());
  },
};
