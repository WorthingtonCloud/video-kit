#!/usr/bin/env node
// Build the video from reel.json as ONE HyperFrames composition (build/comp/index.html), check it, render it.
// Nothing here spends money. Re-run end to end any time; footage and music are only re-cut when their inputs change.
//
//   vs build                       prepare, lint, check the safe zone, render drafts/vN/<video>-<shape>-vN.mp4 + cover +
//                                  its data/<shape>/ (timing, maps, sources), once vs inspect has passed THIS composition (gate.mjs);
//                                  then vs qa on the new cut. Run it in the background: it prints nothing until it's
//                                  done, then the QA report and one "✓ vs build finished" line. Don't check on it.
//   vs build --no-qa               render only
//   vs build --anyway              render past vs inspect's open errors, and say so
//   vs build --storyboard          prepare and lint, then snapshot hero frames to build/qa/storyboard/ (no render):
//                                  LOOK at it before paying the render's time, fix, repeat
//   vs build --no-render           prepare and check only
// The cheap-first ladder: vs build --no-render → vs inspect → vs build --storyboard (or vs snap) → vs build.
//
// Segment shape (reel.json → "segments"):
//   {"name": "s02_hub", "beats": 12, "in": "whip", "source": {"scene": "hub"}, "titles": [["t_layers", 0, 6], ["t_plugged", 6, "end"]]}
// Length: "beats": n (on the grid) · "secs": x · "to_hit": true (runs until the music's first big hit).
// Title times use the segment's own unit ("end" = the segment's end).
// "in" (how this segment arrives):
//   whip (default, up into a blur) · whipx (sideways) · zoom (dolly through the outgoing card) · dot (collapses into
//   its accent point, which flies to center and hits) · flash · fade (into footage) · dissolve (a slow cross-dissolve, no blur, no move: source.dissolve = secs, 1.4) · cut
//   rise (a page swings up like a raised phone) · swing (carousel: both pages travel, curving away) · depth (old page
//   flies past the camera, new one rushes in from far) · flip (turned over like a card) · drop (falls in from above)
//   over (a card lands ON the previous segment, which dims under the first line and, if it's a grid, collapses into
//   the red point on the second line's beat)
// Segment extras: "fx": {"dust": {"x": [0.3, 0.78], "y": [0.24, 0.62], "n": 34}} motes hanging in the light of a clip.
// Top level: "punches": [42.99] extra camera push-ins on drum hits (transitions and emphasis add their own).
//   "never": ["https://site/"] pages that must never be on screen (the one that says the closing line): a shot that
//   records one stops the build, and collage.mjs refuses a tile whose "from" is one.
// Checks it runs before rendering (each one a note a reviewer once had to give): words in the phone safe zone, emphasis
// that has no word to land on, a check mark on its word, a marker split by a line break, a font that never loaded,
// grid tiles that are frames of this reel or the same picture twice, a "never" page. qa.py adds black holes near cuts.
// Sources:
//   {"scene": "chat" | "hub" | "sources" | "endcard"}   drawn in code (reel.js), words from reel.json → "scenes"
//   {"shot": "home", "inset": 0.78}                      a real page in a framed panel that floats in 3D with a glare that
//                                                        follows its tilt (reel.json → "shots": a url that record.mjs
//                                                        scrolls, or a "video" / "dir" of frames you recorded)
//   {"clip": "clips/x.mp4", "ss": 0, "speed": 1}         a video clip (generated, or your own footage)
//   {"still": "stills/x.jpg"}                            a still with a slow push-in ("push" on the segment sets how far)
//   {"card": "t_title", "at": [0, 1, 2], "style": "flap" | "slam", "out": "shatter"}
//                                                        a full-frame title card; "at" = beat each line arrives on; flap =
//                                                        departures-board flip, slam = lands from over the camera with a
//                                                        punch; shatter = every letter flies apart at the cut
//   {"grid": ["stills/collage/t01.jpg", …], "cols": 4}
//                                                        the collage: tiles fly in from every side and land as a 3D wall
//                                                        the camera sweeps over, then a red playhead runs them in order.
//                                                        Build the tiles with collage.mjs from the thing's OWN work (real
//                                                        postings + real visuals, all different); fill every row. ("@t" =
//                                                        a frame of this reel still works, but a wall of the reel's own
//                                                        scenes reads as repetition — review note, Sep 29.)
// Titles (reel.json → "titles"): "spark": true on a stat fires it out of the scene's anchor; "em" = one emphasis on the
// key word, on the beat ("b" beats after the title's slot): {"fx": "pulse" | "box" | "check" | "beats" | "ruler",
// "word": "checked" (default: the accent words), "b": 1, "snap": 3 (ruler: the beat its marker lands)}.
// The steps, in order: vs check (the contracts, check.mjs) → context.mjs (the reel and the helpers) → timing → checks →
// media → css → compose (writes build/comp/index.html and build/timeline.json, the one timing every later step reads) →
// the HyperFrames lint → the safe zone → collage frames → storyboard, or the render gate (gate.mjs) and the render.
import { lifecycle } from "../lib/lifecycle.mjs";
import { check } from "../check.mjs";

// a finished video, or the second shape before the first is approved: refused before anything else runs
if (!process.argv.slice(2).some((a) => a === "--no-render" || a === "--storyboard")) lifecycle();

// the contracts first, before any step loads (they read reel.json as they load): a misspelled scene used to fail inside
// the browser mid-build, a wrong path deep in ffmpeg
const chk = check({ quiet: true });
chk.warnings.forEach((w) => console.log(`  ⚠️  ${w}`));
if (chk.errors.length) {
  console.error(`⛔ vs check found ${chk.errors.length} problem(s):\n${chk.errors.map((e) => `   ✗ ${e}`).join("\n")}`);
  process.exit(1);
}
const { STORY, NORENDER, hf } = await import("./context.mjs");
const { gate } = await import("./gate.mjs");
const { checkNever } = await import("./checks.mjs");
const { prepareMedia } = await import("./media.mjs");
const { css } = await import("./css.mjs");
const { compose } = await import("./compose.mjs");
const { checkSafeZone } = await import("./safezone.mjs");
const { snapTiles, storyboard, render } = await import("./render.mjs");

checkNever();
const m = prepareMedia();
compose({ segHTML: m.segHTML, media: m.media, CSS: css(m) });
hf(["lint"]);
await checkSafeZone();
snapTiles(m.snapTimes);
if (STORY) storyboard();
if (!NORENDER) {
  gate();
  render();
}
