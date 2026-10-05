# Scars: each one cost a round of notes

From the first two explainers (Sep 30 and Oct 1, 2026). Read the area before working in it.

## Voice

- 🚨 **ElevenLabs' free plan can't use library voices over the API** (HTTP 402 `paid_plan_required`). A paid plan can. ‹human: the vendor's plan, not the kit's code›
- 🔑 **`eleven_v4` is the lively model**: bracketed tags direct it and aren't spoken; no SSML `<break>`; only stability and
  similarity. Takes of the same text vary ~10% in length: never hard-code a time, re-run `vs plan`. ‹human: how a take sounds (vs plan re-times whatever its length)›
- 🔑 **Check every take by transcription** (`vs check-take`): the first one said "fell to 12" for "fell twelve percent". ‹human: whether a misheard word changes the meaning (vs check-take lists them)›
- 🚨 **`eleven_v4` performs a described sound instead of saying it**: "clears its throat" came back as an "ahem" on two
  takes, and the words were missing. Never write a vocal action unless the sound is the point. ‹test: regression/vocal-action-in-narration›
- ⚠️ **ElevenLabs' history logs a call a few seconds late**: read at once, it reports the PREVIOUS call's cost.
  `narrate.py` waits for its own entry. ‹test: unit/test_vendors_faked.py›
- ⚠️ **A splice must cut AFTER the previous act's last word** (the first cut clipped "generously"); `vs voicebed` does,
  and prints the level across the join. A re-recorded act from the middle keeps the later acts. ‹test: unit/test_voice_and_sound.py›
- 🚨 **…and BEFORE the replaced act's first word, measured in the audio**: ElevenLabs' word timings ran ~0.2 s late, so
  "0.2 s after the last word" kept "Pic-" of the old "Picture" and the new take said it again (a repeat the reviewer
  heard). `vs voicebed` now cuts at the end of the pause it finds in the base, and resumes at the start of the next one. ‹test: unit/test_voice_and_sound.py›
- 🔑 **Two library voices can share a name**: always the voice ID. ‹test: regression/voice-name-not-id›

## Plan and titles

- 🚨 **A word spec that matches an EARLIER word ends a title before it starts, and the title never leaves the screen**
  ("One" hit "In one big trial"; a stat sat over every scene to the end). `vs plan` refuses it now; use `"One#2"` or
  `"act:word"`. ‹test: regression/early-word-spec›
- ⚠️ **A cue's bare word said twice in its act fires on the first one**: "job" hit "doing a job" a line early, so a
  parody ad's punchline landed too soon (Oct 2, 2026). `vs plan` warns with every time it's said; point at the later
  one with `"job#2"`. ‹test: regression/cue-word-twice›
- ⚠️ **A payoff that arrives late in its scene gets cut off**: punchlines got ~0.3 s before the next scene (a parody
  ad, before v1), a payoff 0.8 s (the Jev explainer, v1). vs inspect's `cut-short` warns when words arrive
  mid-scene and the cut takes them before they can be read. ‹guard: vs inspect cut-short (words; a picture's payoff is still your eyes)›

## Picture

- 🔑 **29 overlaps in one video, none visible in still-frame QA**, all found by `vs audit`: a bar grew under its number;
  dashed links and red X's crossed labels; a mover parked on a card's words; a stamp covered a grade; a page showed
  through a see-through tag; faded cards went see-through; a name sat across its own ring. ‹partly: regression/line-through-ring · human: the other kinds are vs inspect's everyday work›
- 🚨 **Text hanging off its own card was invisible to the audit** until `spills` checked every word against its nearest
  painted box. The same pass found a number off its panel and a label on a thin dashed line the audit couldn't see (a
  thin shape fell under the area threshold; only the top border counted). Each check was proven by planting the flaw. ‹test: regression/spills-own-card, regression/thin-marker-through-label›
- ⚠️ **The audit's own traps:** an SVG `<line>` reports a default black fill (it's a stroke); a label on its own solid
  card is fine; an outline box matters only at its border; text clipped by an `overflow:hidden` box still counts. ‹test: regression/no-false-alarms, regression/scrolled-under-header›
- 🚨 **A scene's own labels are not in the build's safe-zone check** (it checks titles). A first cut shipped four panel
  kickers under the phone's status bar. `vs inspect` (once `vs audit`) reports `phone-safe` in seconds; `vs qa` scans four frames a second
  after a render. A word crossing the edge as it flies in or out (under a second) may stay. ‹test: regression/phone-safe-kicker›
- 🚨 **A vertical scene is drawn at full size** (1 unit = 1 px, design y 0 is 28 px above the frame). Planning at 0.85
  scale put every kicker under the status bar and 900-wide panels in the side crop: 30 hits after a 4-minute render. ‹partly: regression/phone-safe-kicker · human: plan the layout at full size›
- 🔑 **A ring grown from the middle of words crosses them** (bells on "ROUND 1", "DRAW"): `exRing2` starts outside. A
  stamp gets a punch, not a ring. ‹test: regression/line-through-ring›
- 🚨 **GSAP `svgOrigin` + x/y + a scale change on an SVG `<g>` drifts** (`smoothOrigin`): 15 of "twenty people" never
  landed, off a vertical frame, so nobody noticed for three versions. `smoothOrigin: false`. ‹partly: regression/offscreen-parked · human: whether it's parked there by design›
