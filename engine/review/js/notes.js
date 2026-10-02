// The note box under the video (what the note is pinned to, the words, Add), your notes in the round's panel, Claude's
// questions back on them, and the scene at the playhead ("This scene is done"). Every one of these waits, held, with
// Undo, until you Approve & send.
import { app, $, post, undo, fmt, round, toast, esc, liveNotes } from "./core.js";
import { player } from "./player.js";
import { point, draft, crumb, clear, followUp, soundOf } from "./point.js";
import { solo } from "./mix.js";
import { findingsAt, visibleAt, segmentAt } from "./maps.js";

const el = document.querySelector("#tab-notes");
let replying = null; // {id, act}: the note (or finding) whose answer, reopen or dismiss box is open
const when = (n) => ("t" in n.time ? fmt(n.time.t) : `${fmt(n.time.t0)} → ${fmt(n.time.t1)}`);
const short = (id) => id.slice(id.indexOf("/") + 1);
const draftTime = () => (draft.range ? { t0: draft.range[0], t1: draft.range[1] } : { t: player.t() });
const ASKS = { quieter: "Quieter", louder: "Louder", different: "A different sound", remove: "Remove it" };

// the scene at the playhead, and whether the human called it done (vs inspect then holds its frames to this version)
function sceneLine() {
  const R = round(),
    seg = R && segmentAt(player.t());
  if (!seg) return "";
  const d = app.state.done?.[seg.name],
    held = app.state.steps.find((s) => s.pending && s.kind.startsWith("scene.") && s.segment === seg.name);
  if (held)
    return `<span class="done">${held.kind === "scene.done" ? `✓ <b>${esc(seg.name)}</b> is done` : `<b>${esc(seg.name)}</b> reopened`} <span class="held">not sent</span></span><button data-act="undo" data-seqs="${held.seqs.join(",")}">Undo</button>`;
  return d
    ? `<span class="done">✓ <b>${esc(seg.name)}</b> is done (v${d.version}): Claude keeps it as it is</span><button data-scene="reopen" data-seg="${esc(seg.name)}">Reopen it</button>`
    : `<span>Scene <b>${esc(seg.name)}</b></span><button data-scene="done" data-seg="${esc(seg.name)}" title="Claude won't change it: vs inspect holds its frames to v${R.version}">This scene is done</button>`;
}

// the note box under the video: what it will be pinned to (the chip), what it points at in detail (above the box), and
// where it goes (a draft for this round; after Send, straight to Claude)
const shortName = (id) => id.slice(id.indexOf("/") + 1).replace(/^~(ex-)?(k:)?/, "");
function compose() {
  const R = round(),
    box = $("#c-text"),
    open = R && R.status !== "closed";
  box.disabled = !open;
  $("#c-add").disabled = !open;
  const when = fmt(draft.range ? draft.range[0] : player.t());
  box.placeholder = !open
    ? "No round open: Claude opens one on a rendered version."
    : draft.sound
      ? `About this sound (${fmt(draft.sound.t)}): what should change? Or answer it with a button above.`
      : draft.target
        ? `What about ${shortName(draft.target.el)}? (${when})`
        : draft.range
          ? `About ${fmt(draft.range[0])} → ${fmt(draft.range[1])}: what's wrong?`
          : `Leave a note at ${when}${R?.status === "sent" ? " (it goes straight to Claude: the round is sent)" : ""} · click the picture to point at something`;
  const chip = $("#c-chip"),
    m = point.describe(),
    what = draft.sound ? `♪ ${draft.sound.sound}` : draft.target ? shortName(draft.target.el) : draft.range ? `${fmt(draft.range[0])} → ${fmt(draft.range[1])}` : m ? m.split(" ")[0] : "";
  chip.hidden = !what;
  chip.innerHTML = what ? `<span>${esc(what)}${draft.target && m ? ` · ${esc(m.split(" ")[0])}` : ""}</span><button data-c="letgo" title="Let go (esc)">×</button>` : "";
  const x = $("#c-extra"),
    inner = pointing();
  x.hidden = !inner;
  x.innerHTML = inner;
}

// what the note will point at: the breadcrumb (click one to go up a level) and the marks
function pointing() {
  const c = draft.crumbs,
    out = [];
  if (draft.sound) {
    const q = cue(draft.sound.el);
    out.push(`<div class="sound"><div class="markline">sound: <b>${esc(draft.sound.sound)}</b> · ${esc(short(draft.sound.el))} · ${fmt(draft.sound.t)}${draft.sound.db != null ? ` · ${draft.sound.db} dB against the voice` : ""}</div>
      <div class="row"><button data-snd="alone" ${q?.file ? "" : 'disabled title="vs mix again to hear one sound alone"'}>▶ Alone</button><button data-snd="context">▶ In the mix</button></div>
      <div class="asks">${Object.entries(ASKS).map(([k, w]) => `<button data-ask="${k}">${w}</button>`).join("")}</div></div>`);
    return out.join("");
  }
  if (draft.target && c.length > 2)
    out.push(`<div class="crumbs">${c.map((id, i) => (i === 0 ? `<span>${esc(id)}</span>` : `<button data-crumb="${esc(id)}" class="${id === draft.target.el ? "sel" : ""}">${esc(short(id))}</button>`)).join("<i>›</i>")}</div>`);
  const m = point.describe();
  if (m) out.push(`<div class="markline">mark: <b>${m}</b></div>`);
  if (draft.findings.length) out.push(`<div class="markline">about: <b>${draft.findings.map(esc).join(", ")}</b></div>`);
  if (out.length && findingsAt(draft.range ? draft.range[0] : player.t()).length) out.push(`<div class="onscreen">${onscreen()}</div>`);
  if (draft.follows) out.push(`<div class="markline">follows: <b>${esc(draft.follows)}</b></div>`);
  return out.join("");
}

