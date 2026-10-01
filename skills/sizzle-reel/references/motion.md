# What a reel.json can say

The reel is data: `vs build` turns it into one HyperFrames composition. The worked example is the kit's
`templates/reel/reel.json` (`vs new <slug> --kind reel` copies it).

```
Segment shape (reel.json → "segments"):
  {"name": "s02_hub", "beats": 12, "in": "whip", "source": {"scene": "hub"}, "titles": [["t_layers", 0, 6], ["t_plugged", 6, "end"]]}
Length: "beats": n (on the grid) · "secs": x · "to_hit": true (runs until the music's first big hit).
Title times use the segment's own unit ("end" = the segment's end).
"in" (how this segment arrives):
  whip (default, up into a blur) · whipx (sideways) · zoom (dolly through the outgoing card) · dot (collapses into
  its accent point, which flies to center and hits) · flash · fade (into footage) · cut
  rise (a page swings up like a raised phone) · swing (carousel: both pages travel, curving away) · depth (old page
  flies past the camera, new one rushes in from far) · flip (turned over like a card) · drop (falls in from above)
  over (a card lands ON the previous segment, which dims under the first line and, if it's a grid, collapses into
  the red point on the second line's beat)
Segment extras: "fx": {"dust": {"x": [0.3, 0.78], "y": [0.24, 0.62], "n": 34}} motes hanging in the light of a clip.
Top level: "punches": [42.99] extra camera push-ins on drum hits (transitions and emphasis add their own).
  "never": ["https://site/"] pages that must never be on screen (the one that says the closing line): a shot that
  records one stops the build, and vs collage refuses a tile whose "from" is one.
Checks it runs before rendering (each one a note a reviewer once had to give): words in the phone safe zone, emphasis
that has no word to land on, a check mark on its word, a marker split by a line break, a font that never loaded,
grid tiles that are frames of this reel or the same picture twice, a "never" page. vs qa adds black holes near cuts.
Sources:
  {"scene": "chat" | "hub" | "sources" | "endcard"}   drawn in code (the runtime: engine/js/reel/), words from reel.json → "scenes"
  {"shot": "home", "inset": 0.78}                      a real page in a framed panel that floats in 3D with a glare that
                                                       follows its tilt (reel.json → "shots": a url that vs record
                                                       scrolls, or a "video" / "dir" of frames you recorded)
  {"clip": "media/x.mp4", "ss": 0, "speed": 1}         a video clip (generated, or your own footage)
  {"still": "media/x.jpg"}                            a still with a slow push-in ("push" on the segment sets how far)
  {"card": "t_title", "at": [0, 1, 2], "style": "flap" | "slam", "out": "shatter"}
                                                       a full-frame title card; "at" = beat each line arrives on; flap =
                                                       departures-board flip, slam = lands from over the camera with a
                                                       punch; shatter = every letter flies apart at the cut
  {"grid": ["media/collage/t01.jpg", …], "cols": 4}
                                                       the collage: tiles fly in from every side and land as a 3D wall
                                                       the camera sweeps over, then a red playhead runs them in order.
                                                       Build the tiles with vs collage from the thing's OWN work (real
                                                       postings + real visuals, all different); fill every row. ("@t" =
                                                       a frame of this reel still works, but a wall of the reel's own
                                                       scenes reads as repetition — review note, Sep 29.)
Titles (reel.json → "titles"): "spark": true on a stat fires it out of the scene's anchor; "em" = one emphasis on the
key word, on the beat ("b" beats after the title's slot): {"fx": "pulse" | "box" | "check" | "beats" | "ruler",
"word": "checked" (default: the accent words), "b": 1, "snap": 3 (ruler: the beat its marker lands)}.
```

## How it moves: max the motion on the PICTURE, never on reading time

- **A camera that hits with the drums.** `#camrig` punches in on the big hits (onset strength per beat of the bed; the
  band under 150 Hz marks the kicks); the words live outside it and never shake. Scenes are 3D: the chat tilts, the hub
  starts as a tilted close-up and swings face-on, the sources board orbits.
- **Nothing hard-cuts; segments hand off.** `rise` · `swing` · `depth` · `flip` · `drop` for pages; `dot` · `zoom` ·
  `whip`/`whipx` · `flash` · `over` for the rest. Vary them: five pages in a row with five different hand-offs pops.
- **Things arrive from somewhere.** Tools fly in along their spokes, cards from the sides, collage tiles from every
  direction; a card's letters `shatter` at the cut into the next scene. Never across the words.
- **The collage is the set piece:** sixteen different pieces of the thing's OWN work (real postings: cover, number,
  title; real visuals: dashboards, charts, diagrams, UI) landing as a 3D wall under a sweeping camera, a playhead running
  them in order, the next card landing `over` it, the wall collapsing into the motif point. `vs collage` builds the
  tiles at the reel's shape from `reel.json → "collage"` (see the top of `engine/js/collage.mjs`); capture sources at
  phone width (390 @3x) for vertical and desktop (1280 @2x) for widescreen; checkerboard postings and visuals.
- **One emphasis per key word, on the beat, after it lands:** `box`, `check`, `beats`, `ruler`, `pulse`; `spark` on stats.
- One motif carried through (a colored point). Seeded grain, vignette, drifting dot paper, dust in footage.
- Left out on purpose: a HUD (it sits where phones hide things) and sub-second word flurries ("words flying").

## Words and time

- About two seconds for a short title, more for a long one; a number as one big figure, not a sentence.
- One reading zone at a time: a scene with words gets no title; a titled scene is wordless behind it.
- Frame one is the preview in chat apps and most feeds: the hook title is on screen at t = 0, no fade-in.
- The phone safe zone (vertical, 1080 × 1920): every word in x 11–89%, y 10–84%, and below 62% height it stops at x 80%
  (a full-screen player crops ~9% off each side; the buttons, caption and status bar cover the rest). The build warns on
  any title outside it (`"size": 0.9` shrinks one); page recordings sit in a panel at 78% (`shot_inset`); `vs qa` scans
  four frames a second and prints the time ranges of anything in the covered areas.
