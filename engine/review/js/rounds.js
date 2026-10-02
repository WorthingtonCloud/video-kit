// What Claude did with your notes, first thing in a round: each answer is what Claude says it changed and what the new
// version measured (a claimed fix that measures as nothing is flagged). Looks right, Still wrong (with words), Follow up,
// or Compare the two versions side by side. Also here: the patterns Claude asks about (Learn), and the verdict on the
// version, one click (it waits with the rest of your feedback, and Undo takes it back).
import { app, $, post, undo, fmt, esc, round } from "./core.js";
import { compare } from "./compare.js";
import { followFrom } from "./notes.js";
import { player } from "./player.js";

const el = $("#tab-rounds"),
  learnEl = $("#asks-l"),
  verdictEl = $("#verdict-approve");
let reopening = null; // the answer whose "still wrong" box is open

const when = (n) => ("t" in n.time ? fmt(n.time.t) : `${fmt(n.time.t0)} → ${fmt(n.time.t1)}`);
const short = (id) => id.slice(id.indexOf("/") + 1).replace(/^~(ex-)?(k:)?/, "");
const heldStep = (kind, note) => app.state.steps.find((s) => s.pending && s.kind === kind && s.note === note);

function answer(n) {
  const r = n.resolution || {},
    m = n.measured,
    R = round();
  const waiting = n.status === "resolved" || n.status === "wontdo";
  const head = n.status === "wontdo" ? "Claude won't change it" : m ? `Claude fixed it in v${m.to}` : R && R.version !== n.version ? `Claude fixed it in v${R.version}` : "Claude fixed it: in the next version";
  const said = r.said ? `<p class="claude"><b>Claude:</b> ${esc(r.said)}</p>` : "";
  const meas = m
    ? `<p class="meas${m.flag ? " flag" : ""}">${m.flag && /nothing measurable/.test(m.flag) && !m.pixels && !m.audio ? "The page can't measure this kind of change (a timing elsewhere, a thing it can't see), so this one is your eyes." : `Measured: ${esc(m.summary || "")}`}</p>`
    : n.target
      ? `<p class="meas">Measured when the next version opens.</p>`
      : `<p class="meas">Nothing to measure: the note didn't point at one thing. Watch it.</p>`;
  const held = heldStep("note.accepted", n.id) || heldStep("note.reopened", n.id);
  const acts = held
    ? `<div class="doneline ${held.kind === "note.reopened" ? "no" : ""}"><span>${held.kind === "note.accepted" ? "✓ You said: looks right" : "You said: still wrong"} <span class="held">not sent</span></span><button data-r="undo" data-seqs="${held.seqs.join(",")}">Undo</button></div>`
    : n.status === "accepted"
      ? `<div class="doneline"><span>✓ You said it looks right</span></div>`
      : reopening === n.id
        ? `<textarea rows="2" data-reopen placeholder="What's still wrong?"></textarea><div class="btns"><button data-r="cancel">Cancel</button><button class="primary" data-r="reopen-send">Still wrong ⏎</button></div>`
        : `<div class="btns"><button data-r="watch">Watch it</button>${m ? `<button data-r="compare">${m.sound || (m.moment && (m.audio?.changed_secs || 0) >= 0.1) ? "Hear" : "Compare"} v${m.from} · v${m.to}</button>` : ""}${waiting ? `<button class="primary" data-r="accept">Looks right</button><button data-r="reopen">Still wrong…</button>` : ""}<button data-r="follow">Follow up</button></div>`;
  return `<div class="res ${n.status}${m?.flag ? " flagged" : ""}" data-id="${n.id}" ${waiting && !held ? "data-todo" : ""}>
    <div class="when"><b>${when(n)}</b>${n.target?.el ? ` · ${esc(short(r.renamed || n.target.el))}` : ""} · ${esc(head)}</div>
    <q>${esc(n.comment) || "(a mark, no words)"}</q>${said}${meas}${acts}</div>`;
}

