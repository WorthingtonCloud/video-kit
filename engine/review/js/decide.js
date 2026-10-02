// The Decide panel: the choices Claude offers (vs review offer) when there's more than one good way. Picking is the most
// precise feedback there is, so every option plays here, live, before the human picks:
//   · a variant is a built composition (vs review variant): it loads over the picture and follows the player's clock,
//     with the round's sound under it, so a motion or timing choice costs no render
//   · a music take plays through the Mix panel's stems (the levels as set there)
//   · a picture, clip or sound is shown (or played) as it is
//   · a paid option isn't made yet: its card says what it would cost, and picking it is the yes to that number
// "See option A" only shows it (the banner on the picture says so: not picked); 0–9 switch while it plays (0 = the render
// as it is). Picking is its own row: Pick A, Pick B, or Neither (with words), and the pick waits, with Undo, for your
// send. The page never builds or spends anything; Claude applies the pick (vs review apply).
import { app, $, post, undo, fmt, esc, toast } from "./core.js";
import { player } from "./player.js";
import { stems } from "./mix.js";

const el = $("#tab-decide"),
  stage = $("#stage");
let open = false,
  cur = null, // the choice on the stage
  showing = "", // its option on the stage ("" = the render as it is)
  saying = null, // the choice whose "none of these" box is open
  stopAt = null; // Play the choice: where it pauses
const views = new Map(); // preview url → {kind, node, win, tl, W, H, ready}
const layer = document.createElement("div");
layer.className = "preview";
layer.hidden = true;
stage.insertBefore(layer, $("#overlay"));
const banner = $("#banner");

const choices = () => Object.values(app.state?.choices || {});
const waiting = () => choices().filter((c) => !c.picked);
const optOf = (c, id) => c?.options.find((o) => o.id === id);
const t0Of = (c) => (c?.time ? ("t" in c.time ? c.time.t : c.time.t0) : null);
const when = (c) => (!c.time ? "" : "t" in c.time ? fmt(c.time.t) : `${fmt(c.time.t0)} → ${fmt(c.time.t1)}`);
const url = (p) => "/" + p.replace(/^\/+/, "");
// an option's words, without the letter it may already carry ("A · Red from the start" is shown under "See option A")
const bare = (o) => (o.label || "").replace(new RegExp(`^${o.id.toUpperCase()}\\s*[·:.)-]\\s*`), "");
const label = (o) => (o.kind === "take" ? `take ${o.take}${o.label ? " · " + esc(bare(o)) : ""}` : o.label ? esc(bare(o)) : { variant: "a variant", take: `music take ${o.take}`, video: "a clip", image: "a picture", audio: "a sound", paid: "not made yet" }[o.kind] || esc(o.kind));

// ── the previews: one node per option, made once, shown one at a time ──
function view(o) {
  const key = o.kind === "take" ? `take:${o.take}` : o.kind === "paid" ? `paid:${cur}:${o.id}` : url(o.preview);
  if (views.has(key)) return views.get(key);
  const v = { kind: o.kind, ready: o.kind !== "variant" };
  if (o.kind === "variant") {
    const f = document.createElement("iframe");
    f.title = `option ${o.id}: the composition, played live`;
    f.tabIndex = -1;
    f.setAttribute("aria-hidden", "true");
    f.onload = async () => {
      const win = f.contentWindow,
        doc = f.contentDocument,
        root = doc.querySelector("[data-composition-id]");
      try {
        await Promise.race([doc.fonts?.ready, new Promise((r) => setTimeout(r, 10000))]); // never forever (the rare stall)
        doc.querySelectorAll("video,audio").forEach((m) => ((m.muted = true), m.pause()));
        Object.assign(v, { win, doc, tl: win.__timelines?.main, W: +root.dataset.width, H: +root.dataset.height, ready: true });
        v.tl?.pause?.();
        fit();
        seek(player.t(), true);
      } catch (e) {
        toast(`Option ${o.id} didn't load: ${e.message}`, true);
      }
    };
    f.src = `${url(o.preview)}index.html`;
    v.node = f;
  } else if (o.kind === "image") {
    v.node = Object.assign(document.createElement("img"), { src: url(o.preview), alt: `option ${o.id}` });
  } else if (o.kind === "video" || o.kind === "audio") {
    v.node = Object.assign(document.createElement(o.kind), { src: url(o.preview), muted: o.kind === "video", preload: "auto", playsInline: true });
  } else if (o.kind === "paid") {
    v.node = document.createElement("div");
    v.node.className = "pv-paid";
    v.node.innerHTML = `<b>${esc(o.id.toUpperCase())}</b><span>${label(o)}</span><small>Not made yet: ${esc(o.cost || "")}</small>`;
  }
  if (v.node) {
    v.node.hidden = true;
    layer.appendChild(v.node);
  }
  views.set(key, v);
  return v;
}
// a composition lays out at its own size; it's scaled to fit the stage (and centered, if its shape differs)
function fit() {
  const sw = stage.clientWidth,
    sh = stage.clientHeight;
  for (const v of views.values())
    if (v.kind === "variant" && v.W) {
      const k = Math.min(sw / v.W, sh / v.H);
      Object.assign(v.node.style, { width: `${v.W}px`, height: `${v.H}px`, left: `${(sw - v.W * k) / 2}px`, top: `${(sh - v.H * k) / 2}px`, transform: `scale(${k})` });
    }
}
new ResizeObserver(fit).observe(stage);

