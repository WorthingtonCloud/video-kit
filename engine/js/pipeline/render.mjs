// Build step 7, pictures: frames of this reel for a collage grid ("@t"), the storyboard (hero frames, no render), and the
// render itself plus the cover still.
import fs from "node:fs";
import path from "node:path";
import { QA, TIMELINE, CONTRACTS } from "../lib/paths.mjs";
import { archive } from "../lib/archive.mjs";
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
  // Two frames drawn per frame shown, each pair averaged: a light motion blur. Small text and thin lines in a slowly
  // turning panel get redrawn a little sharper or softer at each angle, so they flickered on alternate frames (the
  // shimmer qa.py measures: Socrates 95-98 s went from 111-162 flickering patches a second to 18, the text as sharp).
  // Costs about twice the render time. reel.json "blend": 1 turns it off for one video.
  const blend = R.blend ?? CONTRACTS.render.blend;
  if (blend > 1) {
    const raw = path.resolve(OUT.replace(".mp4", ".frames.mp4"));
    hf(["render", "-o", raw, "--fps", String(FPS * blend), "--video-frame-format", "png", "--quiet"]);
    ff("-i", raw, "-vf", `tmix=frames=${blend}:weights=${Array(blend).fill(1).join(" ")},framestep=${blend}`, "-r", String(FPS),
       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "copy", "-movflags", "+faststart", path.resolve(OUT));
    fs.rmSync(raw, { force: true });
  } else hf(["render", "-o", path.resolve(OUT), "--fps", String(FPS), "--video-frame-format", "png", "--quiet"]);
  // the cover: a still for the platform's thumbnail upload (LinkedIn lets you pick one; most chat apps don't)
  ff("-ss", String(R.cover?.at ?? 2.0), "-i", OUT, "-frames:v", "1", "-q:v", "2", OUT.replace(".mp4", "-cover.jpg"));
  // the version keeps its own copy of the timing it was rendered with (qa.py reads it; the build's copy moves on)
  fs.copyFileSync(TIMELINE, OUT.replace(".mp4", ".timeline.json"));
  // ...and its maps, so a review round, Compare and its outlines still work after build/ moves on
  const a = archive(OUT);
  console.log(`${END.toFixed(2)}s → ${OUT}  (+ cover, + timeline.json for qa.py, + ${a.home}/: ${a.kept.join(", ")})`);
  if (a.skipped.length) console.log(`  ⚠️  ${a.skipped.join(" and ")} weren't made from this composition (rendered --anyway?): not kept`);
}
