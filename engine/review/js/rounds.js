// What Claude did with your notes, first thing in a round: each answer is what Claude says it changed and what the new
// version measured (a claimed fix that measures as nothing is flagged). Looks right, Still wrong (with words), Follow up,
// or Compare the two versions side by side. Also here: the patterns Claude asks about (Learn), and the verdict on the
// version, one click (it waits with the rest of your feedback, and Undo takes it back).
import { app, $, post, undo, fmt, esc, round, cuts } from "./core.js";
import { compare } from "./compare.js";
import { followFrom, watch } from "./notes.js";
import { player } from "./player.js";

const el = $("#tab-rounds"),
  learnEl = $("#asks-l"),
  verdictEl = $("#verdict-approve");
let reopening = null; // the answer whose "still wrong" box is open

const when = (n) => ("t" in n.time ? fmt(n.time.t) : `${fmt(n.time.t0)} → ${fmt(n.time.t1)}`);
// three facts kept apart (vs review, feedback.py): Claude says it fixed it · the next version measured the change · you
// say it's right. The verdict is the measurement's, never Claude's word.
const VERDICT = {
  changed: "✓ Measured: it changed",
  removed: "✓ Measured: it's removed",
  other: "⚠ Measured: it changed, but not the way you asked",
  contrary: "⚠ Measured: it went the other way",
  unchanged: "⚠ Measured: no change",
  gone: "⚠ Measured: it's gone",
  unmeasured: "Not measured",
};
const ASKED = { move: "Move it", bigger: "Bigger", smaller: "Smaller", longer: "Longer", shorter: "Shorter", simpler: "Less busy", remove: "Remove it" };
const VERIFIED = ["changed", "removed"];
const OVER = { other: "it changed, not the way you asked", contrary: "it went the other way", unchanged: "no change measured", gone: "it's gone", unmeasured: "not measured" };
// older measurements carry only a flag: read the verdict from it, as vs review does
const verdictOf = (m) =>
  m.verdict || (m.gone ? (m.flag ? "gone" : "removed") : /^nothing measurable/.test(m.flag || "") ? "unchanged" : /^asked/.test(m.flag || "") ? (/louder|quieter/.test(m.flag) ? "contrary" : "other") : "changed");
const short = (id) => id.slice(id.indexOf("/") + 1).replace(/^~(ex-)?(k:)?/, "");
const heldStep = (kind, note) => app.state.steps.find((s) => s.pending && s.kind === kind && s.note === note);

function answer(n) {
  const r = n.resolution || {},
    m = n.measured,
    R = round();
  const waiting = n.status === "resolved" || n.status === "wontdo";
  const head = n.status === "wontdo" ? "Claude won't change it" : m ? `Claude says it's fixed in v${m.to}` : R && R.version !== n.version ? `Claude says it's fixed in v${R.version}` : "Claude says it's fixed: in the next version";
  const said = r.said ? `<p class="claude"><b>Claude:</b> ${esc(r.said)}</p>` : "";
  const v = m && verdictOf(m),
    detail = m ? (m.summary || "").replace(/ · ⚠ .*$/, "") : "";
  // a stand-in (less busy = fewer things on screen) hints at what was asked; it doesn't prove it
  const proxy = m?.strength === "proxy" && v === "changed";
  const meas = m
    ? v === "unmeasured"
      ? `<p class="meas flag">Not measured (${esc(m.why || "nothing to compare")}): this one is your eyes.${detail && !detail.startsWith("not measured") ? `<br>What it did see: ${esc(detail)}` : ""}</p>`
      : `<p class="meas${!VERIFIED.includes(v) || proxy ? " flag" : ""}"><b>${proxy ? "≈ Measured by a stand-in" : VERDICT[v]}</b>${detail ? ` · ${esc(detail)}` : ""}${proxy ? "<br>Fewer things on screen isn't always less busy: your eyes decide." : ""}${
          v === "unchanged" && n.status === "resolved" ? "<br>Claude says it changed; the next version shows nothing measurable. Check it with your eyes." : ["other", "contrary", "gone"].includes(v) && m.flag ? `<br>${esc(m.flag)}` : ""
        }</p>`
    : n.status === "resolved"
      ? `<p class="meas">Measured when the next version opens.</p>`
      : "";
  const held = heldStep("note.accepted", n.id) || heldStep("note.reopened", n.id);
  // your eyes outrank the measurement: accepting a fix it couldn't confirm is allowed, and said beside it
  const over = (vv) => (OVER[vv] ? ` (over the measurement: ${OVER[vv]})` : "");
  const acts = held
    ? `<div class="doneline ${held.kind === "note.reopened" ? "no" : ""}"><span>${held.kind === "note.accepted" ? `✓ You said: looks right${over(v)}` : "You said: still wrong"} <span class="held">not sent</span></span><button data-r="undo" data-seqs="${held.seqs.join(",")}">Undo</button></div>`
    : n.status === "accepted"
      ? `<div class="doneline"><span>✓ You said it looks right${over(n.accepted?.verdict)}</span></div>`
      : reopening === n.id
        ? `<textarea rows="2" data-reopen placeholder="What's still wrong?"></textarea><div class="btns"><button data-r="cancel">Cancel</button><button class="primary" data-r="reopen-send">Still wrong ⏎</button></div>`
        : `<div class="btns"><button data-r="watch">Watch it</button>${m ? `<button data-r="compare">${m.sound || (m.moment && (m.audio?.changed_secs || 0) >= 0.1) ? "Hear" : "Compare"} v${m.from} · v${m.to}</button>` : ""}${waiting ? `<button class="primary" data-r="accept">Looks right</button><button data-r="reopen">Still wrong…</button>` : ""}<button data-r="follow">Follow up</button></div>`;
  return `<div class="res ${n.status}${m?.flag ? " flagged" : ""}" data-id="${n.id}" ${waiting && !held ? "data-todo" : ""}>
    <div class="when">${cuts() || n.cut === "16x9" ? `<span class="shape">${n.cut === "16x9" ? "wide" : "tall"}</span>` : ""}<b>${when(n)}</b>${n.target?.el ? ` · ${esc(short(r.renamed || n.target.el))}` : ""} · ${esc(head)}</div>
    <q>${n.ask ? `${esc(ASKED[n.ask])}${n.comment ? ": " : ""}` : ""}${esc(n.comment) || (n.ask ? "" : "(a mark, no words)")}</q>${said}${meas}${acts}</div>`;
}

