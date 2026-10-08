---
name: sizzle-reel
description: >
  Make a short promo / sizzle reel (30–60 seconds, vertical first, widescreen too) end to end: the brief, the
  narrative, the music and its beat grid, scenes drawn in code and rendered by HyperFrames, real page recordings, the
  user's own footage and screenshots, a few paid mood shots, the beat-synced edit, the agent's own frame-by-frame QA,
  the cover. It keeps a studio that learns: the settled look, music style and spending caps in profile.json, the user's
  notes as rules in lessons.md, and a library reused across videos. Use when the user says "/sizzle-reel", "make a
  sizzle reel", "make a promo video", "make a reel for <thing>", "a trailer for <thing>", "a LinkedIn video for
  <thing>", or asks to revise, re-cut, or make a widescreen version of a reel, or to bring their own footage into one.
---

# sizzle-reel

A 30–60 second reel the agent makes by itself: it writes it, makes or picks the music, draws the scenes, records the
real pages, prompts the few paid shots, cuts on the beat, and checks it. The human directs in conversation and judges
in Review Studio (a note pinned to a moment, an element and a mark, or a pick between options); they never touch the
timeline. Narrated videos with the voice as the clock use the `explainer-video` skill (same engine).

**How it works:** `reel.json` (the music, the shots, the titles, the segments on the beat grid) → `vs build` writes ONE
HyperFrames composition → `vs inspect` maps every element by name and finds words and pictures fighting (an error
blocks the render) → HyperFrames renders it frame by frame, audio included → `vs qa` → Review Studio.

## Start here, every time