// the option on the stage follows the player's clock: its timeline seeks, its clips and sounds keep up
function seek(t, force) {
  const c = choices().find((x) => x.id === cur),
    o = optOf(c, showing);
  if (!open || !o) return;
  const v = view(o),
    playing = player.playing();
  if (v.kind === "variant" && v.ready && v.tl) {
    v.tl.seek(t, false);
    v.doc.querySelectorAll("video[data-start]").forEach((m) => keepUp(m, t - +m.dataset.start, +m.dataset.duration, playing));
  } else if (v.kind === "video" || v.kind === "audio") keepUp(v.node, t - (t0Of(c) ?? 0), v.node.duration || 1e9, playing);
  if (stopAt != null && playing && t >= stopAt) {
    stopAt = null;
    player.pause();
  }
}
function keepUp(m, local, dur, playing) {
  if (local < 0 || local > dur) return m.paused || m.pause();
  if (playing) {
    if (m.paused) {
      m.currentTime = local;
      m.play().catch(() => {});
    } else if (Math.abs(m.currentTime - local) > 0.2) m.currentTime = local;
  } else {
    if (!m.paused) m.pause();
    if (Math.abs(m.currentTime - local) > 0.02) m.currentTime = local;
  }
}
player.on((t) => seek(t));

// put an option on the stage ("" = the render as it is): the others hide, the sound goes where this one needs it
async function show(id) {
  const c = choices().find((x) => x.id === cur),
    o = optOf(c, id);
  showing = o ? id : "";
  for (const v of views.values()) if (v.node) v.node.hidden = true;
  views.forEach((v) => (v.kind === "video" || v.kind === "audio") && v.node.pause());
  layer.hidden = !o || o.kind === "take" || o.kind === "audio";
  if (o && !layer.hidden) view(o).node.hidden = false;
  const audio = o && (o.kind === "take" || o.kind === "audio");
  if (o?.kind === "take") {
    try {
      await stems.use(o.take);
    } catch (e) {
      toast(`Can't play take ${o.take}: ${e.message}`, true);
    }
  } else await stems.use(null);
  if (o?.kind === "audio") view(o); // a sound plays over the muted picture
  app.video.muted = !!audio || !!player.clock;
  stage.dataset.preview = o && !audio ? o.id : "";
  banner.hidden = !o;
  banner.innerHTML = o ? `<span>Showing <b>option ${esc(o.id.toUpperCase())}</b> · not picked${o.kind === "variant" ? " · played live, not rendered" : ""}</span><button data-c="back">Back to the render</button>` : "";
  seek(player.t(), true);
  render();
}
banner.addEventListener("click", (e) => e.target.closest("[data-c=back]") && show(""));