// what's on screen at this moment: how much, whether a title is up, and any finding live here
function onscreen() {
  const t = draft.range ? draft.range[0] : player.t();
  const n = visibleAt(t).length,
    title = (app.maps?.timeline?.titles || []).find((x) => t >= x.t0 && t < x.t1),
    live = findingsAt(t).filter((f) => app.state?.findings[f.id]?.status !== "dismissed");
  return `${n} element${n === 1 ? "" : "s"} on screen · ${title ? `title up: ${esc(title.id)}` : "title zone empty"}${live.length ? ` · <span class="warn">⚠ ${live.length} finding${live.length > 1 ? "s" : ""} here</span>` : ""}`;
}

const cue = (el) => (app.maps?.cues || []).find((c) => c.el === el);
const heldOf = (kind, note) => app.state.steps.find((s) => s.pending && s.kind === kind && s.note === note);
const STATUS = { draft: "not sent", sent: "with Claude", reopened: "with Claude: still wrong" };

// your notes: what's waiting to be sent, and what's with Claude (an answered one moves up to "Check Claude's fixes")
function item(n) {
  const added = heldOf("note.added", n.id),
    tgt = n.target?.el ? ` · ${esc(short(n.target.el))}` : "";
  return `<div class="item ${n.status}" data-id="${n.id}">
    <span class="ico">${n.sound ? "♪" : "t" in n.time ? "●" : "▬"}</span>
    <div><span class="seek" data-t="${"t" in n.time ? n.time.t : n.time.t0}">${n.sound?.ask ? `${esc(ASKS[n.sound.ask])}: ${esc(n.sound.sound)}${n.comment ? " · " : ""}` : ""}${esc(n.comment) || (n.sound?.ask ? "" : "<i>(a mark, no words)</i>")}</span>
      <small>${when(n)}${n.segment ? " · " + esc(n.segment) : ""}${tgt}${n.follows ? " · follows " + esc(n.follows) : ""}${n.step ? " · about a step" : ""} <span class="status ${n.status}">${esc(STATUS[n.status] || n.status)}</span></small></div>
    <div class="acts">${added ? `<button data-act="undo" data-seqs="${added.seqs.join(",")}">Remove</button>` : ""}</div></div>`;
}

// Claude's questions back on your notes (a choice offered as the question shows in Decide instead)
function question(n) {
  const q = [...n.thread].reverse().find((h) => h.type === "question"),
    held = heldOf("note.answered", n.id);
  const body = held
    ? `<div class="doneline"><span>You answered <span class="held">not sent</span></span><button data-act="undo" data-seqs="${held.seqs.join(",")}">Undo</button></div>`
    : replying?.id === n.id
      ? `<textarea rows="2" data-reply="answer" placeholder="Your answer"></textarea><div class="btns"><button data-act="cancel">Cancel</button><button class="primary" data-act="answer-send" data-id="${n.id}">Answer ⏎</button></div>`
      : `<div class="btns"><button data-act="watch" data-id="${n.id}">Watch it</button><button class="primary" data-act="answer" data-id="${n.id}">Answer…</button></div>`;
  return `<div class="res question" data-id="${n.id}" ${held ? "" : "data-todo"}>
    <div class="when"><b>${when(n)}</b>${n.target?.el ? ` · ${esc(short(n.target.el))}` : ""} · your note</div>
    <q>${esc(n.comment) || "(a mark, no words)"}</q>
    <p class="claude"><b>Claude asks:</b> ${esc(q?.text || "")}</p>${body}</div>`;
}
const asksChoice = (n) => n.thread.at(-1)?.type === "choice" || Object.values(app.state.choices).some((c) => c.for === n.id && !c.picked);

export const notes = {
  render() {
    const R = round();
    const a = document.activeElement,
      typing = a?.dataset?.reply ? ["[data-reply]", a.value] : null;
    const live = liveNotes(),
      mine = live.filter((n) => ["draft", "sent", "reopened"].includes(n.status)),
      asked = Object.values(app.state.notes).filter((n) => n.status === "question" && !asksChoice(n) || heldOf("note.answered", n.id));
    $("#asks-q").innerHTML = asked.map(question).join("");
    el.innerHTML = mine.length ? mine.map(item).join("") : `<p class="empty">Nothing yet. Pause anywhere, click the picture if it's about one thing, and type in the box under the video.</p>`;
    $("#verdict-scene").innerHTML = `<div class="scene-line" id="c-scene">${sceneLine()}</div>`;
    compose();
    if (typing) {
      const t = $("#asks-q").querySelector(typing[0]);
      if (t) {
        t.value = typing[1];
        t.focus();
      }
    }
  },
  maps() {
    notes.render();
  },
};

