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
const shots = [];
for (const t of times) {
  await p.evaluate((t) => {
    window.__timelines.main.seek(t, false);
  }, t);
  const file = path.join(out, `${t.toFixed(2).padStart(7, "0")}.png`);
  await p.screenshot({ path: file });
  shots.push({ t, file });
}
console.log(`${out}/ (${times.length})`);

// Contact sheets: every session used to tile the stills by hand with a throwaway script (three tries, once). A sheet
// of eight costs about what one full-size still does to look at.
if (forceSheet || (!every && !noSheet && shots.length >= 4)) {
  const land = W > H,
    cols = land ? 3 : 4,
    rows = land ? 3 : 2,
    cw = land ? 480 : 270,
    ch = Math.round((cw * H) / W),
    per = cols * rows,
    seg = (t) => (TL.segments.find((s) => t >= s.t0 && t < s.t1) || TL.segments[TL.segments.length - 1])?.name || "";
  const sp = await b.newPage();
  await sp.setViewport({ width: cols * (cw + 6) + 6, height: 400, deviceScaleFactor: 1 });
  for (let i = 0; i * per < shots.length; i++) {
    const part = shots.slice(i * per, (i + 1) * per),
      cells = part
        .map(
          (s) =>
            `<figure><img src="${pathToFileURL(path.resolve(s.file)).href}"><figcaption><b>${s.t.toFixed(2)}s</b> ${seg(s.t)}</figcaption></figure>`,
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
