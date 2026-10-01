# Scars: each one cost a round of notes

From the first two explainers (Sep 30 and Oct 1, 2026). Read the area before working in it.

## Voice

- 🚨 **ElevenLabs' free plan can't use library voices over the API** (HTTP 402 `paid_plan_required`). A paid plan can.
- 🔑 **`eleven_v4` is the lively model**: bracketed tags direct it and aren't spoken; no SSML `<break>`; only stability and
  similarity. Takes of the same text vary ~10% in length: never hard-code a time, re-run `vs plan`.
- 🔑 **Check every take by transcription** (`vs check-take`): the first one said "fell to 12" for "fell twelve percent".
- 🚨 **`eleven_v4` performs a described sound instead of saying it**: "clears its throat" came back as an "ahem" on two
  takes, and the words were missing. Never write a vocal action unless the sound is the point.
- ⚠️ **ElevenLabs' history logs a call a few seconds late**: read at once, it reports the PREVIOUS call's cost.
  `narrate.py` waits for its own entry.
- ⚠️ **A splice must cut AFTER the previous act's last word** (the first cut clipped "generously"); `vs voicebed` does,
  and prints the level across the join. A re-recorded act from the middle keeps the later acts.
- 🔑 **Two library voices can share a name**: always the voice ID.

## Plan and titles

- 🚨 **A word spec that matches an EARLIER word ends a title before it starts, and the title never leaves the screen**
  ("One" hit "In one big trial"; a stat sat over every scene to the end). `vs plan` refuses it now; use `"One#2"` or
  `"act:word"`.

## Picture

- 🔑 **29 overlaps in one video, none visible in still-frame QA**, all found by `vs audit`: a bar grew under its number;
  dashed links and red X's crossed labels; a mover parked on a card's words; a stamp covered a grade; a page showed
  through a see-through tag; faded cards went see-through; a name sat across its own ring.
- 🚨 **Text hanging off its own card was invisible to the audit** until `spills` checked every word against its nearest
  painted box. The same pass found a number off its panel and a label on a thin dashed line the audit couldn't see (a
  thin shape fell under the area threshold; only the top border counted). Each check was proven by planting the flaw.
- ⚠️ **The audit's own traps:** an SVG `<line>` reports a default black fill (it's a stroke); a label on its own solid
  card is fine; an outline box matters only at its border; text clipped by an `overflow:hidden` box still counts.
- 🚨 **A scene's own labels are not in the build's safe-zone check** (it checks titles). A first cut shipped four panel
  kickers under the phone's status bar. `vs audit` reports `phone-safe` in seconds; `vs qa` scans four frames a second
  after a render. A word crossing the edge as it flies in or out (under a second) may stay.
- 🚨 **A vertical scene is drawn at full size** (1 unit = 1 px, design y 0 is 28 px above the frame). Planning at 0.85
  scale put every kicker under the status bar and 900-wide panels in the side crop: 30 hits after a 4-minute render.
- 🔑 **A ring grown from the middle of words crosses them** (bells on "ROUND 1", "DRAW"): `exRing2` starts outside. A
  stamp gets a punch, not a ring.
- 🚨 **GSAP `svgOrigin` + x/y + a scale change on an SVG `<g>` drifts** (`smoothOrigin`): 15 of "twenty people" never
  landed, off a vertical frame, so nobody noticed for three versions. `smoothOrigin: false`.
- ⚠️ **HyperFrames' lint refuses tweening `left`/`top`**: move a wrapper's `x`.
- ⚠️ **Widescreen:** a scene pinned right leaves half the frame empty in an explainer (titles are sparse) → the
  centered-until-a-title glide. A photo's box shows its sides on a wide frame → fades. An exit sized for vertical stops
  in plain sight → `EXIT`.

## Build and checks

- 🚨 **A `$` in scene code was rewritten by the build**: the scenes were inlined with a string replace, which reads `$$`
  as "one dollar sign", so "HEAR IT $$" rendered as "HEAR IT $" in an approved video (found Oct 1, 2026). The build
  inlines with a function now; nothing in scene code is special.
- ⚠️ **Puppeteer: never return the timeline from `evaluate`** (`tl.seek` returns it; serializing it hangs); same for
  `document.fonts.ready`. Wrap them: `{ tl.seek(t); }`.
- 🔑 **Snapshots are repeatable but not perfectly:** the same build re-snapped differs by 1–2 brightness levels on text
  edges and up to ~13 on a transition. `vs compare` reports it; treat max ≤ 2 as noise, and look at anything larger.
- ⚠️ **zsh aborts a chain on an unmatched glob** (`ls a*.mp3 && next` never runs `next`), and **doesn't split
  `$VAR` into words**: call `vs` by its full path every time.

## Sound

- ⚠️ **ElevenLabs sound effects:** 11 credits a second; the "single click" came back as three; every file starts with a
  different amount of silence (the mixer aligns by the attack); loudness varies ~20 dB between files (it normalizes).
- 🚨 **A generated sound can come back nearly silent** (two "stamps" at -55 and -49 dBFS). `vs sfx` and `vs ingest`
  measure every sound and flag it; layer it over a thud rather than normalizing noise up.
- ⚠️ **Suno on kie.ai:** the model is nested (`ai-music-api/generate` outside, `V6` inside); `duration: 180` is honored;
  an `audio_url` once served a truncated file (the `stream_audio_url` had all of it).
- ⚠️ **A busy stretch gets fewer sounds, not quieter ones**: 154 effects (38 ticks) was too many for 2:49.
