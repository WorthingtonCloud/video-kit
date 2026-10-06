# Scars: each one cost a round of notes

From two reels (a 58 s lab reel, v1→v22, and a product reel, Sep 27–29, 2026). Read before the first cut.

## Story and words

- 🔑 **The cold-viewer test is the finish line:** someone who has never seen the thing watches and is asked "what's this
  for?". Their reaction outranks your frame checks. A reel that bragged about the agent, then showed a website, failed it. ‹human: a stranger's reaction›
- 🔑 **Literal beats metaphor.** A well (for memory) and a set of keys failed on cold viewers; an animated diagram of the
  real thing landed. The maker's lore is load-bearing for them and invisible to a stranger. ‹human: a stranger's reaction›
- 🔑 **Words need time** (two viewers on one cut: "words just flying across the screen"). 22 titles plus scene words in
  73 s read as "I'd read the top and miss the bottom"; 13 titles of ≥ ~4 s each worked. One reading zone at a time. ‹test: regression/fast-text-label, regression/two-zones-title›
- ⚠️ A line that dates itself ("155 days") or says nothing ("The models.") comes out. ‹human: what a line says›
- 🔑 **The closing line is spent once:** the site's homepage headline WAS the closing line, and showing that page
  mid-reel spent the ending. `reel.json → "never"` stops it. ‹test: regression/never-page›

## Music

- 🔑 **One track, straight through, full volume, fade at the end.** Cutting to silence for a twist, reprising the drop,
  and a muffled dip all failed. Drama comes from the picture. ‹human: the ear›
- 🚨 **`vs beats`'s first hit can be a pickup, not the drop** (7.89 s vs the real 7.67 s kick): the wrong phase put the
  final hit between beats. Verify on two far-apart strong hits and derive the beat from them. ‹partly: unit/test_voice_and_sound.py · human: confirm the hit by ear›
- ⚠️ **A beat tool's single number can be wrong**: one called a grid half a beat late; per band it sat on the kick.
  Measure the bands, trust the ear. ‹human: the ear›
- 🔑 **The ending that landed:** the song as-is to the end; the tile, the point (a strong downbeat), the name and the
  address each on a beat (`endcard.word_b` / `url_b`); then fade the last phrase ~1.3 s. A dead stop and an invented
  ring-out both failed. ‹human: the feel (the end card's beats are settings: word_b, url_b)›
- 🚨 **An end card's beats can run past the card:** `word_b: 2` / `url_b: 4` count beats after the point lands (2 beats
  in), so they need ~6 beats plus reading time; the video-kit reel's 3.5 s card at 0.63 s beats ended before its address
  came round, so it never showed through three approved cuts. The end card now pulls both onto earlier beats when the card
  is short (`endcard.hold`, default 1.2 s for the address), and vs inspect's `never-seen` (error) catches any words that
  never reach the screen; `fast-text` catches words that arrive too close to the video's end. ‹test: regression/endcard-url-late›
- ⚠️ Replayed intro bars were heard as a repeat; replay whole bars BEFORE the build so the song keeps one build, one drop. ‹human: the ear›

## Picture

- 🚨 **Blacks must match** (cards read gray from mixed color ranges on an ffmpeg join, measured 11 → 26). One HyperFrames
  render removed the join; draw on the target site's own ground color; `vs qa` measures every segment's corner. ‹guard: vs qa (blacks per segment, after a render)›
- 🔑 **Emphasis hangs off the word, sized in em, never a measured width.** The font loads AFTER the runtime, so a width
  read at build time is the fallback font's: a marker came up short and a check mark sat on its word. The build measures
  with the real font and warns. ‹guard: vs build (measures the marks with the real font and warns)›
- ⚠️ **A reflection must follow the surface's tilt** ("it appears on one side, goes away, then appears on the other"):
  the glare is computed from the page's sway and every hand-off turn, as if one light is fixed in the room. ‹human: the eye›
- ⚠️ **Repeating rings read as "a bit much"**: one ring per moment. A pulse grows away from its neighbor, ≤ 1.08×. ‹human: taste›
- ⚠️ **A page on screen before its slot is a black rectangle** unless its video plays early: clips run from 0.4 s before
  their cut to 0.45 s after. `vs qa` flags big pure-black patches near a cut. ‹guard: vs qa (black patches near a cut)›
- ⚠️ **Lines that start on a card draw OVER it**; flowing data needs a head, a glow, a tail and a steady stream to read on
  a phone. ‹human: the eye›
- 🔑 **The collage is never frames of this reel**: every tile a different source, covers the reel hasn't shown, never the
  closing-line page, no bylines. `vs collage` refuses repeats, the reel's own output, and `never` pages. ‹guard: vs collage and vs build (repeats, the reel's own frames, never pages)›