// the learning prompt: a pattern Claude spotted (by counting) and worded; the human decides what it becomes
const DEST = { profile: "your profile (a value)", lessons: "your lessons (a rule)", check: "a check (your threshold)", kit: "the kit (a bug anyone would hit)", video: "this video only" };
function lessons() {
  const heldOf = (l) => app.state.steps.find((s) => s.pending && s.kind === "lesson.decided" && s.lesson === l.id);
  const L = Object.values(app.state.lessons).filter((l) => l.decision == null || heldOf(l));
  return L.map((l) => {
    const held = heldOf(l);
    return `<div class="res lesson" data-lesson="${esc(l.id)}" ${l.decision == null ? "data-todo" : ""}>
    <div class="when"><b>${l.count ? `Seen ${l.count}×` : "A pattern"}</b> · ${esc(l.tag || "")} · would go to ${esc(DEST[l.dest] || l.dest)}</div>
    <p class="plain">${esc(l.text)}</p>
    ${l.evidence?.length ? `<p class="dhint">from ${esc(l.evidence.slice(0, 6).join(", "))}${l.evidence.length > 6 ? " …" : ""}</p>` : ""}
    ${held ? `<div class="doneline"><span>${esc(held.text.split(": ").pop())} <span class="held">not sent</span></span><button data-r="undo" data-seqs="${held.seqs.join(",")}">Undo</button></div>`
      : `<div class="btns"><button class="primary" data-r="remember">Remember</button><button data-r="video">This video only</button><button data-r="ignore">Ignore</button></div>`}</div>`;
  }).join("");
}

// the verdict on this version: one click, and it waits with the rest of your feedback
function approval() {
  const R = round(),
    S = app.state;
  if (!R || R.status === "closed") return "";
  const done = S.approved.find((a) => a.version === R.version && a.cut === R.cut),
    held = S.steps.find((s) => s.pending && s.kind === "version.approved" && s.version === R.version);
  if (held)
    return `<button class="verdict-btn on" data-r="undo" data-seqs="${held.seqs.join(",")}">✓ Approved: v${R.version} is done <span class="held">not sent · undo</span></button>
      <p class="dhint">It goes to Claude with the rest of your feedback when you send.</p>`;
  if (done) return `<div class="doneline"><span>✓ v${R.version} approved ${esc(done.at.slice(11, 16))}: Claude makes the finals from it</span></div>`;
  return `<button class="verdict-btn" data-r="approve">Approve v${R.version}: it's done</button>
    <p class="dhint">One click. Only when nothing's left to fix: Claude then makes the finals from v${R.version}.</p>`;
}

export const rounds = {
  render() {
    const S = app.state;
    if (!S) return;
    const answered = Object.values(S.notes).filter((n) => ["resolved", "wontdo"].includes(n.status) || heldStep("note.accepted", n.id) || heldStep("note.reopened", n.id));
    const a = document.activeElement,
      typing = a?.dataset?.reopen != null ? a.value : null;
    el.innerHTML = answered.map(answer).join("");
    learnEl.innerHTML = lessons();
    verdictEl.innerHTML = approval();
    if (typing != null) {
      const t = el.querySelector("[data-reopen]");
      if (t) {
        t.value = typing;
        t.focus();
      }
    }
  },
};

async function act(e) {
  const b = e.target.closest("button[data-r]");
  if (!b) return;
  const r = b.dataset.r,
    id = b.closest(".res")?.dataset.id,
    R = round();
  const lid = b.closest(".lesson")?.dataset.lesson;
  if (r === "undo") return undo(b.dataset.seqs.split(",").map(Number));
  if (lid && ["remember", "video", "ignore"].includes(r)) return post([{ type: "lesson.decided", id: lid, decision: r }]);
  if (r === "approve") return post([{ type: "version.approved", version: R.version, cut: R.cut, video: R.video }]);
  const n = app.state.notes[id];
  if (r === "watch") return player.seek("t" in n.time ? n.time.t : n.time.t0);
  if (r === "compare") return compare(n);
  if (r === "accept") return post([{ type: "note.accepted", id }]);
  if (r === "follow") return followFrom(id);
  if (r === "reopen") {
    reopening = id;
    rounds.render();
    return el.querySelector("[data-reopen]")?.focus();
  }
  if (r === "cancel") {
    reopening = null;
    return rounds.render();
  }
  if (r === "reopen-send") return reopen(id);
}
async function reopen(id) {
  const t = el.querySelector("[data-reopen]"),
    text = t?.value.trim();
  if (!text) return t?.focus();
  reopening = null;
  await post([{ type: "note.reopened", id, text }]);
}
for (const x of [el, learnEl, verdictEl]) x.addEventListener("click", act);
el.addEventListener("keydown", (e) => {
  if (e.target.dataset?.reopen == null) return;
  if (e.key === "Escape") {
    reopening = null;
    rounds.render();
  } else if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    reopen(e.target.closest(".res").dataset.id);
  }
});
