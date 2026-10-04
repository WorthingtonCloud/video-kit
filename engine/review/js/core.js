// Review Studio's page, the core every panel shares. The page reads the snapshot (review/state.json, through the server)
// and writes only the human's events (notes, sends, answers, decisions); the agent's answers arrive in the same snapshot,
// so main.js polls it. Panels import this and register with app.parts; nothing here imports a panel.
export const $ = (s) => document.querySelector(s);
export const app = { state: null, ctx: null, raw: null, cut: null, maps: null, video: $("#video"), parts: [] };
export const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// the round's maps: the timeline (when), the element map (what is where), the findings, the words, the sound cues.
// Any of them can be missing (an old render, no mix yet); the panels draw what there is.
async function loadMaps(R) {
  const get = async (u) => (u ? fetch(u, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null) : null);
  const [timeline, elements, findings, words, cues, qa] = await Promise.all([R.timeline, R.elements, R.findings, R.words, R.cues, R.qa].map(get));
  app.maps = { timeline, elements, findings, words, cues, qa, exact: R.exact };
  app.parts.forEach((p) => p.maps?.());
}

// ── the server ──
// The human's feedback waits in the page (held) until Approve & send: these kinds, while a round is open. Each one lands
// with a message that says what it was, in plain words, and an Undo.
export const HELD = new Set(["note.added", "note.edited", "note.withdrawn", "note.answered", "note.accepted", "note.reopened",
  "finding.confirmed", "finding.dismissed", "choice.made", "mix.saved", "version.approved", "lesson.decided", "scene.done", "scene.reopened", "round.nonotes"]);
export async function post(events, { quiet = false } = {}) {
  const R = round(),
    open = R && R.status !== "closed",
    evs = events.map((e) => (open && HELD.has(e.type) ? { ...e, held: true } : e));
  const r = await fetch("api/events", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ events: evs }) });
  const j = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) {
    toast(j.error || `HTTP ${r.status}`, true);
    throw new Error(j.error);
  }
  take(j);
  const seqs = (j.seqs || []).filter((q, i) => evs[i]?.held);
  if (seqs.length && !quiet) {
    const words = app.state.steps.filter((s) => s.seqs.some((q) => seqs.includes(q))).map((s) => s.text);
    toast(`${words.join(" · ") || "Added"} · waits for your send`, false, () => undo(seqs));
  }
  return j;
}
// take back held feedback (its lines in the log); what's already gone (sent, or undone along with something) is skipped
export async function undo(seqs) {
  const live = new Set(app.state?.pending || []),
    of = seqs.filter((q) => live.has(q));
  if (!of.length) return toast("Nothing to undo: it was already sent or undone.");
  await post(of.map((q) => ({ type: "undo", of: q })), { quiet: true });
  toast("Undone.");
}
// the steps waiting to be sent, oldest first (the Review list)
export const pending = () => (app.state?.steps || []).filter((s) => s.pending);
export async function load() {
  const r = await fetch("api/state", { cache: "no-store" });
  take(await r.json());
}
// what in the context can change while the page is open (a new mix, a new take to listen to, Claude starting or
// stopping its watch): any of these redraws, like a new event does
const ctxKey = (c) => JSON.stringify([c?.mixer?.tag, c?.mixer?.video, c?.listen, c?.waiting, c?.round?.video, c?.round?.cuts?.length, c?.versions?.length]);
function take(j) {
  const changed = !app.state || j.state.events !== app.state.events || ctxKey(j.context) !== ctxKey(app.raw);
  app.state = j.state;
  app.raw = j.context;
  app.ctx = onScreen(j.context);
  if (changed) render();
}

// ── both shapes in one round (vs review open finds the other render of the version): the page shows one at a time.
// ctx.round is the one on screen (its video, maps, composition), round() says its cut and video, so every note, finding
// decision and approval the page makes is about the shape the human is looking at. Each shape gets its own feedback.
export const cuts = () => app.raw?.round?.cuts || null;
function onScreen(ctx) {
  const cs = ctx?.round?.cuts,
    R = app.state?.rounds.at(-1);
  if (!cs?.length) {
    app.cut = null;
    return ctx;
  }
  if (!cs.some((c) => c.cut === app.cut)) {
    let kept = null;
    try {
      kept = localStorage.getItem(`review.cut.${R?.n}`);
    } catch {}
    app.cut = cs.some((c) => c.cut === kept) ? kept : ctx.round.cut;
  }
  return { ...ctx, round: { ...ctx.round, ...cs.find((c) => c.cut === app.cut) } };
}
// switch the shape on screen: the same moment, the other picture, still playing if it was (a reviewer, Oct 4, 2026: flipping
// back and forth stopped the video each time, and the button still said pause)
export function setCut(cut, t = app.video.currentTime, play = !app.video.paused && !app.video.ended) {
  if (!cuts()?.some((c) => c.cut === cut) || cut === app.cut) return false;
  app.cut = cut;
  try {
    localStorage.setItem(`review.cut.${round()?.n}`, cut);
  } catch {}
  app.ctx = onScreen(app.raw);
  const v = app.video;
  v.addEventListener(
    "loadedmetadata",
    () => {
      v.currentTime = Math.min(t, v.duration || t);
      if (play) v.play().catch(() => {});
    },
    { once: true },
  );
  render();
  return true;
}
// the other shape's findings carry its name (vs review: "16x9:f-…"), so the same check on both is two answers
export const cutPrefix = () => (cuts() && app.cut !== app.state?.rounds.at(-1)?.cut ? `${app.cut}:` : "");
// is this note about the shape on screen (a round with one shape: always)
export const onCut = (n) => !cuts() || (n.cut || app.state?.rounds[n.round - 1]?.cut) === app.cut;
export const shapeName = (c) => (c === "16x9" ? "widescreen" : "vertical");
// a round as one shape: its cut, video and size (a round with both shapes keeps each in cuts)
export const asCut = (R, cut) => {
  const c = cut && R?.cuts?.find((x) => x.cut === cut);
  return c ? { ...R, cut: c.cut, video: c.video, size: c.size } : R;
};
// a project path's address on this server (review_server.url): a reel's widescreen cut lives in the project beside this
// one, served as /@<that project>/out/…
export const href = (p) => (p.startsWith("../") ? `/@${p.slice(3)}` : `/${p.replace(/^\.\//, "")}`);