async function add(ask) {
  const t = $("#c-text"),
    text = t.value.trim();
  if (!text && !draft.target && draft.mark.type === "none" && !draft.also.length) return t.focus();
  const note = { ...point.note(), comment: text };
  if (ask && note.sound) note.sound = { ...note.sound, ask };
  t.value = ""; // cleared first: the panel redraws as soon as the note lands
  grow();
  t.blur(); // back to watching: space plays again, and the keys mean what they say
  try {
    await post([{ type: "note.added", note }]);
    clear();
  } catch {
    t.value = text;
    grow();
  }
}

// a follow-up: back to the note's moment and target, a new note that points at the old one
export function followFrom(id) {
  const n = app.state.notes[id];
  player.seek("t" in n.time ? n.time.t : n.time.t0);
  followUp(n);
  $("#c-text").focus();
}

// the note box: Enter adds, shift-Enter a new line, Esc lets go; it grows with what's typed
const box = $("#c-text");
function grow() {
  box.style.height = "auto";
  box.style.height = `${Math.min(120, box.scrollHeight + 2)}px`;
}
box.addEventListener("input", grow);
box.addEventListener("focus", () => player.playing() && player.pause());
box.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    add();
  } else if (e.key === "Escape") {
    box.blur();
    clear();
  }
});
$("#c-add").onclick = () => add();
$("#c-chip").addEventListener("click", (e) => e.target.closest("[data-c=letgo]") && clear());
$("#c-extra").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.ask) return add(b.dataset.ask);
  if (b.dataset.snd === "alone") return solo(cue(draft.sound.el)).catch((x) => toast(`Can't play it alone: ${x.message}`, true));
  if (b.dataset.snd === "context") {
    const t = draft.sound.t;
    player.seek(Math.max(0, t - 1.2));
    player.play();
    const stop = (u) => u > t + 1.4 && (player.pause(), stops.delete(stop));
    return stops.add(stop);
  }
  if (b.dataset.crumb) return crumb(b.dataset.crumb);
});

// your notes, Claude's questions, the scene line: one handler for the three
async function click(e) {
  const s = e.target.closest(".seek");
  if (s && !e.target.closest("button")) return player.seek(+s.dataset.t);
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.scene === "done") return post([{ type: "scene.done", segment: b.dataset.seg }]);
  if (b.dataset.scene === "reopen") return post([{ type: "scene.reopened", segment: b.dataset.seg }]);
  const id = b.dataset.id,
    act = b.dataset.act;
  if (act === "undo") return undo(b.dataset.seqs.split(",").map(Number));
  if (act === "watch") {
    const n = app.state.notes[id];
    return player.seek("t" in n.time ? n.time.t : n.time.t0);
  }
  if (act === "answer") {
    replying = { id, act };
    notes.render();
    return $("#asks-q [data-reply]")?.focus();
  }
  if (act === "cancel") {
    replying = null;
    return notes.render();
  }
  if (act === "answer-send") return send(id);
}
for (const x of [el, $("#asks-q"), $("#verdict-scene")]) x.addEventListener("click", click);
async function send(id) {
  const box = $("#asks-q [data-reply]"),
    text = box?.value.trim();
  if (!text) return box?.focus();
  replying = null;
  await post([{ type: "note.answered", id, text }]);
}
$("#asks-q").addEventListener("keydown", (e) => {
  if (!e.target.dataset?.reply) return;
  if (e.key === "Escape") {
    replying = null;
    notes.render();
  } else if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send(e.target.closest(".res").dataset.id);
  }
});
const stops = new Set(); // "In the mix": pause a moment after the sound
player.on((t) => {
  stops.forEach((f) => f(t));
  const sc = $("#c-scene"),
    now = segmentAt(t)?.name;
  if (sc && sc.dataset.seg !== now) {
    sc.dataset.seg = now;
    sc.innerHTML = sceneLine();
  }
  if (!player.playing() || document.activeElement !== box) compose();
});
point.on(() => compose());
// the timeline picked a note: show it here
document.addEventListener("note:select", (e) => {
  document.querySelectorAll(".item.sel, .res.sel").forEach((x) => x.classList.remove("sel"));
  const it = document.querySelector(`#dbody [data-id="${CSS.escape(e.detail)}"]`);
  if (it) {
    document.dispatchEvent(new CustomEvent("panel:open", { detail: it.closest(".dsec").id }));
    it.classList.add("sel");
    it.scrollIntoView({ block: "nearest" });
  }
});
// the timeline's Sound row: that sound becomes what the note is about
document.addEventListener("cue:select", (e) => {
  const q = cue(e.detail);
  if (q) soundOf(q);
});
