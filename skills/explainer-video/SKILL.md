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
the user's logo. The agent writes, voices, draws, checks and mixes; the human reviews in Review Studio, where a note is
pinned to a moment, an element and a mark, and never edits the video themselves.

**How it works:** `narration.txt` → voice with word timings → `plan.json` (scenes and titles pinned to words) → `vs plan`
→ `reel.json` (checked against its contract: `vs check`) → `scenes.js` on the engine's scene library → `vs build
--no-render` → `vs inspect` (every element by name; an error blocks the render) → HyperFrames render → Review Studio
(`vs review`: rounds of notes, choices, standing rules) → `cues.py` (sounds pinned to the same words) → `vs mix` → the
Mix panel, where the human picks the music, the levels and the ducking.

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
   `vs narrate <tag>` prints the cost and stops (about 0.06 ElevenLabs credits a character; the spend gate) → say the
   number → the human's yes → `vs narrate <tag> --yes` → `vs check-take voice/narration-<tag>.mp3` (fix any word that
   changes the meaning) → `vs pitch …` (a flat read is the failure) → too long for its slot? `vs fit --take … --secs N
   --out <tag>` (shorter pauses, then a faster read, timings moved with it; `--pause none` keeps the comic timing) →
   `vs listen take.mp3="a label" …` → the human listens in Review Studio (no round yet: the listening page sits where the
   video goes, on the same address); say you can't.
   **Their own recording instead:** `vs ingest <file> --as voice` (word timings by transcription, about a cent a minute,
   asks first) splits it into the script's acts; everything after works the same.
4. **The picture, voice only (v1).** `vs voicebed --take voice/narration-<tag>.mp3 --out <tag>`; `plan.json`: segments
   per act, `cues` (word specs `"word"`, `"word#2"`, `"act:word"`, `±secs`), `titles` (`[id, from, to]`); `vs plan`.
   Write `scenes.js` (`references/scenes.md`: the helpers, the props, the design space, the overlap rules); name what a
   note is likely to be about (`div()`'s 5th argument, `exName`). The loop, every time, before the human sees anything:
   `vs build --no-render` (runs `vs check` first) → `vs inspect --shots` (must say **no errors**, phone-safe included;
   `vs crops 1,2` to look at hits; its warnings go to the human) → `vs snap <secs> …` and LOOK at every new scene's key
   moments → bump `"version"` in `plan.json` and `vs plan` → `vs build` (~4 min; it refuses a composition inspect hasn't
   passed, and never overwrites a version) → `vs qa out/<name>-vN.mp4` (safe zone, blacks, cuts sheet, flash; any word
   in the red gets moved).
5. **Review, every version, in Review Studio.** `vs review open --stage picture` starts a round on the newest render
   (refused while inspect has open errors, `--ask` puts them to the human; refused while the human has feedback they
   haven't sent). With `out/<name>-16x9-vN…` rendered at the same version, the round shows both shapes: a Vertical |
   Wide switch (S), and every note, finding and approval belongs to the shape on screen (`vs review show` labels
   each note VERTICAL or WIDESCREEN; `--only` opens one shape). Serve it: ONE `.claude/launch.json` entry per video, `<vs> -p <slug> review --port <its own port>`,
   started once at the voice step. **Its address (`http://localhost:<port>/review/`) is the only link the human ever
   gets, every round, every stage:** the open tab follows the project live (the narration, each new version, the Mix
   section opens itself when `vs mix` makes one), in any browser. Never a second server, a `#hash` link or a file path.
   **The loop, the same every round:** the human gives feedback (points at the frame, writes, answers your fixes and
   questions, picks, approves the version); each thing waits in the page with Undo; they review the list, press
   **Approve & send** (nothing to change: **No notes · send**, which still reaches you as "no notes this round"). A
   warning they answered in an earlier round is carried to the next version by `vs review open` (same check, same
   place, within 3 s): never ask twice. Right after you tell them a round is open, run `vs review wait` in the background: it exits the
   moment they send (and prints `vs review show`), which wakes you, and the page tells them Claude is watching, so they
   never come back to type "sent" (no wait running: the page asks them to). Only what was sent reaches you (`state.json`, `vs review show`); a note they
   add after a send waits for its own send ("sent again"). Steps decided in chat (an OK on the outline, a yes to a
   price) go in their log of steps: `vs review step "<what they did>" [--stage story] [--when <time>]`. Then:
   - `vs review show` (reading it tells the page you have it): every note's moment, target element, mark and words. LOOK at each still
     (`review/frames/<note>.jpg`: what they saw, the target and mark drawn on it). Unsure what they mean? `vs review ask
     <note> "…"`; never guess.
   - Fix in code (an element with a derived `~name` that got a note gets a real name), run the loop, then answer every
     note: `vs review resolve <note> --said "what changed" --files … --tags …` (`--wontdo` with the reason; a target
     that's gone needs `--renamed <new>` or `--removed`; the tags are in `vs help review`).
   - The next version: `vs review open` measures every answer in it (moved, resized, reworded, re-timed). A claimed fix
     that measured as nothing is flagged: fix it, or say why it's not a box (a color, a sound). The human says Looks
     right, Still wrong (with words) or follows up, and approves the version (one click) when it's done.
   - **More than one good way? Offer a choice, don't guess.** Build each (`vs build --no-render` → `vs inspect` →
     `vs review variant <id> "what it is"`), then `vs review offer "<question>" --option a --option b [--t <from> <to>]
     [--for <note>]`. The human plays each one live in **Decide** (no render) and picks; `vs review apply <choice>` puts
     the pick back into the project. Music takes (`--option 2=take:2`) and paid options (`--paid c='<the step>'`, priced
     by its own spend gate; picking it is the yes) work the same way.
   - **Standing rules:** a keep-clear zone in a sent note, and a scene the human marks done, are rules `vs inspect`
     enforces from then on (`keep-clear`, `done-changed`). Change a done scene only after they reopen it in the page.
   - **Warnings are theirs to call, with your advice:** two reading zones, fast text and things parked off the frame
     (`vs inspect`), flash, loudness, true peak, sound density and covered areas (`vs qa`) show in the page in plain words,
     a card per check. Before you tell them a round is open, advise each: `vs review advise --check <check> --advice
     leave|fix --plain "what it is, plainly" --why "…"` (`vs review open` and `show` list the ones without advice). They
     take your advice in one click, or not: Fix it = real (treat it as a note), Leave it = fine as it is. Their
     thresholds live in `profile.json → checks`.
   - A changed line: re-record only those acts (`vs narrate <tag> --acts 9-10`, its cost first), `vs check-take`,
     `vs voicebed --base <approved> --take <new> --out <tag>`, point plan.json at it, `vs plan`. A line that "isn't
     resonating": offer two wordings (tighter vs fuller) as a choice, with what each costs.