- ⚠️ **"The circle looks tall" was the labels, not the circle** (measured 150 × 150): ring labels short, on their ring. ‹human: measure a shape before fixing it›
- ⚠️ **A logo beside a wordmark read as a letter**: the mark in its own app-icon tile, above the name; the name arrives
  after the mark lands. ‹human: the eye›
- ⚠️ **A grid that misses a tile reads as a mistake**: nine tiles, a third of a beat apart, all landed with time to hold. ‹guard: vs build (warns on an unfilled grid)›
- 🔑 **The `over` card dims what it lands on, and only a collage brightens back for its collapse**: a scene with words
  stays dim, or its words fight the card's (the reel template's sources under "This video…" for 0.6 s, Oct 1, 2026).
  ‹test: regression/over-dims-words›
- 🔑 **Text is drawn in code, never by a video model.** Paid shots are textless mood only. ‹human: what to ask a model for›

## Generation

- ⚠️ **Seedance doesn't reliably obey the prompt** (asked for a sine wave, drew a flatline; it was kept). QA every take. ‹human: QA every take (vs qa --clip)›
- ⚠️ **Higgsfield:** no spend API, auto-reload, no cap; estimate from the token formula (5 s at 480p ≈ $1.03, 720p ≈
  $2.31). Its firewall rejects Python's default user agent (`vs gen` sends curl's). Input images must be public URLs:
  `vs gen` hosts them on kie.ai first (they leave the machine). ‹partly: unit/test_vendors_faked.py, unit/test_commands.py · human: the vendor's bill›
- ⚠️ **Suno on kie.ai wants the model NESTED** (`ai-music-api/generate` outside, `V6` inside); a top-level `V6` is a 422. ‹test: unit/test_vendors_faked.py›
- ⚠️ **Long paid jobs print every poll**, so silence means something; a failed poll is "unknown", never "done". Never
  re-submit because the log went quiet: check the vendor's dashboard first. ‹partly: unit/test_vendors_faked.py · human: the vendor's dashboard before any re-submit›

## Recording and the renderer

- ⚠️ **Record pages at phone size for vertical** (390 wide @3x) and scroll the path once before recording (scroll
  animations otherwise show half-built). Hide chat launchers and cookie banners (`hide`). Never record a byline. ‹human: what a page shows (record.mjs sizes and scrolls it)›
- ⚠️ **A remote font `@import` inside a file:// page can hang forever**: `vs fonts` downloads it once into the library. ‹guard: vs fonts (downloads once into the library)›
- 🚨 **HyperFrames reorders separate scripts**: a runtime in its own file ran before its data and painted 27 black
  frames. The build inlines data + runtime + registration in ONE script. `hyperframes check` catches runtime errors. ‹test: integration/test_fixtures.py›
- ⚠️ **GSAP `fromTo` paints its start state at load**: entrances need that; "flash on, then fade" layers must not
  (`immediateRender: false`). ‹human: a rule for whoever writes a scene›
- ⚠️ **HyperFrames rules that bit:** media needs static `data-start`/`data-duration`; fonts need a local `@font-face`;
  never tween `letterSpacing` or `left`; scale SVG with `svgOrigin`; telemetry is on by default (`vs build` turns it
  off); `snapshot` calls Gemini if `GEMINI_API_KEY` is set (`--describe false`). ‹guard: vs build (HyperFrames' lint; telemetry off)›
- ⚠️ `ffmpeg tile` over mixed pixel formats fails (`vs qa` normalizes each cell first). ‹guard: vs qa (normalizes each cell)›

## Checks

- 🚨 **A check that looks at nothing passes.** The overlap audit once added up segment lengths from `secs`, so on a
  beat-timed reel it checked zero frames and printed "no overlaps" (`vs mix` crashed on the same file). Fixed in 1.0.1:
  the audit takes its times from the built composition and says how many moments it checked; the mix times effects
  the way the build does. Read the "checked N moments" line, not just the verdict ("no findings" / "no errors" since vNext). ‹test: regression/beat-reel-zero-frames›
- ⚠️ **A label with a halo isn't crossed by the line under it**: the hub's ring labels sit ON their ring, a halo in
  the ground color cutting it around each letter, and the ring runs on between the words. By design (Oct 1, 2026);
  `vs inspect` knows. ‹test: regression/haloed-ring-label›
- 🚨 **`vs snap` showed shot panels wrong:** the page's timeline never moves its `<video>`s (HyperFrames does that only
  while rendering), so a floating recording sat black or on a stale frame, and the checker reported five false
  problems in them (video-kit-fusion v1, Oct 5, 2026). Snap now seeks each video to its time and waits for the frame;
  one it can't confirm is named in a ⚠ line (and on the sheet): judge that panel from a render. ‹test: regression/stale-shot-panel›
