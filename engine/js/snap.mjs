// Stills of the composition straight from the timeline (no render), to LOOK at before paying for one:
//   vs snap 44 59.8 …                     those moments → build/qa/snap/, and with 4 or more, labeled contact sheets
//                                         (sheet-1.jpg …: each still captioned with its time and segment). Look at the
//                                         sheets; open a single still only to check a detail.
//   vs snap --every 1 --out <dir>         one frame a second (at x.5 s) into <dir>: a reference set to compare against
//                                         after a change (vs compare <dir> <other dir>). No sheets unless --sheet.
//   --sheet / --no-sheet                  force the contact sheets on or off
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { launch } from "./lib/browser.mjs";
import { COMP, QA, readTimeline } from "./lib/paths.mjs";

const args = process.argv.slice(2),
  opt = (k) => (args.includes(k) ? args.splice(args.indexOf(k), 2)[1] : null),
  flag = (k) => (args.includes(k) ? (args.splice(args.indexOf(k), 1), true) : false);
const every = opt("--every"),
  out = opt("--out") || `${QA}/snap`,
  forceSheet = flag("--sheet"),
  noSheet = flag("--no-sheet");
const TL = readTimeline(), // the build's timing and size: the composition's own, whatever reel.json says now
  [W, H] = TL.size;
const b = await launch(),
  p = await b.newPage();
await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await p.goto(pathToFileURL(path.resolve(COMP, "index.html")).href, { waitUntil: "load" });
await p.evaluate(async () => {
  await Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 10000))]); // never forever (a rare stall)
  return true;
});
let times = args.map(Number);
if (every) {
  const end = TL.end;
  times = [];
  for (let t = +every / 2; t < end; t += +every) times.push(+t.toFixed(3));
}
if (!every) fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
const segAt = (t) => (TL.segments.find((s) => t >= s.t0 && t < s.t1) || TL.segments[TL.segments.length - 1])?.name || "";
// The page's timeline moves everything but its <video>s: HyperFrames sets those only while rendering, so a seek left
// a shot panel on its first frame, a black one, or a stale one, and the checker reported five false problems in the
// floating recordings (video-kit-fusion v1, Oct 5, 2026). Each video on screen at t is put at its own time
// (data-start, plus data-playback-start / -rate as HyperFrames reads them) and held until it has seeked there and
// shown that frame; one that can't be confirmed in time comes back by name, so its panel is not trusted.
const VIDEO_WAIT_MS = 5000;
async function settleVideos(t) {
  return p.evaluate(
    async (t, ms) => {
      const within = (pr, ms) => Promise.race([pr, new Promise((r) => setTimeout(() => r(false), ms))]);
      const once = (v, ev) => new Promise((r) => v.addEventListener(ev, () => r(true), { once: true }));
      const num = (v, k, d) => (Number.isFinite(parseFloat(v.getAttribute(k))) ? parseFloat(v.getAttribute(k)) : d);
      const bad = [];
      await Promise.all(
        [...document.querySelectorAll("video")].map(async (v, k) => {
          const s = num(v, "data-start", 0),
            d = num(v, "data-duration", Infinity);
          if (t < s || t >= s + d || !v.getClientRects().length) return; // not on screen at t
          const name = { id: v.id || `video ${k + 1}`, src: v.getAttribute("src") || "" };
          v.pause();
          const failed = new Promise((r) => v.addEventListener("error", () => r(false), { once: true }));
          if (v.readyState < 1 && (v.error || !(await within(Promise.race([once(v, "loadedmetadata"), failed]), ms))))
            return bad.push({ ...name, why: v.error ? `won't load (error ${v.error.code})` : "never loaded" });
          let want = (t - s) * num(v, "data-playback-rate", 1) + num(v, "data-playback-start", num(v, "data-media-start", 0));
          if (Number.isFinite(v.duration)) want = Math.min(Math.max(0, want), Math.max(0, v.duration - 0.001));
          const seeked = once(v, "seeked"),
            shown = "requestVideoFrameCallback" in v ? new Promise((r) => v.requestVideoFrameCallback(() => r(true))) : null;
          v.currentTime = want;
          if (!(await within(seeked, ms))) return bad.push({ ...name, why: `never finished seeking to ${want.toFixed(2)}s` });
          // seeked = the frame is decoded; the frame callback = it reached the picture. Off-screen ticks can be slow.
          if (shown && !(await within(shown, ms)) && v.readyState < 2)
            return bad.push({ ...name, why: `seeked to ${want.toFixed(2)}s but no frame came` });
          if (Math.abs(v.currentTime - want) > 0.05) bad.push({ ...name, why: `sits at ${v.currentTime.toFixed(2)}s, not ${want.toFixed(2)}s` });
        }),
      );
      return bad;
    },
    t,
    VIDEO_WAIT_MS,
  );
}