6. **Learning: nothing becomes a rule without the human's click.** Every note is one-off by default. Tag each answer;
   `vs review learn` shows the patterns (a tag on accepted notes in two projects, or three times in one). Word one as a
   rule in the human's terms: `vs review propose <tag> "<the rule>"`; they answer Remember, This video only or Ignore in
   the page (Ignore is remembered too). `vs review show` says where a remembered one goes: `profile.json` (a value or a
   check's threshold), `lessons.md` (a rule, in their words, dated, with the why) or this plan (this video only). Taste
   never goes into the kit.
7. **The sound pass (v2), once the picture is right.** Music: `vs music` prints the cost (directions from the profile;
   `music.json` overrides) → the human's yes → `vs music --yes`. Or the library's beds, or theirs (`vs ingest <file>
   --as music` makes it a take). Sounds: write `cues.py` (`references/sound.md`; `vs sfx list` shows what's free); for
   sounds the library lacks, `sfx.json` + `vs sfx` (prints the cost; only missing ones are bought, and they stay in the
   library). `vs mix --video out/<name>-vN.mp4 --tag vN` → every take mixed + the Mix panel's stems. `vs mixer` opens
   Review Studio on its **Mix** section (`/review/#mix`): the human switches takes live, sets the music level, the ducking
   (how far the music dips while the voice speaks) and the effects, and presses **Save**: in a round it waits with the
   rest of their feedback and reaches `mix.json` when they send (no round open: at once). A sound they
   don't like comes back as a note on that one sound (they click it on the timeline, hear it alone, and answer quieter,
   louder, a different sound, or remove it): fix it in `cues.py` and re-mix; the next round measures it. Then
   `vs mix --video … --tag vN --final`. The picture is never re-rendered for sound.
8. **The other shape.** `vs plan --wide` → the loop again, and LOOK at every scene (an exit sized for a vertical frame
   stops in plain sight on a wide one: exits × `EXIT`) → mux the approved sound: `ffmpeg -i out/<name>-16x9-vN.mp4 -i
   out/<name>-vN-take<N>.mp4 -map 0:v -map 1:a -c copy out/<name>-16x9-vN-take<N>.mp4`. Then `vs plan` (back to vertical).
9. **Finish: the end of the flow is visible.** `vs review finish --final out/<name>-vN-takeK.mp4 out/<name>-16x9-…`:
   the page shows "Done" with both files to download and a way back in (pick the part, leave a note, send), and you run
   `vs review wait` again. In chat: send both files too.
10. **The studio learns.** `vs learn --final out/<name>-vN-take<N>.mp4 out/<name>-16x9-vN-take<N>.mp4`: finals to
   `finals/`, the saved levels and the winning music into the profile, the winning take into `library/music`, one line
   of history. Then the agent's part: any new rule into `lessons.md`; any scene helper another video could use into
   `library/scenes/` (it prints the candidates). `vs review report` gives the review's numbers (notes pinned, right
   first time, findings, time spent, cost). Update `NEXT.md` so the next session starts from the file.

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

- **Paid generation: ask first, every time, with the number,** then run with `--yes`. Every paid step goes through one
  spend gate: it prints the estimate and this video's spend so far, refuses past the profile's caps and budget, and
  logs to the studio ledger on submit (`vs spent`). Some vendors auto-recharge: the balance is not a budget.
- **Nothing publishes without the human's explicit go, per ship.** Review Studio runs locally; it is not an artifact.
- **Every number on screen is verified against its source on render day, with a source tag.**
- **Text never fights a picture** (`vs inspect` enforces it; the rules are in `references/scenes.md`).
- **Every version is new:** bump `"version"` before every render; the gate refuses to overwrite one a round has seen.
- **Long jobs:** a render is ~4 minutes; watch it with a monitor that exits on the result or a failure, never on silence.

## References (read the one you need)

- `references/scenes.md`: the scene library (helpers, icons, props), the design space, the overlap rules, widescreen.
- `references/sound.md`: cues, starting levels, the bundled sounds, the Mix panel, music.
- `vs help review`: every Review Studio command, the tags, the standing rules.
- `references/scars.md`: every mistake that cost a round of notes, by area. Read the area before working in it.
- `references/costs.md`: what things cost, from real runs.
