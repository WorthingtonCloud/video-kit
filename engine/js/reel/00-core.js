// The reel, as one HyperFrames composition. build.mjs writes index.html (the styles, the media tags, and the reel's
// data with every time already worked out) and inlines this file after the data; it turns that data into the DOM and
// ONE paused GSAP timeline.
// Everything is a pure function of time: seeded randomness, no Math.random, no Date.now, nothing async. The renderer
// seeks frames in any order across several workers, so a frame must never depend on the one before it.
//
// v19, the motion pass: same story, words, cut points and music as v18; the picture moves. A camera rig that punches
// on the drum hits, scenes built in 3D, segments that hand off to each other (carousel, flip, fly-through, drop), a
// collage that assembles as a 3D wall and collapses into the red point, and one emphasis move per key word.
// Words still hold as long as they did: all the extra motion is on the picture, never on reading time.
//
// Scenes are drawn in a 1080-wide design space (content in y 100..1300, centered on 540,700), then fitted: high up
// on a vertical video (titles live below), on the right of a widescreen one (titles live on the left).
(() => {
  const R = window.REEL,
    [W, H] = R.size,
    LAND = W > H,
    P = R.palette,
    B = R.beat,
    END = R.end;
  const FIN = { grain: 0.07, vignette: true, texture: "dots", ...(R.finish || {}) };
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const NS = "http://www.w3.org/2000/svg";
  const svg = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const div = (cls, parent, html = "", style = "") => {
    const d = document.createElement("div");
    d.className = cls;
    if (html) d.innerHTML = html;
    if (style) d.style.cssText = style;
    parent.appendChild(d);
    return d;
  };
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const easeOut = (x) => 1 - Math.pow(1 - clamp(x), 3);
  const easeInOut = (x) => {
    x = clamp(x);
    return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  };
  function mulberry32(a) {
    return () => {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const tl = gsap.timeline({ paused: true });
  const ticks = []; // per-frame work: (t) => void
  const IR = { immediateRender: false }; // later tweens must not paint their start state at load
  const TP = { transformPerspective: 1800 };
  const camrig = $("#camrig"),
    fx = $("#fx");

