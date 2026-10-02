// Review Studio's page, the core every panel shares. The page reads the snapshot (review/state.json, through the server)
// and writes only the human's events (notes, sends, answers, decisions); the agent's answers arrive in the same snapshot,
// so main.js polls it. Panels import this and register with app.parts; nothing here imports a panel.
export const $ = (s) => document.querySelector(s);
export const app = { state: null, ctx: null, maps: null, video: $("#video"), parts: [] };
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
const ctxKey = (c) => JSON.stringify([c?.mixer?.tag, c?.mixer?.video, c?.listen, c?.waiting, c?.round?.video, c?.versions?.length]);
function take(j) {
  const changed = !app.state || j.state.events !== app.state.events || ctxKey(j.context) !== ctxKey(app.ctx);
  app.state = j.state;
  app.ctx = j.context;
  if (changed) render();
}

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
export const round = () => app.state?.rounds.at(-1) || null;
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
  $("#dsub").textContent = R ? `Round ${R.n} · v${R.version} · ${R.cut === "16x9" ? "widescreen" : "vertical"}` : "no round open";
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
