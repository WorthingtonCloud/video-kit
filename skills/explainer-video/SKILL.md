---
name: explainer-video
description: >
  Make a narrated motion-graphics explainer (2–3 minutes, vertical first, widescreen too) that explains a piece's
  concepts and the data behind them, end to end: the act-by-act arc, the narration, an ElevenLabs voice with word timings
  (or the user's own recording), scenes drawn in code and pinned to the words, the inspection of every element, review
  rounds in Review Studio (the user points at the frame; every answer is measured), a faint music bed and subtle sound
  effects dialed in by the user, and the user's logo at the end. It keeps a studio that learns:
  the settled look, voice, music and levels in profile.json, the user's notes as rules in lessons.md, and a library of
  sounds, music and media reused across videos. Use when the user says "/explainer-video", "make an explainer", "an
  explainer for <piece>", "a TL;DR video", "a narrated video for <post/report/note>", "explain <concept> in a video", or
  asks to revise, re-voice, re-mix or re-cut an explainer, or to bring their own footage, screenshots, audio or
  narration into one.
---

# explainer-video

A narrated explainer that replaces a piece's TL;DR. It explains the CONCEPTS and the data behind them; it is not a
video about the article. The narration keeps the time: every animation starts on the word it illustrates. It ends on
the user's logo. The agent writes, voices, draws, checks and mixes. The human directs in conversation and judges in
Review Studio, where a note is pinned to a moment, an element and a mark. They never edit the video themselves.

**How it works:** `narration.txt` → voice with word timings → `plan.json` (scenes and titles pinned to words) → `vs plan`
→ `reel.json` → `scenes.js` on the engine's scene library → `vs build --no-render` → `vs inspect` (an error blocks the
render) → render → Review Studio → `cues.py` (sounds pinned to the same words) → `vs mix` → the Mix panel.

## Start here, every time

