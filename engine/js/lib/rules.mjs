// The human's standing rules, from Review Studio's diary snapshot (review/state.json, which vs review rewrites after
// every write), checked by vs inspect beside its own checks:
//   keep-clear  a zone a note drew ("nothing goes here"): in the note's scene, on the cut it was drawn on, nothing but
//               what it was drawn over (and what that holds, and what holds it) may enter it
//   done        a scene the human marked done (scene.done): its frames are locked to the version it was approved in.
//               That version's composition is kept beside its render (out/<name>-vN.review/comp.html); both are snapped
//               at the same moments and compared. A snapshot of one composition is identical every time (measured: 0 of
//               129,600 pixels), so any difference is a real change; the render itself can't be the reference (its
//               grain and encoding differ from a snapshot by up to 234 levels).
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";
import { step } from "./browser.mjs";

const LIVE = new Set(["sent", "question", "resolved", "accepted", "reopened"]); // a draft isn't sent; withdrawn is gone

export function readRules(dir = ".") {
  const f = path.join(dir, "review/state.json");
  if (!fs.existsSync(f)) return { keep: [], done: [] };
  const S = JSON.parse(fs.readFileSync(f, "utf8"));
  const keep = [];
  for (const n of Object.values(S.notes || {})) {
    if (!LIVE.has(n.status) || n.resolution?.outcome === "wontdo") continue; // a won't-do the human accepted isn't a rule
    const zs = [n.mark, ...(n.also || [])].filter((m) => m?.type === "keep-clear" && m.box);
    // what the zone protects: what was mostly inside it when drawn (keeps; older notes: everything it touched), never
    // the note's own target, which is usually the thing that shouldn't be there
    const tgt = n.target?.el;
    zs.forEach((z, i) =>
      keep.push({ id: `${n.id}${zs.length > 1 ? "-" + (i + 1) : ""}`, note: n.id, segment: n.segment, cut: n.cut, box: z.box,
                  over: (z.keeps || z.over || []).filter((a) => a !== tgt) }),
    );
  }
  const done = Object.entries(S.done || {}).map(([segment, d]) => ({ segment, ...d }));
  return { keep, done };
}

const cutOf = (W, H) => (W > H ? "16x9" : "9x16");
const area = (b) => Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]);
const inter = (a, b) => area([Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.min(a[2], b[2]), Math.min(a[3], b[3])]);
const holds = (a, b, m = 0.002) => a[0] <= b[0] + m && a[1] <= b[1] + m && a[2] >= b[2] - m && a[3] >= b[3] - m;

