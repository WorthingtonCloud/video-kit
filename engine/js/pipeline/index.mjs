#!/usr/bin/env node
// Build the video from reel.json as ONE HyperFrames composition (build/comp/index.html), check it, render it.
// Nothing here spends money. Re-run end to end any time; footage and music are only re-cut when their inputs change.
//
//   vs build                       prepare, lint, check the safe zone, render out/<name>-v<N>.mp4 + cover + cuts
//   vs build --storyboard          prepare and lint, then snapshot hero frames to build/qa/storyboard/ (no render):
//                                  LOOK at it before paying the render's time, fix, repeat
//   vs build --no-render           prepare and check only
//
// Segment shape (reel.json → "segments"):
//   {"name": "s02_hub", "beats": 12, "in": "whip", "source": {"scene": "hub"}, "titles": [["t_layers", 0, 6], ["t_plugged", 6, "end"]]}
// Length: "beats": n (on the grid) · "secs": x · "to_hit": true (runs until the music's first big hit).
// Title times use the segment's own unit ("end" = the segment's end).
// "in" (how this segment arrives):
//   whip (default, up into a blur) · whipx (sideways) · zoom (dolly through the outgoing card) · dot (collapses into
//   its accent point, which flies to center and hits) · flash · fade (into footage) · cut
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
// The steps, in order: context.mjs (the reel and the helpers) → timing → checks → media → css → compose → the HyperFrames
// lint → the safe zone → collage frames → storyboard or render.
import { STORY, NORENDER, hf } from "./context.mjs";
import { checkTitles, checkNever } from "./checks.mjs";
import { prepareMedia } from "./media.mjs";
import { css } from "./css.mjs";
import { compose } from "./compose.mjs";
import { checkSafeZone } from "./safezone.mjs";
import { snapTiles, storyboard, render } from "./render.mjs";

checkTitles();
checkNever();
const m = prepareMedia();
compose({ segHTML: m.segHTML, media: m.media, CSS: css(m) });
hf(["lint"]);
await checkSafeZone();
snapTiles(m.snapTimes);
if (STORY) storyboard();
if (!NORENDER) render();