// ── the panel ──
const heldPick = (c) => app.state.steps.find((s) => s.pending && s.kind === "choice.made" && s.choice === c.id);
function card(c) {
  const held = heldPick(c),
    picked = c.picked && (c.picked === "none" ? "neither" : `${c.picked.toUpperCase()}${optOf(c, c.picked) ? ` (${label(optOf(c, c.picked))})` : ""}`);
  const see = (o, i) => `<button class="opt${c.id === cur && o.id === showing ? " on" : ""}" data-c="see" data-o="${esc(o.id)}"><span class="see">${c.id === cur && o.id === showing ? "Showing" : "See"} ${o.id ? `option ${esc(o.id.toUpperCase())}` : "it as rendered"}<kbd>${i}</kbd></span>
      <span class="ol">${o.id ? label(o) : `v${app.state.rounds.at(-1)?.version ?? ""}, the version you're reviewing`}</span>
      ${o.timing ? `<small class="warn">timing differs: ${esc(o.timing)} (it plays over the round's sound)</small>` : ""}${o.cost ? `<small class="${o.paid ? "warn" : ""}">${esc(o.cost)}</small>` : ""}</button>`;
  const pick = held
    ? `<div class="doneline"><span>✓ Your pick: ${esc(picked)} <span class="held">not sent</span></span><button data-c="undo" data-seqs="${held.seqs.join(",")}">Undo</button></div>`
    : c.picked
      ? `<div class="doneline"><span>✓ You picked ${esc(picked)}${c.applied?.pick === c.picked ? " · Claude applied it" : ""}</span></div>`
      : saying === c.id
        ? `<textarea rows="2" data-say placeholder="Neither: what would work instead?"></textarea><div class="btns"><button data-c="none-cancel">Cancel</button><button class="primary" data-c="none-send">Neither ⏎</button></div>`
        : `<div class="pick"><span class="k">Your pick</span>${c.options.map((o) => `<button data-c="pick" data-o="${esc(o.id)}">${o.paid ? `Pick ${esc(o.id.toUpperCase())} (spends it)` : `Pick ${esc(o.id.toUpperCase())}`}</button>`).join("")}<button data-c="none">Neither…</button></div>`;
  return `<div class="res choice${c.picked ? " done" : ""}" data-choice="${esc(c.id)}" ${c.picked ? "" : "data-todo"}>
    <div class="when">${c.for ? `For your note${(() => { const n = app.state.notes[c.for]; return n ? ` at <b>${fmt("t" in n.time ? n.time.t : n.time.t0)}</b>` : ""; })()}` : "<b>A choice</b>"}${c.time ? ` · ${when(c)}` : ""} · ${esc(c.cost || "")}</div>
    <p class="plain">${esc(c.question)}</p>
    <div class="opts">${[...c.options, { id: "", kind: "render" }].map((o, i) => see(o, o.id ? i + 1 : 0)).join("")}</div>
    ${c.time ? `<div class="btns sm"><button data-c="play">▶ Play ${esc(when(c))}</button></div>` : ""}
    ${pick}${c.picked === "none" && c.said ? `<p class="dhint">You said: “${esc(c.said)}”</p>` : ""}</div>`;
}

function render() {
  const C = choices().filter((c) => !c.picked || heldPick(c) || c.round === app.state.rounds.at(-1)?.n); // done ones: this round's only
  if (cur && !choices().some((c) => c.id === cur)) cur = null;
  const a = document.activeElement,
    typing = a?.dataset?.say != null ? a.value : null;
  el.innerHTML = C.map(card).join("");
  if (typing != null) {
    const t = el.querySelector("[data-say]");
    if (t) {
      t.value = typing;
      t.focus();
    }
  }
}

async function pick(c, o, text) {
  await post([{ type: "choice.made", id: c.id, pick: o, ...(text ? { text } : {}) }]);
}

// a choice becomes the one on the stage: every option loads now, so a switch while it plays is instant
async function select(id) {
  if (id === cur) return;
  cur = id;
  open = true;
  await show("");
  choices().find((x) => x.id === cur)?.options.forEach(view);
}
// See option X: on the stage, at the choice's moment, playing (a still option would look like nothing happened)
async function seeIt(c, id) {
  await select(c.id);
  await show(id);
  const t = player.t(),
    a = t0Of(c),
    b = c.time && "t1" in c.time ? c.time.t1 : a;
  if (a != null && (t < a - 0.05 || t > b + 0.05)) player.seek(a);
  if (id) {
    stopAt = c.time && "t1" in c.time ? c.time.t1 : null;
    player.play();
  }
}

el.addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-c]"),
    box = e.target.closest(".choice"),
    c = box && choices().find((x) => x.id === box.dataset.choice);
  if (!c || !b) return;
  const k = b.dataset.c;
  if (k === "see") return seeIt(c, b.dataset.o);
  if (k === "undo") return undo(b.dataset.seqs.split(",").map(Number));
  if (k === "pick") return pick(c, b.dataset.o);
  if (k === "play") {
    await select(c.id);
    player.seek(t0Of(c));
    stopAt = "t1" in (c.time || {}) ? c.time.t1 : null;
    return player.play();
  }
  if (k === "none") {
    saying = c.id;
    render();
    return el.querySelector("[data-say]")?.focus();
  }
  if (k === "none-cancel") {
    saying = null;
    return render();
  }
  if (k === "none-send") return sayNone(c);
});
async function sayNone(c) {
  const t = el.querySelector("[data-say]"),
    text = t?.value.trim();
  if (!text) return t?.focus();
  saying = null;
  await pick(c, "none", text);
}
el.addEventListener("keydown", (e) => {
  if (e.target.dataset?.say == null) return;
  if (e.key === "Escape") {
    saying = null;
    render();
  } else if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sayNone(choices().find((x) => x.id === cur));
  }
});
// 0–9 put an option on the stage (0 = the render), while the panel is open
document.addEventListener("keydown", (e) => {
  if (!open || e.target.closest?.("textarea, input:not([type=range])") || e.metaKey || e.ctrlKey || e.altKey || !/^[0-9]$/.test(e.key)) return;
  const c = choices().find((x) => x.id === cur);
  if (!c) return;
  const k = +e.key;
  if (k === 0) show("");
  else if (c.options[k - 1]) show(c.options[k - 1].id);
  e.preventDefault();
});
// the timeline's Choices row: that one, here
document.addEventListener("choice:select", (e) => {
  document.dispatchEvent(new CustomEvent("panel:open", { detail: "sec-asks" }));
  select(e.detail);
  el.querySelector(`[data-choice="${CSS.escape(e.detail)}"]`)?.scrollIntoView({ block: "nearest" });
});

export const decide = {
  render,
  // the round's panel folded or opened: folding it puts the render back on the stage
  async panel(on) {
    if (!on && open) {
      open = false;
      stopAt = null;
      await show("");
      layer.hidden = true;
    }
    render();
  },
  get showing() {
    return showing;
  },
};
