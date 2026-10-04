// Review Studio's page: the panels, wired to the core, the keys, and the poll that brings the agent's answers in.
// The video gets the room: the round's panel and the timeline start folded (each remembered per browser), and F puts the
// video on the whole screen with the strip under it floating over the picture.
import { app, $, load, fit, toast, cuts, setCut } from "./core.js";
import { player, setup, sceneJump } from "./player.js";
import { timeline, zoomStep } from "./timeline.js";
import { notes } from "./notes.js";
import { point, mark, setTool, clear } from "./point.js";
import { mix } from "./mix.js";
import { rounds } from "./rounds.js";
import { decide } from "./decide.js";
import { rules } from "./rules.js";
import { scrub } from "./scrub.js";
import { findingsPanel } from "./findings.js";
import { loop } from "./loop.js";
import { panel } from "./panel.js";
import { steps } from "./steps.js";
import "./usage.js";

// ── the top bar folds while anything in it would overlap or clip (review.css .f1–.f4), measured, not set by fixed
//    widths: fixed widths went stale when the shape switch arrived, and the step strip spilled off both its edges, the
//    current step clipped under the stage names (a reviewer, Oct 4, 2026: "too crowded and things are overlapping") ──
{
  const top = $("#top"),
    L = $("#loop"),
    W = $("#crumbs"),
    F = ["f1", "f2", "f3", "f4"];
  const over = () => L.scrollWidth > L.clientWidth + 1 || W.scrollWidth > W.clientWidth + 1 || top.scrollWidth > top.clientWidth + 1;
  const fitTop = () => {
    top.classList.remove(...F);
    for (const c of F) {
      if (!over()) break;
      top.classList.add(c);
    }
  };
  let tm = 0; // a timer, not requestAnimationFrame: a background tab pauses frames, and the bar should be right on arrival
  const soon = () => {
    clearTimeout(tm);
    tm = setTimeout(fitTop, 30);
  };
  // the bar's own size, the sizes of what's in it (a web font arriving widens every word without touching the DOM),
  // and every change of its words
  const ro = new ResizeObserver(soon);
  [top, W, $(".top-r")].forEach((e) => ro.observe(e));
  new MutationObserver(soon).observe(top, { childList: true, subtree: true, characterData: true });
  document.fonts?.ready.then(soon);
}

// ── what stays folded: remembered in this browser (a private window forgets, and that's fine) ──
const remember = (k, v) => {
  try {
    v === undefined ? null : localStorage.setItem(`review.${k}`, v ? "1" : "0");
    return localStorage.getItem(`review.${k}`) === "1";
  } catch {
    return v ?? false;
  }
};
export function drawer(on = $("#drawer").hidden) {
  $("#drawer").hidden = !on;
  $("#dtab").hidden = on;
  $("#roundbtn").setAttribute("aria-expanded", on);
  remember("drawer", on);
  fit();
  decide.panel(on);
  mix.panel(on && $("#mix-h").getAttribute("aria-expanded") === "true");
}
// the Mix section: open = the stems are the sound
function mixOpen(on = $("#mix-h").getAttribute("aria-expanded") !== "true") {
  $("#mix-h").setAttribute("aria-expanded", on);
  $("#tab-mix").hidden = !on;
  mix.panel(on && !$("#drawer").hidden);
}
$("#mix-h").onclick = () => mixOpen();
export function timelineShown(on = $("#tl").hidden) {
  $("#tl").hidden = !on;
  $("#tl-toggle").setAttribute("aria-expanded", on);
  $("#tl-toggle").textContent = on ? "▾ Timeline" : "▴ Timeline";
  remember("timeline", on);
  if (on) timeline.render?.();
  fit();
}
$("#roundbtn").onclick = () => drawer();
// both shapes: the switch (and S) puts the other one on screen at the same moment
$("#shapes").onclick = (e) => {
  const b = e.target.closest("button[data-cut]");
  if (b) setCut(b.dataset.cut);
};
const otherCut = () => cuts()?.find((c) => c.cut !== app.cut)?.cut;
$("#dtab").onclick = () => drawer(true);
$("#dclose").onclick = () => drawer(false);
$("#tl-toggle").onclick = () => timelineShown();

