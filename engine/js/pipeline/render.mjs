// Build step 7, pictures: frames of this reel for a collage grid ("@t"), the storyboard (hero frames, no render), and the
// render itself plus the cover still.
import fs from "node:fs";
import path from "node:path";
import { QA } from "../lib/paths.mjs";
import { R, W, LAND, FPS, OUT, COMP, ff, hf, r3, mtime } from "./context.mjs";
import { SEGS, END } from "./timing.mjs";

// frames of this reel for the grid ("@t"): snapshotted from the composition itself, so they match it exactly
export function snapTiles(snapTimes) {
  const stale = snapTimes.filter((s) => mtime(s.out) < mtime("reel.json"));
  if (stale.length) {
    const dir = `${COMP}/.snaps`;
    fs.rmSync(dir, { recursive: true, force: true });
    hf(["snapshot", "--at", stale.map((s) => s.at).join(","), "--no-end", "--describe", "false", "-o", ".snaps"]);
    const pngs = fs
      .readdirSync(dir)
      .filter((f) => f.endsWith(".png"))
      .sort();
    stale.forEach((s, k) => ff("-i", `${dir}/${pngs[k]}`, "-vf", `scale=${Math.round(W / 2)}:-2`, "-q:v", "3", s.out));
  }
}

export function storyboard() {
  // hero frames: the middle of every segment and the moment each title has fully landed
  const at = new Set();
  SEGS.forEach((s) => {
    at.add(r3((s.t0 + s.t1) / 2));
    s.titles.forEach((tt) => at.add(r3(Math.min(tt.t1 - 0.2, tt.t0 + 0.8))));
  });
  const times = [...at].sort((a, b) => a - b),
    out = path.resolve(QA, "storyboard");
  fs.rmSync(out, { recursive: true, force: true });
  hf(["snapshot", "--at", times.join(","), "--no-end", "--describe", "false", "-o", out]);
  // our own sheet: HyperFrames skips its contact sheet on a long list. Cell k (left to right) = times[k].
  ff(
    "-pattern_type",
    "glob",
    "-i",
    `${out}/frame-*.png`,
    "-vf",
    `scale=${LAND ? 360 : 240}:-2,tile=9x${Math.ceil(times.length / 9)}:padding=4:color=white`,
    "-frames:v",
    "1",
    "-q:v",
    "3",
    `${QA}/storyboard.jpg`,
  );
  console.log(
    `storyboard: ${QA}/storyboard.jpg (${times.length} frames, left to right at ${times.map((x) => x.toFixed(1)).join(", ")}s)\n  ← look at every frame before rendering; fix, then run again`,
  );
}

export function render() {
  hf(["render", "-o", path.resolve(OUT), "--fps", String(FPS), "--video-frame-format", "png", "--quiet"]);
  // the cover: a still for the platform's thumbnail upload (LinkedIn lets you pick one; most chat apps don't)
  ff("-ss", String(R.cover?.at ?? 2.0), "-i", OUT, "-frames:v", "1", "-q:v", "2", OUT.replace(".mp4", "-cover.jpg"));
  console.log(`${END.toFixed(2)}s → ${OUT}  (+ cover, + cuts.json for qa.py)`);
}
