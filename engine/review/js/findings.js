// Findings, said plainly, each with Claude's recommendation (vs review advise). A check's findings come as one card ("6
// moments · something bright near a phone's edges"): one click takes Claude's advice, or the other way, or a note; one
// by one when they differ. A decision from an earlier round shows as what you said then, and answering again replaces
// it. Fix it = it's real, Claude changes it; Leave it = fine as it is. Errors from vs inspect only reach a round when
// Claude put them to you (vs review open --ask).
import { app, $, post, undo, esc, round } from "./core.js";
import { player } from "./player.js";
import { about } from "./point.js";
import { findings } from "./maps.js";

const el = $("#asks-f"),
  opened = new Set(), // checks shown one by one
  changing = new Set(); // checks whose carried answer the human chose to change
const mmss = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;
const short = (id) => id.slice(id.indexOf("/") + 1).replace(/^~(ex-)?(k:)?/, "");
const at = (f) => f.at ?? f.t0;
const say = (d, many) => (d === "fix" ? (many ? "fix them" : "fix it") : many ? "leave them" : "leave it");
const cap = (w) => w[0].toUpperCase() + w.slice(1);

function groups() {
  const by = new Map();
  for (const f of findings()) {
    const k = f.check || "other";
    by.set(k, [...(by.get(k) || []), f]);
  }
  return [...by.entries()];
}
// one finding, this round: decided now (held = not sent yet), decided in an earlier round, or open
function stateOf(f) {
  const R = round(),
    d = app.state.findings[f.id],
    held = app.state.steps.find((s) => s.pending && s.findings?.includes(f.id));
  if (!d) return { open: true };
  const dec = d.status === "confirmed" ? "fix" : "leave";
  if (d.round === R?.n && d.carried && !changing.has(f.check || "other")) return { now: true, dec, carried: d.carried.round };
  if (d.covered && !changing.has(f.check || "other")) return { now: true, dec, note: d.covered.by }; // your note answered it
  return d.round === R?.n && !d.carried && !d.covered ? { now: true, dec, held } : { earlier: true, dec, round: d.carried?.round || d.round, open: true };
}

function line(st, many, seqs) {
  if (st.note) // your own note spoke to it: answered, nothing to click
    return `<div class="doneline ${st.dec === "fix" ? "no" : ""}"><span>✓ ${cap(say(st.dec, many))} <span class="held">from your note</span></span><button data-f="change">Change</button></div>`;
  if (st.carried) // answered in an earlier round: it stands, nothing to click
    return `<div class="doneline ${st.dec === "fix" ? "no" : ""}"><span>✓ ${cap(say(st.dec, many))} <span class="held">your answer from round ${st.carried}</span></span><button data-f="change">Change</button></div>`;
  return `<div class="doneline ${st.dec === "fix" ? "no" : ""}"><span>✓ ${cap(say(st.dec, many))}${seqs ? ` <span class="held">not sent</span>` : ""}</span>${seqs ? `<button data-f="undo" data-seqs="${seqs.join(",")}">Undo</button>` : ""}</div>`;
}