// keep-clear, from the scrub's own map (no extra browser work): META[i] = {addr, up}, seenAt = [[t, [[i, x0, y0, x1, y1]]]]
export function keepClear({ rules, TL, META, seenAt, W, H, near, MIN, STEP }) {
  const out = [],
    warn = [],
    idx = new Map(META.map((m, i) => [m.addr, i])),
    ups = (i) => {
      const a = [];
      for (let u = META[i].up; u != null && !a.includes(u); u = META[idx.get(u)]?.up ?? null) a.push(u);
      return a;
    };
  for (const z of rules.keep) {
    if (z.cut && z.cut !== cutOf(W, H)) continue; // a mark stays with the cut it was drawn on
    const S = TL.segments.find((s) => s.name === z.segment);
    if (!S) {
      warn.push(`keep-clear from ${z.note}: its scene ${z.segment} isn't in this build (renamed?), so it isn't checked`);
      continue;
    }
    const gone = z.over.filter((a) => !idx.has(a));
    if (gone.length) warn.push(`keep-clear from ${z.note}: ${gone.join(", ")} isn't in this build: it can now be in the zone`);
    // what may be there: what it was drawn over, what holds that, and what that holds
    const ok = new Set(z.over);
    for (const a of z.over) if (idx.has(a)) ups(idx.get(a)).forEach((u) => ok.add(u));
    META.forEach((m, i) => ups(i).some((u) => z.over.includes(u)) && ok.add(m.addr));
    const spans = new Map();
    for (const [t, els] of seenAt) {
      if (t < S.t0 || t >= S.t1 || near(t)) continue;
      const hit = [];
      for (const [i, ...b] of els) {
        const a = META[i].addr;
        if (ok.has(a) || a.startsWith("frame/") || area(b) > 0.6 || holds(b, z.box)) continue; // backdrops and holders
        const x = inter(b, z.box);
        if (x > 0.25 * area(b) || x > 0.05 * area(z.box)) hit.push([i, b]);
      }
      // the smallest thing wins: a group is flagged only when nothing it holds is
      const ids = new Set(hit.map(([i]) => META[i].addr));
      for (const [i, b] of hit) {
        if (hit.some(([j]) => j !== i && ups(j).includes(META[i].addr) && ids.has(META[j].addr))) continue;
        const L = spans.get(i) || [];
        const last = L.at(-1);
        if (last && t - last.t1 <= STEP * 2.1) (last.t1 = t), last.boxes.push([t, b]);
        else L.push({ t0: t, t1: t, boxes: [[t, b]] });
        spans.set(i, L);
      }
    }
    for (const [i, L] of spans)
      for (const s of L) {
        if (s.t1 - s.t0 + STEP < MIN) continue;
        const mid = (s.t0 + s.t1) / 2,
          [at, b] = s.boxes.reduce((p, q) => (Math.abs(q[0] - mid) < Math.abs(p[0] - mid) ? q : p));
        out.push({
          check: "keep-clear",
          elements: [META[i].addr],
          text: `in the zone ${z.note} asked to keep clear${z.over.length ? ` (around ${z.over.map((a) => a.split("/").pop()).join(", ")})` : ""}`,
          detail: z.id,
          t0: s.t0,
          t1: s.t1,
          at,
          box: [b[0] * W, b[1] * H, b[2] * W, b[3] * H].map(Math.round),
          box_n: b,
          zone: z.box,
          hint: `you asked for nothing here (${z.note}): move it out of the zone, or ask whether it may stay`,
        });
      }
  }
  return { out, warn };
}