// the learning prompt: a pattern Claude spotted (by counting) and worded; the human decides how far it reaches
const kindName = () => (app.ctx?.kind === "reel" ? "reel" : "explainer");
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
      : `<div class="btns"><button class="primary" data-r="remember" title="A rule for every video you make">Every video</button><button data-r="kind" title="A rule for every ${esc(kindName())} you make">Every ${esc(kindName())}</button><button data-r="project" title="A rule for this video, nowhere else">This video only</button><button data-r="ignore" title="Not a rule: never asked again">Ignore</button></div>`}</div>`;
  }).join("");
}

// the verdict on this version: one click, and it waits with the rest of your feedback
function approval() {
  const R = round(),
    S = app.state;
  if (!R || R.status === "closed") return "";
  // both shapes in a round: each is approved on its own (the one on screen), so one can be done while the other isn't
  const both = cuts(),
    nm = both ? `the ${R.cut === "16x9" ? "widescreen" : "vertical"} v${R.version}` : `v${R.version}`,
    done = S.approved.find((a) => a.version === R.version && a.cut === R.cut),
    held = S.steps.find((s) => s.pending && s.kind === "version.approved" && s.version === R.version && (!s.cut || s.cut === R.cut));
  if (held)
    return `<button class="verdict-btn on" data-r="undo" data-seqs="${held.seqs.join(",")}">✓ Approved: ${nm} is done <span class="held">not sent · undo</span></button>
      <p class="dhint">It goes to Claude with the rest of your feedback when you send.${both ? " The other shape has its own Approve: switch to it at the top." : ""}</p>`;
  if (done) return `<div class="doneline"><span>✓ ${nm} approved ${esc(done.at.slice(11, 16))}: Claude makes its final from it</span></div>`;
  return `<button class="verdict-btn" data-r="approve">Approve ${nm}: it's done</button>
    <p class="dhint">One click. Only when nothing's left to fix: Claude then makes the final from ${nm}.${both ? " Each shape is approved on its own." : ""}</p>`;
}

export const rounds = {
  render() {
    const S = app.state;
    if (!S) return;
    // only the latest round's cards: an answer shown through a round the person sent without acting on has lapsed, and
    // one their own note already spoke to (covered) is closed by those words
    const answered = Object.values(S.notes).filter((n) => (["resolved", "wontdo"].includes(n.status) && !n.lapsed && !n.covered) || heldStep("note.accepted", n.id) || heldStep("note.reopened", n.id));
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
  if (lid && ["remember", "kind", "project", "ignore"].includes(r)) return post([{ type: "lesson.decided", id: lid, decision: r }]);
  if (r === "approve") return post([{ type: "version.approved", version: R.version, cut: R.cut, video: R.video }]);
  const n = app.state.notes[id];
  if (r === "watch") return watch(n, "t" in n.time ? n.time.t : n.time.t0);
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
