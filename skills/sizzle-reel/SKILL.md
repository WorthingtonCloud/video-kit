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
real pages, prompts the few paid shots, cuts on the beat, and checks it. The human approves and gives notes; they never
touch the timeline. Narrated videos with the voice as the clock use the `explainer-video` skill (same engine).

**How it works:** `reel.json` (the music, the shots, the titles, the segments on the beat grid) → `vs build` writes ONE
HyperFrames composition (`build/comp/index.html`: the runtime, the scenes, the titles, the transitions, the finish) →
HyperFrames renders it frame by frame in headless Chrome, audio included → `vs qa`.

## Start here, every time

1. **The command is this skill's `vs`**: `<this skill's folder>/vs <step>` (the base directory shown when the skill
   loads), the full path in every call.
2. **Read the studio's `lessons.md` and `profile.json` first** (`vs where`): the look, the reel's music direction, the
   spending caps, every note this user has given. Don't re-ask what they answer. `reel.json` overrides for one reel.
3. `vs doctor`. No studio yet? `vs setup`. A new reel: `vs new <slug> --kind reel`.

**What lives where:** the studio keeps `profile.json`, `lessons.md`, `library/` (music that won, sounds, fonts, logo,
reusable media, promoted scene pieces), `finals/`, `ledger.csv`. A project (`studio/projects/<slug>/`) holds the reel:
`reel.json`, `SCRIPT.md`, `brainstorm-*.md`, `scenes.js` (its own scenes), `NEXT.md`; `inputs/` (what the human handed
over), `media/` (working copies, generated stills and clips), `music/`; `build/` is regenerated (comp, qa, rec); `out/`
keeps every version.

## The steps, with the gates

1. **A short grill, only the open questions**, one at a time, each with your recommended answer, every answer written to
   `brainstorm-<date>.md` before the next: what is the reel FOR and where will it post; what should a viewer GET by the
   end (a reel that brags about the agent and then shows a website leaves people asking "what's this for?"); the closing
   line; what real footage, pages or screenshots exist (ask for them: they beat anything generated); any exception to
   the profile. Five questions, not twenty.
2. **Pitch 2–3 narratives, each with a beat sheet; recommend one; wait for the pick.** Write it to `SCRIPT.md`: beats,
   on-screen words, the source of each beat (drawn scene / page recording / their footage / paid shot), the cost. The
   story connects: problem → what this is → what the viewer gets → proof → close.
3. **Music, free first.** The studio's `library/music`, the human's own track (`vs ingest <file> --as music`), or the
   ~$2 test with their yes: one music call (`vs gen music --style "…"`: 2 takes, $0.06; the profile's reel direction is
   the starting style) plus, if the script has paid shots, one 480p draft (~$1.03). They pick by ear; say you can't hear.
4. **Beat grid:** `vs beats music/<take>.mp3 --write`. Check the first hit against the sketch; `--hit <secs>` if the
   human hears the drop elsewhere. The cuts land with the drum a viewer hears (it prints which). If the cut outgrows the
   song: fit the picture to the song first, else replay whole bars before the build, else Suno extend; offer both.
5. **Build free first:** drawn scenes, page recordings (`vs record`), the human's footage and screenshots (`vs ingest`),
   titles, cards, the collage (`vs collage`), push-ins on stills. Paid shots only for textless mood moments nothing on
   the laptop can make. Project-only scenes go in `scenes.js` (`Object.assign(SCENES, {…})`; it shares the runtime's
   helpers). `vs build --storyboard` → `build/qa/storyboard.jpg` (hero frames, no render): LOOK at every frame; fix.
6. **Paid shots** (their yes, per batch): `vs gen still|clip …` prints the cost; draft at 480p → `vs qa <clip> --clip` →
   LOOK → 720p only for the approved draft → QA again. Every generation gets a ledger row, kept or rejected, with why.
7. **Cut:** `vs build` (~a minute for 58 s), then `vs qa out/<name>-vN.mp4`. Every ⚠️ either prints is a note a human
   once had to give: fix it, don't explain it. Open the first frame, the safe sheet, and the cuts sheet (one strip per
   transition: ghosted titles, empty frames, early lines, flashes of black). Bump `version` for every cut they review.
8. **Send it:** the file, what changed in one line each, the spend so far. Notes come back as "time + what"; each note
   also becomes a rule in `lessons.md` the same day (one line, dated, with the why). Say the cost of any paid note first.
9. **Finish:** the cover JPEG (the kit writes it); frame one says the hook; widescreen if wanted (the same `reel.json`
   with `size` flipped, LOOKED at again). Effects under the music, if the profile or the human wants them: `cues.py` +
   `vs mix --video out/<name>-vN.mp4 --tag vN` + `vs mixer` (the human sets the effects against the track and Saves).
   Then `vs learn --final <files>` (finals filed, the winning track into the library, history) and update `NEXT.md`.

## Bring your own

`vs ingest <files or folder> [--as image|clip|sfx|music|logo] [--note "…"]`: screenshots and photos (→ `media/`,
normalized), screen recordings and clips (→ `media/<name>.mp4`, a steady frame rate, their sound kept as a `.wav`),
audio (say what it is: effect or music), logos. Use them as `{"still": "media/x.jpg"}`, `{"clip": "media/x.mp4"}`
(full frame), `{"shot": "x"}` with `"shots": {"x": {"video": "media/x.mp4"}}` (a floating panel that tilts in 3D), or
as collage tiles. A reusable one (`--to library`) is named `lib:media/<file>`.

## Guardrails

- **Paid generation: ask first, every time, with the number.** Budget per the profile (~$15); `vs gen` refuses past it.
- **Text is drawn in code, never by a video model** (models garble labels and invent logos). Paid shots are textless.
- **Every number on screen is re-checked against a live public page on render day.**
- **The closing line is spent once:** list the page that says it in `reel.json → "never"` and the kit stops you.
- **Nothing posts anywhere without the human's explicit go, per post.**

## References

- `references/motion.md`: the segment, source, transition and emphasis vocabulary (what `reel.json` can say).
- `references/scars.md`: every mistake that cost a round of notes. Read it before the first cut.
- `references/costs.md`: what things cost, from real reels.