- 🚨 **Small text and thin lines in a slowly turning panel flickered** (sharp, soft, sharp, soft on alternate frames):
  the browser redraws them a little differently at each angle. Four approved videos carried it; a reviewer saw it ("the icons flicker"). Drawing at twice the size made it worse. `vs build` now draws two frames per frame and
  averages them (`render.blend`, ~2× the render time), and `vs qa` warns `shimmer`. Keep the tilt. ‹test: unit/test_qa_findings.py›
- ⚠️ **A chat turn scrolled up out of its window read as "parked off the frame"** (24 warnings, none real): what a
  clipping box hides doesn't count; a frame-sized box isn't a window. ‹test: regression/clipped-not-parked, regression/offscreen-parked›
- ⚠️ **Frame one was solid black** (entrances timed `seg.t0 - 0.35` clamp to 0): the feed's preview. `vs inspect` warns
  `blank-start`. ‹test: unit/deadair.test.mjs›
- ⚠️ **HyperFrames' lint refuses tweening `left`/`top`**: move a wrapper's `x`. ‹guard: vs build (HyperFrames' lint)›
- ⚠️ **Widescreen:** a scene pinned right leaves half the frame empty in an explainer (titles are sparse) → the
  centered-until-a-title glide. A photo's box shows its sides on a wide frame → fades. An exit sized for vertical stops
  in plain sight → `EXIT`. ‹partly: regression/offscreen-parked · human: the layout's balance›

## Build and checks

- 🚨 **A tween given an object or NaN where a number goes does nothing, silently**: `exPath()` returns `{x, y}`, used as
  a number, so the chat stack never scrolled (contextual-ui v1, Oct 2, 2026; only stills showed it, since a move that
  never happens fights nothing). Under vs inspect every tween's values are checked as it's made; `dead-tween` (an error)
  names the element and the line. ‹test: regression/nan-tween›

- 🚨 **A `$` in scene code was rewritten by the build**: the scenes were inlined with a string replace, which reads `$$`
  as "one dollar sign", so "HEAR IT $$" rendered as "HEAR IT $" in an approved video (found Oct 1, 2026). The build
  inlines with a function now; nothing in scene code is special. ‹test: regression/dollars-in-scene-code›
- ⚠️ **A rare browser stall sat out the 60 s protocol timeout** (three times on Oct 1, 2026: vs inspect twice, vs build's
  safe-zone check once), and puppeteer's stack never named our step. Every browser call now names its step
  (`step()` in `lib/browser.mjs`), and the wait for fonts gives up after 10 s, says so and measures with what loaded
  (an unsettled `document.fonts.ready` is the suspect). If it comes back, the output says where. ‹guard: lib/browser.mjs step() + the bounded font wait›
- ⚠️ **Puppeteer: never return the timeline from `evaluate`** (`tl.seek` returns it; serializing it hangs); same for
  `document.fonts.ready`. Wrap them: `{ tl.seek(t); }`. ‹human: a rule for whoever writes a check (the kit's own follow it)›
- 🔑 **Snapshots are repeatable but not perfectly:** the same build re-snapped differs by 1–2 brightness levels on text
  edges and up to ~13 on a transition. `vs compare` reports it; treat max ≤ 2 as noise, and look at anything larger. ‹human: reading vs compare's numbers›
- ⚠️ **zsh aborts a chain on an unmatched glob** (`ls a*.mp3 && next` never runs `next`), and **doesn't split
  `$VAR` into words**: call `vs` by its full path every time. ‹human: a shell habit›

- ⚠️ **A send nobody heard:** a leftover `vs review wait` read the human's send and exited into a log nobody watched,
  while the agent sat on a second one. A second watcher now refuses (`--replace` takes over). ‹test: unit/test_review.py›
- ⚠️ **Re-filing finals (a re-render) rewrote the music bed's first win and added a second history line** (spend counted
  twice), three times by hand before the fix. ‹test: unit/test_learn_refile.py›

## Sound

- ⚠️ **ElevenLabs sound effects:** 11 credits a second; the "single click" came back as three; every file starts with a
  different amount of silence (`vs mix` aligns by the attack); loudness varies ~20 dB between files (it normalizes). ‹partly: unit/test_voice_and_sound.py · human: listen to every new sound›
- 🚨 **A generated sound can come back nearly silent** (two "stamps" at -55 and -49 dBFS). `vs sfx` and `vs ingest`
  measure every sound and flag it; layer it over a thud rather than normalizing noise up. ‹test: unit/test_voice_and_sound.py›
- ⚠️ **Suno on kie.ai:** the model is nested (`ai-music-api/generate` outside, `V6` inside); `duration: 180` is honored;
  an `audio_url` once served a truncated file (the `stream_audio_url` had all of it). ‹partly: unit/test_vendors_faked.py · human: a truncated download (music.py tries both links)›
- 🚨 **A re-mix wrote through a linked take into the file it pointed at** (Oct 1, 2026: a scratch copy of Socrates
  linked its renders to save space; `vs mix` overwrote the approved `v3-take2.mp4` through the link. Same bytes, as the
  mix is deterministic, so nothing was lost). `vs mix` now replaces a link instead. Copy, don't link, when a scratch
  copy will be mixed. ‹test: integration/test_fixtures.py›
- ⚠️ **A busy stretch gets fewer sounds, not quieter ones**: 154 effects (38 ticks) was too many for 2:49. ‹partly: unit/test_qa_findings.py · human: which sounds to keep›
