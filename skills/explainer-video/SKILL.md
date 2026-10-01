---
name: explainer-video
description: >
  Make a narrated motion-graphics explainer (2–3 minutes, vertical first, widescreen too) that explains a piece's
  concepts and the data behind them, end to end: the act-by-act arc, the narration, an ElevenLabs voice with word timings
  (or the user's own recording), scenes drawn in code and pinned to the words, the overlap audit, a faint music bed and
  subtle sound effects dialed in by the user in a mixer, and the user's logo at the end. It keeps a studio that learns:
  the settled look, voice, music and levels in profile.json, the user's notes as rules in lessons.md, and a library of
  sounds, music and media reused across videos. Use when the user says "/explainer-video", "make an explainer", "an
  explainer for <piece>", "a TL;DR video", "a narrated video for <post/report/note>", "explain <concept> in a video", or
  asks to revise, re-voice, re-mix or re-cut an explainer, or to bring their own footage, screenshots, audio or
  narration into one.
---

# explainer-video

A narrated explainer that replaces a piece's TL;DR. It explains the CONCEPTS and the data behind them; it is not a
video about the article. The narration keeps the time: every animation starts on the word it illustrates. It ends on
the user's logo. The agent writes, voices, draws, checks and mixes; the human approves and gives notes as "time + what".

**How it works:** `narration.txt` → voice with word timings → `plan.json` (scenes and titles pinned to words) → `vs plan`
→ `reel.json` → `scenes.js` on the engine's scene library → HyperFrames render → `vs audit` (overlaps) → `cues.py`
(sounds pinned to the same words) → `vs mix` → the mixer, where the human picks the music and the levels.

## Start here, every time

1. **The command is this skill's `vs`**: `<this skill's folder>/vs <step>` (the base directory shown when the skill
   loads). Use the full path in every call; shell variables don't carry between calls, and zsh won't split `$VS step`.
2. **Read the studio's `lessons.md` and `profile.json` before anything else** (`vs where` prints where they are). They
   are this user's taste, already settled: the look, the narrator, the register, the music that won, the levels, the
   spending caps, every note they've given. Don't re-ask what they answer. A project's `plan.json` overrides the
   profile for one video.
3. `vs doctor`. No studio yet? `vs setup` (asks nothing, makes the studio, installs the engine once: about 190 MB).

## Where things live: what's kept vs what's made for one video

- **The studio (kept between videos):** `profile.json` (settled values), `lessons.md` (notes as rules), `library/`
  (`sfx/` sounds, `music/` beds that won and tracks brought in, `brand/` fonts and logo, `media/` reusable pictures and
  clips, `scenes/` scene pieces promoted from a finished video), `finals/`, `ledger.csv` (every paid call, every video).
- **A project (this video only):** `studio/projects/<slug>/` from `vs new <slug> --kind explainer`. Yours: `SCRIPT.md`
  (the arc), `narration.txt`, `plan.json`, `scenes.js`, `cues.py`, `music.json`, `sfx.json`, `NEXT.md`. Its media:
  `inputs/` (what the human handed over, untouched), `media/` (working copies, generated stills), `voice/`, `music/`
  (its takes). `build/` is regenerated (comp, qa, mix, mixer). `out/` keeps every version.
- **The kit (read-only):** the engine, the scene library (`references/scenes.md`), 30 bundled sounds (`vs sfx list`),
  the templates, a worked example (`examples/meeting-explainer/`: ten scenes, 95 cues).

## The steps, with the gates

Each step ends with something the human can see or hear, and waits for their call. Versions are never overwritten.

1. **Read the piece; pull the ideas.** What must a cold viewer GET by the end? Each idea's evidence, and its source? What
   must the reader's organization PROVIDE (it gets its own act)? Which lines date themselves or say nothing (cut them)?
2. **The arc first, as acts** (one line each: idea · evidence + source · picture) → `SCRIPT.md`. Expect two rounds.
   Watch for: author/article framing, more than one spoken number per act, a missing "what to provide" act.
3. **The narration.** `narration.txt`: one paragraph per act under `# N title`; v4 tags in brackets direct the voice
   and aren't spoken; CAPS = emphasis; `...` = a beat. Never a vocal action ("clears its throat" gets performed).
   `vs narrate <tag>` (paid, about 0.06 ElevenLabs credits a character: say the number first) → `vs check-take voice/narration-<tag>.mp3` (fix any word that
   changes the meaning) → `vs pitch …` (a flat read is the failure) → `vs listen …` → the human listens; say you can't.
   **Their own recording instead:** `vs ingest <file> --as voice` (word timings by transcription, about a cent a minute,
   asks first) splits it into the script's acts; everything after works the same.
4. **The picture, voice only (v1).** `vs voicebed --take voice/narration-<tag>.mp3 --out <tag>`; `plan.json`: segments
   per act, `cues` (word specs `"word"`, `"word#2"`, `"act:word"`, `±secs`), `titles` (`[id, from, to]`); `vs plan`.
   Write `scenes.js` (`references/scenes.md`: the helpers, the props, the design space, the overlap rules). The loop,
   every time, before the human sees anything: `vs build --no-render` → `vs audit --shots` (must say **no overlaps**,
   phone-safe included; `vs crops 1,2` to look at hits) → `vs snap <secs> …` and LOOK at every new scene's key moments
   → `vs build` (~4 min) → `vs qa out/<name>-vN.mp4` (safe zone, blacks, cuts sheet; any word in the red gets moved).
5. **Notes.** Fix in code and run the loop again. A changed line: re-record only those acts (`vs narrate <tag> --acts
   9-10`), `vs check-take`, `vs voicebed --base <approved> --take <new> --out <tag>`, point plan.json at it, `vs plan`.
   A line that "isn't resonating": two wordings (tighter vs fuller) with what each costs, and a recommendation.
   **Every note becomes a rule in `lessons.md` the same day** (one line, dated, with the why, the human's own words).
6. **The sound pass (v2), once the picture is right.** Music: `vs music` prints the cost (directions from the profile;
   `music.json` overrides) → the human's yes → `vs music --yes`. Or the library's beds, or theirs (`vs ingest <file>
   --as music` makes it a take). Sounds: write `cues.py` (`references/sound.md`; `vs sfx list` shows what's free); for
   sounds the library lacks, `sfx.json` + `vs sfx` (prints the cost; only missing ones are bought, and they stay in the
   library). `vs mix --video out/<name>-vN.mp4 --tag vN` → every take mixed + the mixer. `vs mixer` serves it (a
   `.claude/launch.json` entry running `<vs> -p <slug> mixer --port 4470` opens it in the preview pane at
   `/build/mixer/`): the human switches takes live, sets levels, presses **Save** (→ `mix.json`). Then
   `vs mix --video … --tag vN --final`. The picture is never re-rendered for sound.
7. **The other shape.** `vs plan --wide` → the loop again, and LOOK at every scene (an exit sized for a vertical frame
   stops in plain sight on a wide one: exits × `EXIT`) → mux the approved sound: `ffmpeg -i out/<name>-16x9-vN.mp4 -i
   out/<name>-vN-take<N>.mp4 -map 0:v -map 1:a -c copy out/<name>-16x9-vN-take<N>.mp4`. Then `vs plan` (back to vertical).
8. **Finish: the studio learns.** `vs learn --final out/<name>-vN-take<N>.mp4 out/<name>-16x9-vN-take<N>.mp4`: finals to
   `finals/`, the saved levels and the winning music into the profile, the winning take into `library/music`, one line
   of history. Then the agent's part: any new rule into `lessons.md`; any scene helper another video could use into
   `library/scenes/` (it prints the candidates). Update `NEXT.md` so the next session starts from the file.

## Bring your own

The human will hand things over: screenshots, photos, screen recordings, clips, sound effects, music, their own voice,
a logo. `vs ingest <files or folder> [--as image|clip|sfx|music|voice|logo] [--note "what it is"]`. Pictures and video
are known by their format; **audio must be named** (ask whether it's an effect, music or narration). The original stays
untouched; the working copy is normalized (a screen recording's variable frame rate is made steady; HEIC converted);
everything is indexed (`media.json`; each library folder's `index.json`). Effects, music and logos go to the library;
pictures, clips and narration go to the project (`--to library` keeps a reusable one, named `lib:media/<file>` in a plan).
Using them: a picture in a scene through `scene_data` (`{"img": "media/x.jpg"}` → `exPhoto`); a clip as a whole segment,
full frame (`"source": {"clip": "media/x.mp4"}`) or in a floating panel (`{"shot": "x"}` with `shots.x.video`); a
clip's own sound or an effect by name or path in `cues.py`; music as a mixer take.

## Guardrails

- **Paid generation: ask first, every time, with the number,** then run with `--yes`. Every paid script refuses past the
  profile's caps and logs to the studio ledger (`vs spent`). Some vendors auto-recharge: the balance is not a budget.
- **Nothing publishes without the human's explicit go, per ship.** The mixer runs locally; it is not an artifact.
- **Every number on screen is verified against its source on render day, with a source tag.**
- **Text never fights a picture** (`vs audit` enforces it; the rules are in `references/scenes.md`).
- **Long jobs:** a render is ~4 minutes; watch it with a monitor that exits on the result or a failure, never on silence.

## References (read the one you need)

- `references/scenes.md`: the scene library (helpers, icons, props), the design space, the overlap rules, widescreen.
- `references/sound.md`: cues, starting levels, the bundled sounds, the mixer, music.
- `references/scars.md`: every mistake that cost a round of notes, by area. Read the area before working in it.
- `references/costs.md`: what things cost, from real runs.