// ── full screen: the browser's, when it allows it; the page's own otherwise ──
let idleT;
function idle() {
  document.body.classList.remove("idle");
  clearTimeout(idleT);
  idleT = setTimeout(() => player.playing() && document.activeElement !== $("#c-text") && document.body.classList.add("idle"), 2200);
}
export function fullscreen(on = !document.body.classList.contains("fs")) {
  document.body.classList.toggle("fs", on);
  if (on && !document.fullscreenElement) document.documentElement.requestFullscreen?.().catch(() => {});
  else if (!on && document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
  $("#fs").textContent = on ? "⛶ Exit full screen" : "⛶ Full screen";
  idle();
  requestAnimationFrame(fit);
}
$("#fs").onclick = () => fullscreen();
document.addEventListener("fullscreenchange", () => !document.fullscreenElement && document.body.classList.contains("fs") && fullscreen(false));
addEventListener("pointermove", idle);
player.on(() => document.body.classList.contains("fs") && !player.playing() && document.body.classList.remove("idle"));

// the keys: never while typing a note
document.addEventListener("keydown", (e) => {
  if (e.target.closest?.("textarea, input:not([type=range])") || e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.target.type === "range" && e.key.startsWith("Arrow")) return; // a focused slider takes its own arrows
  const k = e.key;
  if (k === " ") player.toggle();
  else if (k === "ArrowLeft" || k === "ArrowRight") {
    const d = k === "ArrowLeft" ? -1 : 1;
    e.shiftKey ? player.seek(player.t() + d) : player.step(d);
  } else if (k === "[") sceneJump(-1);
  else if (k === "]") sceneJump(1);
  else if (k === "n") $("#c-text").focus();
  else if (k === "N") timeline.noteJump(1);
  else if (k === "-") zoomStep(1);
  else if (k === "=" || k === "+") zoomStep(-1);
  else if (k === "f" || k === "F") fullscreen();
  else if ((k === "s" || k === "S") && otherCut()) setCut(otherCut());
  else if (k === "i" || k === "I") mark("in");
  else if (k === "o" || k === "O") mark("out");
  else if (k === "v" || k === "V") setTool("point");
  else if (k === "a" || k === "A") setTool("arrow");
  else if (k === "k" || k === "K") setTool("keep-clear");
  else if (k === "Escape") document.body.classList.contains("fs") && !draftActive() ? fullscreen(false) : clear();
  else return;
  e.preventDefault();
});
const draftActive = () => app.draft && (app.draft.target || app.draft.range || app.draft.mark.type !== "none" || app.draft.also.length);

// open the round's panel at a section (the timeline, a hash in the address, a link in the page)
document.addEventListener("panel:open", (e) => {
  if ($("#drawer").hidden) drawer(true);
  const sec = document.getElementById(e.detail);
  if (sec?.id === "sec-mix") mixOpen(true);
  sec?.scrollIntoView({ block: "start" });
});

// One address for the whole video: http://localhost:<port>/review/. What's on it follows the project, live, so the tab
// that's already open (any browser) is always right: the narration to listen to before there's a picture, the round's
// video, and the Mix section the moment vs mix makes one (it opens itself, once per new mix). A hash still opens a
// section, on load or when it changes.
let seenMix = null;
const follow = {
  render() {
    const C = app.ctx,
      R = app.state?.rounds.at(-1),
      tag = C.mixer ? `${C.mixer.tag}|${C.mixer.video}` : null;
    $("#sec-mix").hidden = !C.mixer;
    const lf = $("#listen"),
      listening = !!C.listen && !R;
    lf.hidden = !listening;
    $("#stage").hidden = listening;
    if (listening && lf.dataset.src !== C.listen) lf.src = lf.dataset.src = C.listen;
    if (tag && seenMix !== null && tag !== seenMix) {
      document.dispatchEvent(new CustomEvent("panel:open", { detail: "sec-mix" }));
      toast("A new mix is ready: it's open in this round's panel.");
    }
    if (tag !== null || seenMix === null) seenMix = tag ?? "";
  },
};
// the end of the flow (vs review finish): a Done button in the header, and a sheet with the finals to download and a way
// back in: pick the part, write a note, send it. The sheet opens by itself once per finish, in this browser.
const PARTS = [["the words", "About the words: "], ["the voice", "About the voice: "], ["the picture", "About the picture: "], ["the sound", "About the sound: "]];
function finishSheet(open) {
  const F = app.state?.finished;
  if (!F) return;
  $("#fn-files").innerHTML = F.files.map((f) => `<li><a href="${f.url}" download="${f.name}"><span>⤓ ${f.cut === "16x9" ? "Widescreen" : "Vertical"}</span><small>${f.name}</small></a></li>`).join("");
  $("#fn-parts").innerHTML = PARTS.map(([w, p]) => `<button data-p="${p}">${w}</button>`).join("");
  $("#fn-when").textContent = `Filed ${new Date(F.at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`;
  if (open) $("#finish-sheet").hidden = false;
}
const finished = {
  render() {
    const F = app.state?.finished;
    $("#donebtn").hidden = !F;
    if (!F) return;
    let seen = null;
    try {
      seen = localStorage.getItem("review.finished");
    } catch {}
    if (seen !== F.at) {
      try {
        localStorage.setItem("review.finished", F.at);
      } catch {}
      finishSheet(true);
    }
  },
};
$("#donebtn").onclick = () => finishSheet(true);
$("#fn-ok").onclick = () => ($("#finish-sheet").hidden = true);
$("#fn-parts").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-p]");
  if (!b) return;
  $("#finish-sheet").hidden = true;
  const t = $("#c-text");
  t.value = b.dataset.p;
  t.dispatchEvent(new Event("input", { bubbles: true }));
  t.focus();
});

const goHash = () => {
  const at = { "#mix": "sec-mix", "#rounds": "sec-fixes", "#decide": "sec-asks", "#notes": "sec-notes" }[location.hash];
  if (at && (at !== "sec-mix" || app.ctx.mixer)) document.dispatchEvent(new CustomEvent("panel:open", { detail: at }));
};
addEventListener("hashchange", goHash);

app.parts.push(notes, findingsPanel, decide, rounds, timeline, point, mix, rules, scrub, loop, steps, panel, follow, finished, { maps: () => setup(app.maps.timeline) });
await load();
drawer(remember("drawer"));
timelineShown(remember("timeline"));
// a round at the sound stage lands on the Mix section with no hash needed
if (app.ctx.mixer && app.state?.rounds.at(-1)?.stage === "sound" && !location.hash) document.dispatchEvent(new CustomEvent("panel:open", { detail: "sec-mix" }));
goHash();
setInterval(() => load().catch(() => {}), 2000);