1. **The command is this skill's `vs`**: `<this skill's folder>/vs <step>` (the base directory shown when the skill
   loads). Use the full path in every call; shell variables don't carry between calls, and zsh won't split `$VS step`.
2. **Read the studio's `lessons.md` and `profile.json` before anything else** (`vs where` prints where). They are this
   user's settled taste: the look, the narrator, the register, the music that won, the levels, the caps. Don't re-ask
   what they answer. A project's `plan.json` overrides the profile for one video.
3. `vs doctor`. No studio yet? `vs setup` (asks nothing, makes the studio, installs the engine once: about 190 MB).
4. **An existing video? `vs status` first** (`vs -p <video> status` from anywhere). It says where the video stands and the one next step. A
   finished one the human wants changed: `vs reopen <video>` (never edit a finished video's files first: reopen puts its
   sources back exactly as they made the final, and the next draft is the last version + 1).
5. **Three shared protocols** govern every stage below. Read them when you first need them, and follow them as written:
   `vs protocol files` (every name and folder, and the path from first draft to final and back), `vs protocol review`
   (every REVIEW stage, learning, finishing) and `vs protocol studio` (where every piece of information goes, and the
   gates every step shares). This file only adds what is particular to explainers.

A video is ONE project, both shapes: `studio/projects/<video>/` from `vs new <video> --kind explainer --shape vertical`
(the shape it starts in; the other comes once that one is approved). The kit names every file: never type one. Your
files: `SCRIPT.md` (the arc), `narration.txt`, `plan.json`, `scenes.js`, `cues.py`, `music.json`, `sfx.json`,
`NEXT.md`. Its media: `inputs/` (untouched originals), `media/`, `voice/`, `music/`. Every render lands in
`drafts/vN/` as `<video>-<shape>-vN.mp4`; finals and the latest copies are filed by `vs finish`. The kit's worked
example: `examples/meeting-explainer/` (ten scenes, 95 cues).

## The stages

Each stage: **do** → **gate** (don't move on until it holds) → **next**. Versions are never overwritten.

**1 · STORY.** Read the piece and pull the ideas: what must a cold viewer GET by the end? Each idea's evidence and its
source? What must the reader's organization PROVIDE (it gets its own act)? Which lines date themselves or say nothing
(cut them)? Write the arc as acts, one line each (idea · evidence + source · picture) → `SCRIPT.md`.
- Gate: the human OKs the arc in chat. Expect two rounds. Log it: `vs review step "OK'd the arc" --stage story`.
- Fails when: author/article framing, more than one spoken number per act, no "what to provide" act.

**2 · VOICE.** `narration.txt` → a take → checked → fitted → listened to (`references/voice.md`: the format, every
command, their own recording, re-recording one act).
- Gate: the human picks a take on the review page's listening view. Paid: say the number and wait for the yes.
- Produces: `voice/narration-<tag>.mp3` + its word timings → `vs voicebed`.

**3 · PICTURE (v1, voice only).** `plan.json`: segments per act, `cues` (word specs `"word"`, `"word#2"`, `"act:word"`,
`±secs`), `titles` (`[id, from, to]`) → `vs plan`. Write `scenes.js`: `vs help scenes` lists every helper with its
arguments (read it instead of the library's source); `references/scenes.md` has the design space and the overlap rules. Name what a note is likely to be about (`div()`'s 5th argument, `exName`).
**The build loop, every time, before the human sees anything:**
`vs build --no-render` (runs `vs check`) → **the check, delegated:** send the `video-checker` agent the project, this
`vs`'s full path, the moments of every new or changed scene, and what each moment should show (words, picture, what
moves). Pick settled moments: about a second after the cue of the last thing due, not on the cue itself. It runs `vs inspect --shots` and `vs snap`, looks at the contact sheets and returns only the problems; the
screenshots stay in its conversation, not this one. Fix, send it again, until it says no errors and nothing to fix
(phone-safe included). If it isn't available, run those steps yourself and LOOK at the sheets (`sheet-N.jpg`). Then
LOOK once yourself at one sheet of the whole video (`vs snap` with one moment per scene) → bump `"version"` in `plan.json`, `vs plan` → `vs build` **in the background**
(a few minutes, twice the unblended time: it draws two frames per frame and blends them, so tilting text doesn't
flicker). It runs `vs qa` on the new cut itself and prints nothing until both are done, so don't check on it: you're
woken with the QA report (safe zone, blacks, cuts sheet, flash, shimmer: any word in the red gets moved; shimmer means
a slow tilt is making thin lines flicker, so hold that stretch still).
- Gate: the checker (or inspect) says no errors, you LOOKED at the whole-video sheet, qa is clean. Produces: `drafts/vN/<video>-vertical-vN.mp4` + its `data/vertical/` (timing, maps, the sources that made it).

**4 · REVIEW (picture).** Enter REVIEW and follow `vs protocol review` exactly: open the round (`--stage picture`),
advise the findings, `vs review wait` in the background, read, resolve, measure, repeat.
- Explainer context: while the first shape is drafted, a round shows only it. A changed line is re-recorded act by act
  (`references/voice.md`), never the whole read.
- Gate: `vs review status --ready` (the human approved this version). Notes → fix → back to 3 for the next version.

**5 · SOUND (v2, once the picture is approved).** Music, cheapest first: the library's beds, theirs (`vs ingest <file>
--as music`), or `vs music` (prints the cost; their yes; `--yes`). Effects: `cues.py` (`vs sfx list` shows what's free;
missing ones via `sfx.json` + `vs sfx`, priced first). `vs mix` (the newest render) → every take mixed beside it +
the Mix panel. Then REVIEW with `--stage sound` (the protocol): they switch takes and set the levels by ear, answer any
single sound from the timeline, and Save. Details: `references/sound.md`.
- Gate: `vs review status --ready` and a saved mix → `vs mix --final`. The picture is never re-rendered for sound.

**6 · THE OTHER SHAPE.** `vs shape widescreen` (refused until the vertical is approved; it re-plans for the new shape)
→ the build loop again, and LOOK at every scene (an exit sized for a vertical frame stops in plain sight on a wide one:
exits × `EXIT`; what differs goes in plan.json → `"shapes"` → `"widescreen"`) → `vs build` → `vs mix --final` on the
widescreen render (the saved mix fits it: same voice, same times) → REVIEW in the SAME page: the round shows both
shapes with the Vertical | Widescreen switch at the top. Never a second server or port.
- Gate: both shapes approved in one round (`vs review status --ready` checks each).

**7 · FINISH.** `vs finish`: it files the approved mix of each shape into `finals/<video>/`, replaces
`latest/<video>/`, marks the video done, tells the page (Done, with the downloads) and keeps what was learned. Then
`vs review wait` → send both files from `latest/<video>/` in chat too → promote only the lessons the human decided (the
finish lists them) → any scene helper another video could use into `library/scenes/` → `vs review report` → update
`NEXT.md`.

**Later: a change to a finished video.** `vs reopen <video>` → back to 3 (or 5, for sound only) on the vertical, the
next version; then 6 and 7 again. The new final replaces the old one in `latest/`; `finals/` keeps both.

## Bring your own

The human will hand things over: screenshots, photos, screen recordings, clips, sound effects, music, their own voice,
a logo. `vs ingest <files or folder> [--as image|clip|sfx|music|voice|logo] [--note "what it is"]`. Pictures and video
are known by their format; **audio must be named** (ask: effect, music or narration?). The original stays untouched;
the working copy is normalized. Effects, music and logos go to the library; pictures, clips and narration go to the
project (`--to library` keeps a reusable one, named `lib:media/<file>` in a plan). In a scene: a picture through
`scene_data` (`{"img": "media/x.jpg"}` → `exPhoto`); a clip as a whole segment (`"source": {"clip": "media/x.mp4"}`) or
in a floating panel (`{"shot": "x"}` with `shots.x.video`); a clip's own sound or an effect in `cues.py`; music as a take.

## Guardrails for explainers

- **Every number on screen is verified against its source on render day, with a source tag.**
- **Text never fights a picture** (`vs inspect` enforces it; the rules are in `references/scenes.md`).
- The shared gates (paid steps ask first, every version new, nothing publishes without an explicit go, long jobs):
  `vs protocol studio`.

## References (read the one you need)

- `vs protocol files` · `vs protocol review` · `vs protocol studio`: the shared protocols (above).
- `references/voice.md`: narration, takes, fitting, their own recording, re-recording an act.
- `references/scenes.md`: the scene library, the design space, the overlap rules, widescreen.
- `references/sound.md`: cues, starting levels, the bundled sounds, the Mix panel, music.
- `references/scars.md`: every mistake that cost a round of notes, by area. Read the area before working in it.
- `references/costs.md`: what things cost, from real runs.
- `vs help review`: every Review Studio command and option, and the tags.
