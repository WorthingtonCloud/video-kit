# Writing scenes

A project's `scenes.js` holds only its own scenes (and any prop only it needs). The engine inlines, in order: the scene
library (`engine/js/scenes/base.js`, `icons.js`, `props.js`), the studio's promoted pieces (`library/scenes/*.js`), the
project's `scenes.js`, then `layout.js` (the widescreen wrapper). Everything shares the renderer's helpers: `tl` (the one
GSAP timeline), `ticks` (per-frame work), `svg`, `div`, `tw3`, `punch` (a camera push on a hit), `easeOut`, `easeInOut`,
`clamp`, `IR` (`{immediateRender: false}`), `TP`, `mulberry32` (seeded random), `P` (the palette), `W`, `H`, `LAND`.

```js
Object.assign(SCENES, {
  intro(stage, seg) {                       // seg.t0 / seg.t1: the segment's start and end, in seconds
    const c = R.scenes.intro.cues;          // each cue = the absolute time of a word (plan.json → segments → cues)
    …
    return "own-push";                      // the scene moves its own camera (exRig); the renderer adds none
  },
});
```

## Rules that are not negotiable

- **Everything is a pure function of time.** Seeded randomness only, no `Math.random`, no `Date.now`, nothing async:
  the renderer seeks frames in any order across several workers.
- **A first tween on a property paints its start state at load** (an entrance: hidden until its word). Every later tween
  on the same property passes `IR`, or it shows from frame one. A "flash on, then fade" layer must have `IR` too.
- **The design space is 1080 × 1400.** On a vertical cut a scene is drawn at full size (1 unit = 1 px, design y 0 sits
  28 px above the frame): keep words in x 120–960 and y ≥ 220, panels 860 wide at x 110 (a 3D tilt widens them), and
  content above y ≈ 1130 (the titles live below). A scene whose kicker sits near the top can ride lower on the vertical
  cut only: `exRideLower(["intro"], 80)` at the end of the file. `vs audit` reports `phone-safe` hits before any render.
- **Exits must leave the frame in both shapes:** multiply every exit distance by `EXIT` (2 on a widescreen cut).
- **Never tween `left`/`top`** (whole-pixel snapping stutters; the HyperFrames lint refuses it): move a wrapper's `x`.
  Never tween `letterSpacing`. Scale SVG with `svgOrigin` (and `smoothOrigin: false` if you also move it with x/y).
- **One accent color, one meaning per video**, stated in SCRIPT.md (the AI; the placebo; the money). Red elsewhere is
  only a stamp or a strike.
- **One reading zone at a time:** a scene with words gets no title; a titled moment keeps the scene's words quiet.

## The overlap rules (`vs audit` enforces them)

- Every tag, chip and label box is SOLID (no rgba backgrounds): a line or a page must never show through words.
- A bar or a moving thing stops BESIDE its number or label, never under or over it.
- A mover docks on a card's inner corner, not its center.
- A stamp or sticker lands beside the words it comments on, never on them; it gets a punch, not a ring.
- A connector runs along the edges or under solid cards, never through a label.
- A name under an icon sits below the icon's ring, not across it; a line starts below the name.
- Dim a whole scene with ONE scrim on top, never by fading each card (faded cards go see-through).
- A scrolling page gets a solid header strip; don't scroll text under a header (the audit counts clipped text as there).
- A ring around words starts OUTSIDE them (`exRing2`), never from their middle.

## The library

**The look (CSS classes):** `ex-p` a panel (near-square, lit from above) · `ex-k` a mono kicker (`.red`, `.green`) ·
`ex-t` big text · `ex-m` a mono number · `ex-chip` a solid tag (`.red`, `.green`) · `ex-blk` a block row · `ex-bar` a bar ·
`ex-spot` a soft light · `ex-glow` an accent glow · `ex-big` a centered headline · `ex-clip` a clipping box.

**base.js**
- `exLight(stage, x, y, r, seg, n, seed)` one soft spotlight, breathing, with dust in it: the room.
- `exRig(stage, seg, from, to, origin)` a 3D rig that turns slowly across the segment (return `"own-push"`).
- `exIn(el, t, from, dur, ease)` arrive from a state · `exPop(el, t, s, dur, ease)` pop in · `exFade(el, t, to, dur, from)`.
- `exDraw(path, t, dur)` a stroke that draws itself · `exCount(el, t0, dur, a, b, fmt)` a number that counts.
- `exPath(keys)` a mover along keyed points · `exPoint(parent, r)` the accent point with its glow (the motif) ·
  `exAt(el, x, y, s)` place it · `exRing(parent, t0, x, y, r1, dur, col)` a ring from a point.
- `exIcon(parent, name, size, x, y)` a line icon: `person clock mail pen eye lock ticket code logs team sheet chair mag
  car bug q coin eye2` (white strokes, one detail in the accent). Add yours: `Object.assign(GLX, { name: '<path …/>' })`.
- `exRideLower(names, dy)` vertical cut only · `exRGB(hex)` "232,64,44" for an rgba() · `EXIT` · `GREEN`.

**props.js** (promoted from finished videos)
- `exStamp(el, t, rot, big)` a stamp slams down and the camera feels it · `exSlam(el, t, from, dur)` slam in from blur.
- `exStrike(el, t, col)` a strike line across an element · `exRing2(parent, t0, x, y, r0, r1, dur, col)` a ring that
  starts outside what it surrounds · `exBell(parent, t, x, y, r0)` two rings and a punch: a boxing bell.
- `exRound(parent, "ROUND 1", "THE ANSWERS", t, t2, t3)` slams in, rings, shrinks to a corner chip.
- `exKeys([[t, a, b…]…])` eased keyframes · `exPhoto(stage, img, [[t, u, v, scale]…], seg, box)` a photo with its own
  camera that never shows an edge; `.ov` rides with the picture (a line on it, a point).
- `exSvgBox(parent, x, y, size, svgInner)` an SVG drawing in a 200-unit box.

**Promoting a piece.** When a helper in a project's `scenes.js` would serve another video (a prop, a move, an icon), move
it to the studio's `library/scenes/<name>.js` (one file per piece, with a comment saying what it is and where it came
from) and delete it from the project. Every later video gets it. `vs learn` lists the candidates.

## Widescreen

`vs plan --wide` makes the same plan 1920 × 1080 with the same times. The words live on the left, so `layout.js` keeps
each scene centered and slides it right only while a title is up (arriving as the title lands, back as it leaves; short
gaps and titles near a cut hold the side). A photo's box shows its sides on a wide frame: `exPhoto` fades them. LOOK at
every scene in the wide cut: nothing measures an exit that stops in plain sight.

## The worked example

`examples/meeting-explainer/`: ten scenes (a rollout dashboard, an inbox, a web of people, a courier, a hundred projects
pouring into one foundation, an agent that stays when a person leaves…), `plan.json` with 13 titles, `cues.py` with 95
sounds. Copy its patterns, not its scenes.