// done scenes: the approved version's composition and this one, snapped at the same moments of the scene, compared at a
// quarter size. Any pixel more than 24 levels apart, in more than 16 places, is a change.
const archiveOf = (video) => video.replace(/-(take\d+|sfx|mixed)\.mp4$/, ".mp4").replace(/\.mp4$/, ".review");
export async function lockedScenes({ rules, TL, browser, W, H, COMP, seenAt, META }) {
  const out = [],
    warn = [];
  const todo = rules.done.filter((d) => !d.cut || d.cut === cutOf(W, H));
  if (!todo.length) return { out, warn };
  const w = Math.round(W / 4),
    h = Math.round(H / 4);
  const small = (png) =>
    spawnSync("ffmpeg", ["-v", "error", "-i", "-", "-vf", `scale=${w}:${h}:flags=area`, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], {
      input: png,
      maxBuffer: 1 << 27,
    }).stdout;
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  const snaps = async (file, times, label) => {
    await step(`inspect: open ${label}`, () => page.goto(pathToFileURL(path.resolve(COMP, file)).href, { waitUntil: "load" }));
    await step(`inspect: wait for ${label}'s fonts`, () =>
      page.evaluate(async () => {
        await Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 10000))]);
        return true;
      }),
    );
    const got = [];
    for (const t of times) {
      await step(`inspect: ${label} at ${t.toFixed(2)}s`, () =>
        page.evaluate((t) => {
          window.__timelines.main.seek(t, false);
        }, t),
      );
      got.push(small(await step(`inspect: snap ${label} at ${t.toFixed(2)}s`, () => page.screenshot({ type: "png" }))));
    }
    return got;
  };
  for (const d of todo) {
    const home = archiveOf(d.video || ""),
      vtl = fs.existsSync(`${home}/timeline.json`) ? JSON.parse(fs.readFileSync(`${home}/timeline.json`, "utf8")) : null;
    let html = fs.existsSync(`${home}/comp.html`) ? `${home}/comp.html` : null;
    if (!html && vtl && vtl.fingerprint === TL.fingerprint) html = path.join(COMP, "index.html"); // the build hasn't moved on
    const A = vtl?.segments.find((s) => s.name === d.segment),
      B = TL.segments.find((s) => s.name === d.segment);
    if (!html || !A) {
      warn.push(`${d.segment} is marked done in v${d.version}, but that version's composition wasn't kept: it can't be checked`);
      continue;
    }
    const base = { check: "done-changed", severity: "error", elements: [], detail: `${d.segment}, done in v${d.version}` };
    if (!B) {
      out.push({ ...base, check: "done-gone", text: `${d.segment} is gone from the build`, t0: 0, t1: 0, at: 0,
        hint: `the human marked ${d.segment} done in v${d.version}: put it back, or ask them to reopen it` });
      continue;
    }
    const la = A.t1 - A.t0,
      lb = B.t1 - B.t0,
      fps = TL.fps || 30;
    if (Math.abs(la - lb) > 1.01 / fps)
      out.push({ ...base, text: `${d.segment}'s length changed: ${la.toFixed(2)}s → ${lb.toFixed(2)}s`, t0: B.t0, t1: B.t1, at: B.t0 + lb / 2,
        hint: `the human marked ${d.segment} done in v${d.version}: keep its length, or ask them to reopen it` });
    // the scene's own moments, clear of the cuts at both ends (a neighbor's transition may change)
    const offs = [];
    for (let o = 0.6; o < Math.min(la, lb) - 0.5; o += 0.5) offs.push(+o.toFixed(3));
    if (!offs.length) offs.push(+(Math.min(la, lb) / 2).toFixed(3));
    const copy = path.join(COMP, `.done-v${d.version}.html`);
    if (html !== path.join(COMP, "index.html")) fs.copyFileSync(html, copy); // beside the build's assets, so its paths resolve
    let old, now;
    try {
      old = await snaps(path.basename(html === path.join(COMP, "index.html") ? html : copy), offs.map((o) => A.t0 + o), `v${d.version}'s ${d.segment}`);
      now = await snaps("index.html", offs.map((o) => B.t0 + o), `this build's ${d.segment}`);
    } finally {
      fs.rmSync(copy, { force: true });
    }
    let worst = null;
    offs.forEach((o, k) => {
      const a = old[k],
        b = now[k];
      let n = 0,
        x0 = w,
        y0 = h,
        x1 = -1,
        y1 = -1;
      for (let i = 0; i < a.length; i += 3) {
        const dd = Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2]));
        if (dd > 24) {
          n++;
          const p = i / 3,
            x = p % w,
            y = Math.floor(p / w);
          x0 = Math.min(x0, x), y0 = Math.min(y0, y), x1 = Math.max(x1, x), y1 = Math.max(y1, y);
        }
      }
      if (n > 16 && (!worst || n > worst.n)) worst = { o, n, box: [x0 / w, y0 / h, (x1 + 1) / w, (y1 + 1) / h] };
    });
    if (!worst) continue;
    const t = +(B.t0 + worst.o).toFixed(2),
      b = worst.box.map((v) => +v.toFixed(4));
    // what's there now, smallest first (from the scrub's map, at the nearest moment)
    const [, els] = seenAt.reduce((p, q) => (Math.abs(q[0] - t) < Math.abs(p[0] - t) ? q : p), [Infinity, []]);
    const there = els
      .filter(([i, ...e]) => (META[i].addr.startsWith(d.segment + "/") || META[i].addr.startsWith("title/")) && inter(e, b) > 0)
      .sort((p, q) => area(p.slice(1)) - area(q.slice(1)))
      .slice(0, 3)
      .map(([i]) => META[i].addr);
    out.push({
      ...base,
      elements: there,
      text: `${d.segment} changed since v${d.version}: ${worst.n} of ${w * h} pixels (a quarter-size frame) at ${t.toFixed(2)}s`,
      t0: B.t0,
      t1: B.t1,
      at: t,
      box: [b[0] * W, b[1] * H, b[2] * W, b[3] * H].map(Math.round),
      box_n: b,
      hint: `the human marked ${d.segment} done in v${d.version}: undo what changed it, or ask them to reopen it`,
    });
  }
  await page.close();
  return { out, warn };
}