1. **The command is this skill's `vs`**: `<this skill's folder>/vs <step>` (the base directory shown when the skill
   loads), the full path in every call.
2. **Read the studio's `lessons.md` and `profile.json` first** (`vs where`): the look, the reel's music direction, the
   spending caps, every note this user has given. Don't re-ask what they answer. `reel.json` overrides for one reel.
3. `vs doctor`. No studio yet? `vs setup`. A new reel: `vs new <video> --kind reel --shape vertical` (the shape it
   starts in; the other comes once that one is approved).
4. **An existing reel? `vs status` first** (`vs -p <video> status` from anywhere). It says where the reel stands and the one next step. A finished
   one the human wants changed: `vs reopen <video>` (never edit a finished reel's files first).
5. **Three shared protocols** govern every stage below. Read them when you first need them, and follow them as written:
   `vs protocol files` (every name and folder, and the path from first draft to final and back), `vs protocol review`
   (every REVIEW stage, learning, finishing) and `vs protocol studio` (where every piece of information goes, and the
   gates every step shares). This file only adds what is particular to reels.

A reel is ONE project, both shapes (`studio/projects/<video>/`): `reel.json`, `SCRIPT.md`, `brainstorm-*.md`,
`scenes.js` (its own scenes), `NEXT.md`; `inputs/` (what the human handed over), `media/` (working copies, generated
stills and clips), `music/`. Every render lands in `drafts/vN/` as `<video>-<shape>-vN.mp4`. What the other shape
does differently lives in the same `reel.json` → `"shapes"` → `"widescreen"` (its own `segments`, crops), with
`scenes.widescreen.js` and `media/widescreen/` only when the code or a crop has to differ. The kit names every file.

## The stages

Each stage: **do** → **gate** (don't move on until it holds) → **next**. Versions are never overwritten.

**1 · BRIEF.** A short grill, only the open questions, one at a time, each with your recommended answer, every answer
written to `brainstorm-<date>.md` before the next: what the reel is FOR and where it will post; what a viewer should
GET by the end (a reel that brags about the agent and then shows a website leaves people asking "what's this for?");
the closing line; what real footage, pages or screenshots exist (ask for them: they beat anything generated); any
exception to the profile. Five questions, not twenty.
- Gate: every answer written down. Log it: `vs review step "Answered the brief" --stage brief`.

**2 · STORY.** Pitch 2–3 narratives, each with a beat sheet; recommend one. Write the pick to `SCRIPT.md`: beats,
on-screen words, the source of each beat (drawn scene / page recording / their footage / paid shot), the cost. The story
connects: problem → what this is → what the viewer gets → proof → close.
- Gate: the human picks one in chat.

**3 · MUSIC, free first.** The studio's `library/music`, the human's own track (`vs ingest <file> --as music`), or the
~$2 test with their yes: one music call (`vs gen music --style "…"`: 2 takes, $0.06; the profile's reel direction is the
starting style) plus, if the script has paid shots, one 480p draft (~$1.03). They pick by ear; say you can't hear.
- Gate: a take picked. Then the beat grid: `vs beats music/<take>.mp3 --write`. Check the first hit against the sketch;
  `--hit <secs>` if the human hears the drop elsewhere. If the cut outgrows the song: fit the picture to the song first,
  else replay whole bars, else Suno extend; offer both.

**4 · BUILD, free first.** Drawn scenes, page recordings (`vs record`), the human's footage and screenshots (`vs
ingest`), titles, cards, the collage (`vs collage`), push-ins on stills (`references/motion.md`: what `reel.json` can
say). Project-only scenes go in `scenes.js` (`Object.assign(SCENES, {…})`; `vs help scenes` lists every helper with its
arguments, instead of reading the library's source); name what a note is likely to be about
(`div()`'s 5th argument, `exName`). **The build loop:** `vs build --no-render` → send the `video-checker` agent the project, this
`vs`'s full path, the settled moments of every new or changed segment (a beat or so after the last thing lands) and what each should
show; it runs `vs inspect` and `vs
snap`, looks at the sheets and returns only the problems (must come back with **no errors**). Fix, send it again.
Then `vs build --storyboard` → LOOK at every frame of `build/qa/storyboard.jpg` yourself; fix.
- Gate: no errors, and you LOOKED.

**5 · PAID SHOTS** (only textless mood moments nothing on the laptop can make; their yes, per batch). `vs gen still|clip
…` prints the cost and stops → draft at 480p → `vs qa <clip> --clip` → LOOK → 720p only for the approved draft → QA
again. Every generation gets a ledger row, kept or rejected, with why.

**6 · CUT.** Bump `version` in `reel.json`, `vs build` in the background (~a minute for 58 s; it runs `vs qa` on the
cut itself and prints nothing until both are done, so don't check on it). Every ⚠️ either prints is a note a human once had to give: fix it, don't explain it. Open the first frame, the safe sheet and
the cuts sheet (ghosted titles, empty frames, early lines, flashes of black).
- Gate: inspect and qa clean. Produces: `drafts/vN/<video>-<shape>-vN.mp4` + its `data/<shape>/` (timing, maps, sources).

**7 · REVIEW.** Enter REVIEW and follow `vs protocol review` exactly: open the round (`--stage picture`), advise the
findings, `vs review wait` in the background, read, resolve, measure, repeat.
- Reel context: while the first shape is drafted a round shows only it; after `vs shape` it shows both, on the same page
  (the Vertical | Widescreen switch). Never a second server or port. Say the cost of any paid note before acting on it.
- Gate: `vs review status --ready`. Notes → fix → back to 4–6 for the next version.

**8 · THE OTHER SHAPE.** Once the first shape is approved: `vs shape widescreen` (refused until then) → its
`reel.json` → `"shapes"` → `"widescreen"` block (segments, crops) → the build loop → `vs build` (LOOKED at again) →
REVIEW in the same page, both shapes on the switch. A reel made in one shape only skips this (`vs finish --one-shape`).

**9 · FINISH.** The cover JPEG (the kit writes it; frame one says the hook). Effects under the music, if the profile or
the human wants them: `cues.py` + `vs mix` → REVIEW with `--stage final` (the Mix panel: the reel's own track is the
reference; they set the effects against it) → `vs mix --final` (on each shape's render). Then `vs finish`: it files
each shape into `finals/<video>/` with its web copy (small enough to upload), replaces `latest/<video>/`, marks the reel done, tells the page and keeps what was
learned → `vs review wait` → promote only the lessons the human decided → `vs review report` → update `NEXT.md`.

**Later: a change to a finished reel.** `vs reopen <video>` → back to 4–7 on the first shape, the next version; then
8 and 9 again. The new final replaces the old one in `latest/`; `finals/` keeps both.

## Bring your own

`vs ingest <files or folder> [--as image|clip|sfx|music|logo] [--note "…"]`: screenshots and photos (→ `media/`,
normalized), screen recordings and clips (→ `media/<name>.mp4`, a steady frame rate, their sound kept as a `.wav`),
audio (say what it is: effect or music), logos. Use them as `{"still": "media/x.jpg"}`, `{"clip": "media/x.mp4"}`
(full frame), `{"shot": "x"}` with `"shots": {"x": {"video": "media/x.mp4"}}` (a floating panel that tilts in 3D), or
as collage tiles. A reusable one (`--to library`) is named `lib:media/<file>`.

## Guardrails for reels

- **Text is drawn in code, never by a video model** (models garble labels and invent logos). Paid shots are textless.
- **Every number on screen is re-checked against a live public page on render day.**
- **The closing line is spent once:** list the page that says it in `reel.json → "never"` and the kit stops you.
- The shared gates (paid steps ask first with the number, the profile's budget, every version new, nothing posts
  without an explicit go): `vs protocol studio`.

## References

- `vs protocol files` · `vs protocol review` · `vs protocol studio`: the shared protocols (above).
- `references/motion.md`: the segment, source, transition and emphasis vocabulary (what `reel.json` can say).
- `references/scars.md`: every mistake that cost a round of notes. Read it before the first cut.
- `references/costs.md`: what things cost, from real reels.
- `vs help review`: every Review Studio command and option, and the tags.