const shots = [],
  unsure = [];
for (const t of times) {
  await p.evaluate((t) => {
    window.__timelines.main.seek(t, false);
  }, t);
  const bad = await settleVideos(t);
  const file = path.join(out, `${t.toFixed(2).padStart(7, "0")}.png`);
  await p.screenshot({ path: file });
  shots.push({ t, file, unsure: bad.length > 0 });
  // v<i> is segment i's footage (pipeline/media.mjs); it starts a beat early, so the time alone can name the one before
  const segOf = (b) => TL.segments[+(/^v(\d+)$/.exec(b.id) || [])[1]]?.name || segAt(t);
  for (const b of bad) unsure.push(`${t.toFixed(2)}s · ${segOf(b)} · ${b.id} (${b.src}): ${b.why}`);
}
console.log(`${out}/ (${times.length})`);
if (unsure.length) {
  console.log(`⚠ ${unsure.length} video panel${unsure.length > 1 ? "s" : ""} not confirmed: what they show in these stills is NOT trustworthy (judge them from a render)`);
  for (const u of unsure) console.log(`  ⚠ ${u}`);
}

// Contact sheets: every session used to tile the stills by hand with a throwaway script (three tries, once). A sheet
// of eight costs about what one full-size still does to look at.
if (forceSheet || (!every && !noSheet && shots.length >= 4)) {
  const land = W > H,
    cols = land ? 3 : 4,
    rows = land ? 3 : 2,
    cw = land ? 480 : 270,
    ch = Math.round((cw * H) / W),
    per = cols * rows;
  const sp = await b.newPage();
  await sp.setViewport({ width: cols * (cw + 6) + 6, height: 400, deviceScaleFactor: 1 });
  for (let i = 0; i * per < shots.length; i++) {
    const part = shots.slice(i * per, (i + 1) * per),
      cells = part
        .map(
          (s) =>
            `<figure><img src="${pathToFileURL(path.resolve(s.file)).href}"><figcaption><b>${s.t.toFixed(2)}s</b> ${s.unsure ? "<b>⚠ panel unconfirmed</b> " : ""}${segAt(s.t)}</figcaption></figure>`,
        )
        .join("");
    // a page on disk, not setContent: about:blank may not load file:// pictures
    const html = path.join(out, `sheet-${i + 1}.html`);
    fs.writeFileSync(
      html,
      `<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#fff;font:600 15px/1.2 -apple-system,Helvetica,sans-serif}
      main{display:grid;grid-template-columns:repeat(${cols},${cw}px);gap:6px;padding:6px;width:max-content}
      figure{margin:0}img{display:block;width:${cw}px;height:${ch}px;object-fit:cover;outline:1px solid #bbb}
      figcaption{padding:3px 2px 0;color:#222;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}b{color:#c0281b}</style>
      <main>${cells}</main>`,
    );
    await sp.goto(pathToFileURL(path.resolve(html)).href, { waitUntil: "load" });
    const box = await (await sp.$("main")).boundingBox();
    const file = path.join(out, `sheet-${i + 1}.jpg`);
    await sp.screenshot({ path: file, type: "jpeg", quality: 82, clip: box });
    fs.rmSync(html);
    console.log(`${file}  ${part[0].t.toFixed(2)}–${part[part.length - 1].t.toFixed(2)}s (${part.length})`);
  }
}
await b.close();