let tt;
// a message under the picture; with undo, it carries an Undo button for as long as it shows
export function toast(msg, err = false, undo = null) {
  const t = $("#toast"),
    u = $("#toast-u");
  $("#toast-t").textContent = msg;
  t.classList.toggle("err", err);
  u.hidden = !undo;
  u.onclick = undo ? () => (t.classList.remove("on"), undo()) : null;
  t.classList.add("on");
  clearTimeout(tt);
  tt = setTimeout(() => t.classList.remove("on"), err ? 6000 : undo ? 7000 : 2600);
}

export const fmt = (t) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${(t % 60).toFixed(2).padStart(5, "0")}`;
export const round = () => {
  const R = app.state?.rounds.at(-1);
  const c = R?.cuts?.find((x) => x.cut === app.cut);
  return c ? { ...R, cut: c.cut, video: c.video, size: c.size } : R || null;
};
// the notes in play: this round's, plus earlier ones still open (a question, a resolution to accept, a reopened note).
// The Notes panel lists them, the timeline pins them, N jumps between them.
export function liveNotes() {
  const R = round(),
    live = new Set(["sent", "question", "resolved", "wontdo", "reopened"]);
  return Object.values(app.state?.notes || {}).filter((n) => n.status !== "withdrawn" && ((R && n.round === R.n) || live.has(n.status)));
}

// ── the frame around the video ──
export function render() {
  const R = round(),
    C = app.ctx;
  $("#proj").textContent = C.project;
  document.title = `${C.project} · Review Studio`;
  $("#dsub").textContent = R ? `Round ${R.n} · v${R.version} · ${shapeName(R.cut)}${cuts() ? " (both shapes in this round)" : ""}` : "no round open";
  const sh = $("#shapes"),
    cs = cuts();
  sh.hidden = !cs;
  if (cs) {
    const count = (c) => liveNotes().filter((n) => (n.cut || R.cut) === c && ["draft", "sent", "reopened"].includes(n.status)).length || "";
    sh.innerHTML = cs
      .map((c) => `<button data-cut="${c.cut}" aria-pressed="${c.cut === app.cut}" title="Watch the ${shapeName(c.cut)} cut: notes you add are about it"><span class="ic ${c.cut === "16x9" ? "w" : "v"}"></span>${c.cut === "16x9" ? "Wide" : "Vertical"}<b>${count(c.cut)}</b></button>`)
      .join("");
  }
  if (C.round && app.video.dataset.src !== C.round.video) {
    app.video.dataset.src = C.round.video;
    app.video.src = C.round.video;
    if (C.round.size) setAspect(C.round.size[0], C.round.size[1]);
    loadMaps(C.round);
  } else if (!C.round && C.mixer && !app.video.dataset.src) {
    // no round yet (vs mixer straight after vs mix): the picture is the video the stems were mixed against
    app.video.dataset.src = C.mixer.video;
    app.video.src = C.mixer.video;
    app.video.addEventListener("loadedmetadata", () => setAspect(app.video.videoWidth, app.video.videoHeight), { once: true });
  }
  app.parts.forEach((p) => p.render?.());
}

// The stage is exactly the frame's shape at the biggest size the room allows (the overlay and every click are fractions
// of it, so it must never stretch): worked out whenever the room or the shape changes.
let AR = 9 / 16;
export function setAspect(w, h) {
  if (w && h) AR = w / h;
  fit();
}
export function fit() {
  const pl = $("#player"),
    st = $("#stage"),
    cs = getComputedStyle(pl);
  const W = pl.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
    H = pl.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  let h = Math.max(0, H),
    w = h * AR;
  if (w > W) {
    w = Math.max(0, W);
    h = w / AR;
  }
  st.style.width = `${Math.floor(w)}px`;
  st.style.height = `${Math.floor(h)}px`;
  document.dispatchEvent(new Event("stage:fit"));
}
new ResizeObserver(() => fit()).observe($("#player"));
