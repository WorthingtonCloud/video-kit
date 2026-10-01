# Scars: each one cost a round of notes

From two reels (a 58 s lab reel, v1→v22, and a product reel, Sep 27–29, 2026). Read before the first cut.

## Story and words

- 🔑 **The cold-viewer test is the finish line:** someone who has never seen the thing watches and is asked "what's this
  for?". Their reaction outranks your frame checks. A reel that bragged about the agent, then showed a website, failed it.
- 🔑 **Literal beats metaphor.** A well (for memory) and a set of keys failed on cold viewers; an animated diagram of the
  real thing landed. The maker's lore is load-bearing for them and invisible to a stranger.
- 🔑 **Words need time** (two viewers on one cut: "words just flying across the screen"). 22 titles plus scene words in
  73 s read as "I'd read the top and miss the bottom"; 13 titles of ≥ ~4 s each worked. One reading zone at a time.
- ⚠️ A line that dates itself ("155 days") or says nothing ("The models.") comes out.
- 🔑 **The closing line is spent once:** the site's homepage headline WAS the closing line, and showing that page
  mid-reel spent the ending. `reel.json → "never"` stops it.

## Music

- 🔑 **One track, straight through, full volume, fade at the end.** Cutting to silence for a twist, reprising the drop,
  and a muffled dip all failed. Drama comes from the picture.
- 🚨 **`vs beats`'s first hit can be a pickup, not the drop** (7.89 s vs the real 7.67 s kick): the wrong phase put the
  final hit between beats. Verify on two far-apart strong hits and derive the beat from them.
- ⚠️ **A beat tool's single number can be wrong**: one called a grid half a beat late; per band it sat on the kick.
  Measure the bands, trust the ear.
- 🔑 **The ending that landed:** the song as-is to the end; the tile, the point (a strong downbeat), the name and the
  address each on a beat (`endcard.word_b` / `url_b`); then fade the last phrase ~1.3 s. A dead stop and an invented
  ring-out both failed.
- ⚠️ Replayed intro bars were heard as a repeat; replay whole bars BEFORE the build so the song keeps one build, one drop.

## Picture

- 🚨 **Blacks must match** (cards read gray from mixed color ranges on an ffmpeg join, measured 11 → 26). One HyperFrames
  render removed the join; draw on the target site's own ground color; `vs qa` measures every segment's corner.
- 🔑 **Emphasis hangs off the word, sized in em, never a measured width.** The font loads AFTER the runtime, so a width
  read at build time is the fallback font's: a marker came up short and a check mark sat on its word. The build measures
  with the real font and warns.
- ⚠️ **A reflection must follow the surface's tilt** ("it appears on one side, goes away, then appears on the other"):
  the glare is computed from the page's sway and every hand-off turn, as if one light is fixed in the room.
- ⚠️ **Repeating rings read as "a bit much"**: one ring per moment. A pulse grows away from its neighbor, ≤ 1.08×.
- ⚠️ **A page on screen before its slot is a black rectangle** unless its video plays early: clips run from 0.4 s before
  their cut to 0.45 s after. `vs qa` flags big pure-black patches near a cut.
- ⚠️ **Lines that start on a card draw OVER it**; flowing data needs a head, a glow, a tail and a steady stream to read on
  a phone.
- 🔑 **The collage is never frames of this reel**: every tile a different source, covers the reel hasn't shown, never the
  closing-line page, no bylines. `vs collage` refuses repeats, the reel's own output, and `never` pages.
- ⚠️ **"The circle looks tall" was the labels, not the circle** (measured 150 × 150): ring labels short, on their ring.
- ⚠️ **A logo beside a wordmark read as a letter**: the mark in its own app-icon tile, above the name; the name arrives
  after the mark lands.
- ⚠️ **A grid that misses a tile reads as a mistake**: nine tiles, a third of a beat apart, all landed with time to hold.
- 🔑 **Text is drawn in code, never by a video model.** Paid shots are textless mood only.

## Generation

- ⚠️ **Seedance doesn't reliably obey the prompt** (asked for a sine wave, drew a flatline; it was kept). QA every take.
- ⚠️ **Higgsfield:** no spend API, auto-reload, no cap; estimate from the token formula (5 s at 480p ≈ $1.03, 720p ≈
  $2.31). Its firewall rejects Python's default user agent (`vs gen` sends curl's). Input images must be public URLs:
  `vs gen` hosts them on kie.ai first (they leave the machine).
- ⚠️ **Suno on kie.ai wants the model NESTED** (`ai-music-api/generate` outside, `V6` inside); a top-level `V6` is a 422.
- ⚠️ **Long paid jobs print every poll**, so silence means something; a failed poll is "unknown", never "done". Never
  re-submit because the log went quiet: check the vendor's dashboard first.

## Recording and the renderer

- ⚠️ **Record pages at phone size for vertical** (390 wide @3x) and scroll the path once before recording (scroll
  animations otherwise show half-built). Hide chat launchers and cookie banners (`hide`). Never record a byline.
- ⚠️ **A remote font `@import` inside a file:// page can hang forever**: `vs fonts` downloads it once into the library.
- 🚨 **HyperFrames reorders separate scripts**: a runtime in its own file ran before its data and painted 27 black
  frames. The build inlines data + runtime + registration in ONE script. `hyperframes check` catches runtime errors.
- ⚠️ **GSAP `fromTo` paints its start state at load**: entrances need that; "flash on, then fade" layers must not
  (`immediateRender: false`).
- ⚠️ **HyperFrames rules that bit:** media needs static `data-start`/`data-duration`; fonts need a local `@font-face`;
  never tween `letterSpacing` or `left`; scale SVG with `svgOrigin`; telemetry is on by default (`vs build` turns it
  off); `snapshot` calls Gemini if `GEMINI_API_KEY` is set (`--describe false`).
- ⚠️ `ffmpeg tile` over mixed pixel formats fails (`vs qa` normalizes each cell first).