function card([check, F]) {
  const P = app.ctx?.plain?.[check] || {},
    many = F.length > 1,
    adv = app.state.advice[F[0].id],
    st = F.map(stateOf);
  const allNow = st.every((x) => x.now) && st.every((x) => x.dec === st[0].dec);
  const earlier = st.filter((x) => x.earlier),
    was = earlier.length === F.length && earlier.every((x) => x.dec === earlier[0].dec) ? earlier[0] : null;
  const heldSeqs = [...new Set(st.flatMap((x) => x.held?.seqs || []))];
  const first = adv?.advice || "leave",
    other = first === "fix" ? "leave" : "fix";
  const head = `<div class="when"><b>${many ? `${F.length} moments` : mmss(at(F[0]))}</b> · ${F.some((f) => f.severity === "error") ? "an error Claude asks you about" : "automatic check"}</div>
    <p class="fname">${esc(P.name || check)}</p>
    <p class="plain">${esc(adv?.plain || P.says || F[0].text || "")}</p>
    ${adv ? `<p class="advice"><b>Claude recommends: ${say(adv.advice, many)}.</b> ${esc(adv.why || "")}</p>` : `<p class="noadv">Claude hasn't weighed in on ${many ? "these" : "this"} yet.</p>`}
    ${was ? `<p class="was">In round ${was.round} you said “${say(was.dec, many)}”. Your answer here replaces it.</p>` : ""}`;
  const acts = allNow
    ? line(st[0], many, heldSeqs.length ? heldSeqs : null)
    : `<div class="btns"><button class="primary" data-f="${first}">${cap(say(first, many))}${adv ? " (Claude's advice)" : ""}</button><button data-f="${other}">${cap(say(other, many))}</button>
        ${many ? `<button data-f="each">${opened.has(check) ? "Fold ▴" : "One by one ▾"}</button>` : `<button data-f="see" data-id="${esc(F[0].id)}">See it</button><button data-f="note" data-id="${esc(F[0].id)}">Note</button>`}</div>`;
  const each = many && opened.has(check)
    ? `<div class="each">${F.map((f, i) => {
        const x = st[i];
        return `<div class="one" data-id="${esc(f.id)}"><div class="when"><b>${mmss(at(f))}</b>${f.elements?.length ? ` · ${esc(f.elements.slice(0, 3).map(short).join(", "))}` : ""}</div>
          <p class="plain">${esc(f.text || "")}</p>
          ${x.now ? line(x, false, x.held ? x.held.seqs : null) : `<div class="btns sm"><button data-f="see" data-id="${esc(f.id)}">See it</button><button data-f="leave1" data-id="${esc(f.id)}">Leave it</button><button data-f="fix1" data-id="${esc(f.id)}">Fix it</button><button data-f="note" data-id="${esc(f.id)}">Note</button></div>`}</div>`;
      }).join("")}</div>`
    : "";
  return `<div class="res finding" data-check="${esc(check)}" ${st.some((x) => x.open) ? "data-todo" : ""}>${head}${acts}${each}</div>`;
}

function render() {
  if (!app.state) return;
  el.innerHTML = groups().map(card).join("");
}

// See it: to its moment, its zone drawn on the picture until the playhead moves on
function see(f) {
  player.seek(at(f));
  const b = f.box_n || f.box;
  player.draw("finding", b ? [{ x: b[0], y: b[1], width: b[2] - b[0], height: b[3] - b[1], class: "fzone" }] : []);
  shown = at(f);
}
let shown = null;
player.on((t) => {
  if (shown != null && Math.abs(t - shown) > 0.6) {
    shown = null;
    player.draw("finding", []);
  }
});
const decide = (F, d) => {
  const R = round(),
    todo = F.filter((f) => {
      const x = stateOf(f);
      return !(x.now && x.dec === d);
    });
  if (!todo.length) return;
  return post(todo.map((f) => ({ type: d === "fix" ? "finding.confirmed" : "finding.dismissed", id: f.id, check: f.check, round: R?.n })));
};

el.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-f]");
  if (!b) return;
  const card = b.closest(".finding"),
    check = card.dataset.check,
    F = groups().find(([k]) => k === check)?.[1] || [],
    f = F.find((x) => x.id === b.dataset.id),
    a = b.dataset.f;
  if (a === "undo") return undo(b.dataset.seqs.split(",").map(Number));
  if (a === "change") {
    changing.add(check);
    return render();
  }
  if (a === "fix" || a === "leave") return decide(F, a);
  if (a === "fix1" || a === "leave1") return decide([f], a.slice(0, -1));
  if (a === "each") {
    opened.has(check) ? opened.delete(check) : opened.add(check);
    return render();
  }
  if (a === "see") return see(f);
  if (a === "note") {
    see(f);
    about(f.id, f.elements?.[0]);
    $("#c-text").focus();
  }
});
// the timeline picked a finding: open its card one by one, and show it
document.addEventListener("finding:select", (e) => {
  const hit = groups().find(([, F]) => F.some((f) => f.id === e.detail));
  if (!hit) return;
  if (hit[1].length > 1) opened.add(hit[0]);
  render();
  document.dispatchEvent(new CustomEvent("panel:open", { detail: "sec-asks" }));
  el.querySelector(`.one[data-id="${CSS.escape(e.detail)}"], .finding[data-check="${CSS.escape(hit[0])}"]`)?.scrollIntoView({ block: "nearest" });
});

export const findingsPanel = { render, maps: render };
