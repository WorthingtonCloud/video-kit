// Where you are. The top line names the video and its stages (Story › Voice › Picture › Sound › Final for an explainer;
// contracts.json → stages), the finished ones ticked, the current one with its round. Click it: "How we got here", every
// step you took on this video (in the page, and the ones decided in chat that Claude logged), each with Comment (a note
// about that step, pinned to it, that waits for your send like any other) and Watch (to its moment).
import { app, $, post, esc, round } from "./core.js";
import { player } from "./player.js";

const box = $("#plog"),
  btn = $("#crumbs");
let open = false,
  commenting = null; // the step (its first line in the log) whose comment box is open
const cap = (w) => (w ? w[0].toUpperCase() + w.slice(1) : "");
const clock = (at) => new Date(at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
const day = (at) => new Date(at).toLocaleDateString("en-US", { month: "short", day: "numeric" });

function crumbs() {
  const S = app.state,
    R = round(),
    stages = app.ctx?.stages || [],
    i = stages.indexOf(S.stage || R?.stage);
  if (i < 0) return ($("#stages").innerHTML = R ? `<i>›</i><span class="st now">Round ${R.n}</span>` : "");
  const parts = stages.slice(0, i + 1).map((st, k) => `<span class="st ${k < i ? "done" : "now"}">${esc(cap(st))}${k === i && R ? ` · round ${R.n}` : ""}</span>`);
  // narrow windows fold the finished stages into "…"
  $("#stages").innerHTML = `<i>›</i>${i > 0 ? `<span class="fold">…</span><i class="fold">›</i>` : ""}` + parts.map((x, k) => (k < i ? `${x}<i class="d">›</i>` : x)).join("");
}

function log() {
  const S = app.state,
    stages = app.ctx?.stages || [],
    steps = S.steps.filter((s) => !s.pending);
  const by = new Map();
  for (const s of steps) by.set(s.stage || "", [...(by.get(s.stage || "") || []), s]);
  const order = [...new Set(["", ...stages, ...by.keys()])].filter((k) => by.has(k));
  const R = round();
  return `<h2>How we got here</h2><p class="sub">Your steps on this video, not Claude's. Comment on any step: it joins this round's feedback, pinned to that step.</p>` +
    order.map((st) => `<div class="pg ${st === (S.stage || "") ? "now" : ""}"><h4>${esc(cap(st) || "Before the stages")}</h4>${by.get(st).map((s) => {
      const k = s.seqs[0],
        mine = s.kind !== "step.logged" && s.kind !== "round.opened";
      return `<div class="pstep" data-seq="${k}"><time>${esc(clock(s.at))}<br><small>${esc(day(s.at))}</small></time>
        <p>${esc(s.text)}${s.where ? `<small>${esc(s.where)}</small>` : s.kind === "step.logged" ? "<small>in chat</small>" : ""}</p>
        <span class="acts">${s.t != null ? `<button data-p="watch" data-t="${s.t}" title="${s.version && R && s.version !== R.version ? `its moment, in v${R.version}` : "its moment"}">Watch</button>` : ""}${R && R.status !== "closed" ? `<button data-p="comment">Comment</button>` : ""}</span>
        ${commenting === k ? `<div class="cbox2"><textarea rows="2" data-pc placeholder="e.g. I want to revisit this"></textarea><div class="row"><button data-p="cancel">Cancel</button><button class="primary" data-p="send">Add to this round</button></div></div>` : ""}</div>`;
    }).join("")}</div>`).join("") +
    (R ? `<p class="sub here">Now: round ${R.n} on v${R.version}${R.stage ? ` (${esc(R.stage)})` : ""}.</p>` : "");
}

function draw() {
  if (!open) return;
  const typing = document.activeElement?.dataset?.pc != null ? document.activeElement.value : null;
  box.innerHTML = log();
  if (typing != null) {
    const t = box.querySelector("[data-pc]");
    if (t) (t.value = typing), t.focus();
  }
}
function toggle(on = !open) {
  open = on;
  box.hidden = !on;
  btn.setAttribute("aria-expanded", on);
  if (on) draw();
}
btn.onclick = (e) => {
  e.stopPropagation();
  toggle();
};
addEventListener("click", (e) => open && !e.target.closest("#plog, #crumbs") && toggle(false));
addEventListener("keydown", (e) => open && e.key === "Escape" && !e.target.closest?.("textarea") && toggle(false));
box.addEventListener("click", async (e) => {
  e.stopPropagation(); // a redraw detaches the button: the outside-click check below would read it as outside
  const b = e.target.closest("button[data-p]");
  if (!b) return;
  const k = +b.closest(".pstep")?.dataset.seq,
    a = b.dataset.p;
  if (a === "watch") {
    player.seek(+b.dataset.t);
    return toggle(false);
  }
  if (a === "comment") {
    commenting = k;
    draw();
    return box.querySelector("[data-pc]")?.focus();
  }
  if (a === "cancel") {
    commenting = null;
    return draw();
  }
  if (a === "send") {
    const t = box.querySelector("[data-pc]"),
      text = t.value.trim();
    if (!text) return t.focus();
    const s = app.state.steps.find((x) => x.seqs[0] === k),
      at = s.t ?? player.t();
    commenting = null;
    await post([{ type: "note.added", note: { time: { t: +(+at).toFixed(3) }, comment: text, step: { seq: k, text: s.text, at: s.at, kind: s.kind } } }]);
    draw();
  }
});

export const steps = {
  render() {
    if (!app.state) return;
    crumbs();
    draw();
  },
};
