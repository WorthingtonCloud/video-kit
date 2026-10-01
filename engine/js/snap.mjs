// Stills of the composition straight from the timeline (no render), to LOOK at before paying for one:
//   vs snap 44 59.8 …                     those moments → build/qa/snap/
//   vs snap --every 1 --out <dir>         one frame a second (at x.5 s) into <dir>: a reference set to compare against
//                                         after a change (vs compare <dir> <other dir>)
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { launch, loadReel } from "./lib/browser.mjs";
import { COMP, QA } from "./lib/paths.mjs";

const args = process.argv.slice(2),
  opt = (k) => (args.includes(k) ? args.splice(args.indexOf(k), 2)[1] : null);
const every = opt("--every"),
  out = opt("--out") || `${QA}/snap`;
const R = loadReel(),
  [W, H] = R.size;
const b = await launch(),
  p = await b.newPage();
await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await p.goto(pathToFileURL(path.resolve(COMP, "index.html")).href, { waitUntil: "load" });
await p.evaluate(async () => {
  await document.fonts.ready;
  return true;
});
let times = args.map(Number);
if (every) {
  const end = await p.evaluate(() => window.REEL.end);
  times = [];
  for (let t = +every / 2; t < end; t += +every) times.push(+t.toFixed(3));
}
if (!every) fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });
for (const t of times) {
  await p.evaluate((t) => {
    window.__timelines.main.seek(t, false);
  }, t);
  await p.screenshot({ path: path.join(out, `${t.toFixed(2).padStart(7, "0")}.png`) });
}
await b.close();
console.log(`${out}/ (${times.length})`);
