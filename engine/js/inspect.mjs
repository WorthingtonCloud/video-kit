// vs inspect (vs audit is the same step): ONE scrub of the composition that writes two maps.
//   build/elements.json  every named element (js/reel/55-names.js): its segment and scene, what kind of thing it is, its
//                        words, the line of scenes.js that made it, when it's on screen, and its box over time (as
//                        fractions of the frame, kept whenever it moves) — what the review page and qa.py look names up in
//   build/findings.json  every place words and pictures fight, keyed to the elements involved, with a hint:
//     covers          a shape paints OVER words (a reviewer, Sep 30: the email bar grew over "28 h", then it lit up red)
//     line-through    a line or an outline runs through words
//     on-photo        words on a picture with nothing solid behind them
//     low-contrast    words on a shape too close to them in brightness
//     title-on-scene  a title lands on the scene's own drawing
//     straddles       words half on a shape, half off it
//     spills          words run past the edge of their own card ("OTHER TEAM" hung off its box through v3)
//     phone-safe      (vertical cuts) a scene's words where a phone hides them for a second or more: the status bar, the
//                     side crop, the button rail, the caption (Socrates v1, Oct 1, 2026: 30 hits, every scene's kicker)
//     on-text         two sets of words overlap
//     dead-tween      an animation whose value isn't a number (an object, NaN): GSAP skips it silently, the thing
//                     never moves (contextual-ui v1, Oct 2, 2026; 00-core.js checks every tween under inspect)
//     never-seen      words the build made that never reach the screen: timed past their segment's end (the video-kit
//                     reel's end card, Oct 4, 2026: its address was due after the card ended, v6–v8; mapchecks.mjs)
//   warnings (each can be by design: the human confirms or dismisses it in Review Studio):
//     two-zones       a title is up while the scene shows words of its own: one reading zone at a time (the second
//                     reel's v1, Sep 2026: "I'd read the top and miss the bottom")
//     fast-text       words gone before they can be read (js/lib/mapchecks.mjs; thresholds: profile.json → checks)
//     cut-short       words that arrive mid-scene and leave with the cut before they can be read (mapchecks.mjs)
//     offscreen-at-rest  something parked partly off the frame for a second or more (mapchecks.mjs)
//     dead-air        nothing on screen but the backdrop for a stretch (mapchecks.mjs; dead_air_secs)
//     blank-start     the first frame shows nothing but the backdrop: the feed's preview (mapchecks.mjs)
//   and the human's standing rules from Review Studio (js/lib/rules.mjs):
//     keep-clear      something entered a zone a note asked to keep clear (in that note's scene, on its cut)
//     done-changed    a scene the human marked done no longer matches the version it was approved in (its frames, or
//                     its length); done-gone: it isn't in the build at all
//   Every error stops the render until it's fixed or the human dismisses it; warnings don't. Near a cut (the transitions blur
//   and overlap on purpose) words aren't checked, but the elements are still mapped. Needs `vs build --no-render` first.
//   vs inspect [--step 0.15] [--min 0.45] [--from s] [--to s] [--shots]   (--shots: a still per finding, build/qa/findings/)
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { launch, step } from "./lib/browser.mjs";
import { COMP, QA, readTimeline, ELEMENTS, FINDINGS, SOURCES, CONTRACTS } from "./lib/paths.mjs";
import { readRules, keepClear, lockedScenes } from "./lib/rules.mjs";
import { fastText, parked, deadAir, blankStart, neverSeen } from "./lib/mapchecks.mjs";
import { checks } from "./lib/paths.mjs";

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > 0 ? process.argv[i + 1] : d;
};
const STEP = +arg("--step", 0.15),
  MIN = +arg("--min", 0.45),
  SHOTS = process.argv.includes("--shots"),
  FROM = +arg("--from", 0),
  TO = +arg("--to", 1e9);
// the cuts and the length come from the build's timing (build/timeline.json), exactly as the composition was timed.
// Summing reel.json's "secs" read a beat-timed reel's length as NaN, so the audit checked nothing and said "no overlaps"
// (fixed in 1.0.1).
// The size is the composition's too: a project's build can be the other shape from its reel.json (Socrates' comp was the
// widescreen cut while reel.json said vertical), and measuring at the wrong size reads garbage.
const TL = readTimeline(),
  [W, H] = TL.size,
  cuts = TL.segments.map((s) => s.t0),
  END = TL.end;
if (!(END > 0)) {
  console.error(`⛔ the composition's length is ${END}: run vs build --no-render first`);
  process.exit(1);
}

const b = await launch(),
  p = await b.newPage();
// ask the runtime to keep the call stack that made each element (00-core.js): that's how one traces to scenes.js
await p.evaluateOnNewDocument(() => {
  window.__INSPECT = true;
  Error.stackTraceLimit = 40;
});
await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await step("inspect: open the composition", () => p.goto(pathToFileURL(path.resolve(COMP, "index.html")).href, { waitUntil: "load" }));
const settled = await step("inspect: wait for the fonts", () => p.evaluate(async () => {
  const settled = await Promise.race([document.fonts.ready.then(() => true), new Promise((r) => setTimeout(() => r(false), 10000))]);
  const s = document.createElement("style");
  s.textContent = "*{pointer-events:auto !important}";
  document.head.appendChild(s);
  return settled;
}));
if (!settled) console.log("⚠️  the composition's fonts didn't settle in 10 s (a browser stall): measuring with what had loaded");

// every named element, once: what it is, its words, and the stack that made it
const META = await step("inspect: list the named elements", () => p.evaluate(() => {
  const SH = new Set(["circle", "ellipse", "rect", "line", "polyline", "polygon", "path", "text", "image", "use"]);
  const all = window.__names.all();
  window.__inspectEls = all.map((x) => x.el);
  const addrOf = new Map(all.map(({ addr, el }) => [el, addr]));
  const up = (el) => {
    for (let e = el.parentElement; e && e.nodeType === 1; e = e.parentElement) if (addrOf.has(e)) return addrOf.get(e);
    return null;
  };
  const seen = (c) => /rgba?\(/.test(c || "") && !/rgba\([^)]*,\s*0\)/.test(c);
  return all.map(({ addr, el }) => {
    const tag = el.tagName.toLowerCase(),
      text = window.__names.text(el).replace(/\s+/g, " ").trim().slice(0, 80),
      pic = /^(img|video|canvas|image)$/.test(tag) || !!el.querySelector("img,video,canvas");
    const cs = el instanceof SVGElement ? null : getComputedStyle(el),
      box = cs && (seen(cs.backgroundColor) || cs.backgroundImage !== "none" || parseFloat(cs.borderTopWidth) > 0);
    const kind = addr.startsWith("title/")
      ? "title"
      : pic
        ? "picture"
        : text
          ? "text"
          : SH.has(tag)
            ? "shape"
            : box
              ? "box"
              : "group";
    return { addr, named: !el.getAttribute("data-el").startsWith("~"), kind, text, stack: window.__names.made(el), up: up(el) };
  });
}));

// tweens with a value that can't be a number (00-core.js lists them as the composition loads, under inspect): GSAP skips
// them without a word, so the thing never moves and no picture check can tell
const BAD = await step("inspect: list the tweens that can't run", () =>
  p.evaluate(() => (window.__badTweens || []).map((b) => ({ addr: window.__names.addr(b.el), props: b.props, stack: b.stack }))),
);

const hits = [],
  seenAt = []; // [t, [[element index, x0, y0, x1, y1], …], {element index: the part a clipping box lets show}] per moment
let checked = 0;
const nearCut = (t) => cuts.some((c) => t > c - 0.5 && t < c + 0.6),
  C = checks(); // the tunable thresholds (contracts.json, profile.json → checks)
for (let t = Math.max(0.05, FROM); t < Math.min(END, TO); t += STEP) {
  const near = nearCut(t);
  if (!near) checked++;
  const found = near ? [] : await step(`inspect: check the words at ${t.toFixed(2)}s`, () => p.evaluate(
    (t, W, H, Z, Z2) => {
      window.__timelines.main.seek(t, false);
      const alpha = (c) => {
        const m = c.match(/rgba?\(([^)]+)\)/);
        if (!m) return 0;
        const v = m[1].split(",").map(Number);
        return v.length > 3 ? v[3] : 1;
      };
      // how visible: opacity all the way up, and a scene dimmed behind a card (brightness ≤ ~0.3, or blurred past
      // reading: the over transition) is recessive, not words fighting the card's
      const vis = (el) => {
        let o = 1;
        for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
          const cs = getComputedStyle(e);
          if (cs.display === "none" || cs.visibility === "hidden") return 0;
          o *= +cs.opacity;
          if (cs.filter && cs.filter !== "none") {
            const br = cs.filter.match(/brightness\(([\d.]+)\)/),
              bl = cs.filter.match(/blur\(([\d.]+)px\)/);
            if (br) o *= +br[1];
            if (bl && +bl[1] >= 4) return 0;
          }
          if (o < 0.2) return 0;
        }
        return o;
      };
      const skip = (el) => el.closest(".ex-spot,.ex-glow,.ex-mote,.grain,.vignette,#grain,script,style,head");
      const label = (el) => {
        const tt = el.closest("[data-title]");
        if (tt) return "title " + tt.dataset.title;
        const blk = el.closest(".ex-chip,.ex-blk,.ex-k,.ex-t,.ex-m") || el;
        return `"${(blk.textContent || "").trim().replace(/\s+/g, " ").slice(0, 36)}"`;
      };
      const where = (el) => {
        const panel = el.closest(".ex-p"),
          k = panel && panel.querySelector(".ex-k");
        return k ? ` in [${k.textContent.trim().slice(0, 28)}]` : "";
      };
      // words: every visible text node, measured tight
      const texts = [],
        tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n; (n = tw.nextNode()); ) {
        if (!n.textContent.trim()) continue;
        const el = n.parentElement;
        if (!el || skip(el) || vis(el) < 0.3) continue;
        const rg = document.createRange();
        rg.selectNodeContents(n);
        let r = rg.getBoundingClientRect();
        // only what shows: a box that clips (overflow hidden) cuts its words to its own edges, so a page scrolled under
        // its header isn't three sets of words on top of each other (Socrates, Oct 1, 2026)
        for (let e = el; e && e !== document.body; e = e.parentElement) {
          const cs = getComputedStyle(e);
          if (cs.overflowX === "visible" && cs.overflowY === "visible") continue;
          const c = e.getBoundingClientRect(),
            l = Math.max(r.left, c.left),
            rt = Math.min(r.right, c.right),
            tp = Math.max(r.top, c.top),
            bt = Math.min(r.bottom, c.bottom);
          r = { left: l, right: rt, top: tp, bottom: bt, width: Math.max(0, rt - l), height: Math.max(0, bt - tp) };
          if (!r.width || !r.height) break;
        }
        if (r.width < 3 || r.height < 1 || r.right < 0 || r.left > W || r.bottom < 0 || r.top > H) continue;
        texts.push({
          el,
          r,
          label: label(el),
          // [data-group]: one paragraph whose phrases arrive one by one (wrapped spans' boxes overlap; a parody explainer, Oct 5, 2026)
          group: el.closest("[data-title]") || el.closest(".ex-chip,.ex-blk,.ex-k,.ex-t,.ex-m,[data-group]") || el,
        });
      }
      // shapes: svg geometry, and boxes with a visible fill or border, or an image
      const shapes = [];
      document
        .querySelectorAll("rect,circle,ellipse,line,path,polyline,polygon,image,div,img,canvas,video")
        .forEach((el) => {
          if (skip(el)) return;
          const r = el.getBoundingClientRect();
          if (r.width * r.height < 16 || r.width * r.height > 0.35 * W * H) return;
          if (el instanceof SVGElement) {
            if (el.closest("defs,clipPath,mask")) return;
          } else if (!/IMG|CANVAS|VIDEO/.test(el.tagName)) {
            const cs = getComputedStyle(el);
            const fill = alpha(cs.backgroundColor) > 0.05 || cs.backgroundImage !== "none";
            const edge = ["Top", "Right", "Bottom", "Left"].some(
              (d) =>
                parseFloat(cs[`border${d}Width`]) > 0 &&
                alpha(cs[`border${d}Color`]) > 0.05 &&
                cs[`border${d}Style`] !== "none",
            ); // any side: a dashed marker is often one border-left
            if (!fill && !edge) return;
          }
          if (vis(el) < 0.3) return;
          shapes.push({ el, r });
        });
      const inter = (a, b) => {
        const l = Math.max(a.left, b.left),
          r = Math.min(a.right, b.right),
          tp = Math.max(a.top, b.top),
          bt = Math.min(a.bottom, b.bottom);
        return r > l && bt > tp ? { l, r, t: tp, b: bt, a: (r - l) * (bt - tp) } : null;
      };
      const out = [];
      for (const T of texts) {
        const ta = T.r.width * T.r.height;
        for (const S of shapes) {
          if (S.el.contains(T.el) || T.el.contains(S.el) || T.group.contains(S.el)) continue; // its own card, or a mark inside its own chip
          // a thin shape (a rule, a dashed marker) covers little area but still cuts through the words: any crossing counts
          const thin = Math.min(S.r.width, S.r.height) < 8,
            x = inter(T.r, S.r);
          if (!x || (!thin && x.a < 0.12 * ta)) continue;
          // what S paints where it meets the words: a stroke through words always fights; a fill fights when it's
          // opaque and over the words, or under them with too little contrast; a see-through box only at its border
          const cs = getComputedStyle(S.el),
            svgEl = S.el instanceof SVGElement,
            img = /IMG|CANVAS|VIDEO|image/i.test(S.el.tagName);
          let paint = null,
            strokeOnly = false,
            outline = false;
          if (svgEl) {
            const f = cs.fill,
              fa = f === "none" || S.el.tagName.toLowerCase() === "line" ? 0 : alpha(f) * +cs.fillOpacity;
            if (fa > 0.15) paint = f;
            else {
              strokeOnly = true;
              paint = cs.stroke;
            }
            if (strokeOnly && /rect|circle|ellipse/.test(S.el.tagName)) outline = true;
          } else if (!img) {
            if (alpha(cs.backgroundColor) > 0.15) paint = cs.backgroundColor;
            else if (cs.backgroundImage.includes("gradient"))
              paint = (cs.backgroundImage.match(/rgba?\([^)]+\)/) || [null])[0];
            else outline = true;
          }
          if (outline) {
            // only its border counts: skip words wholly inside it (with a margin) or wholly outside
            const m =
                (parseFloat(cs.strokeWidth) ||
                  Math.max(...["Top", "Right", "Bottom", "Left"].map((d) => parseFloat(cs[`border${d}Width`]) || 0)) ||
                  3) /
                  2 +
                3,
              r = S.r,
              q = T.r;
            if (q.left > r.left + m && q.right < r.right - m && q.top > r.top + m && q.bottom < r.bottom - m) continue;
          }
          let over = 0,
            under = 0,
            bare = 0;
          for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9])
            for (const fy of [0.2, 0.5, 0.8]) {
              const st = document.elementsFromPoint(x.l + (x.r - x.l) * fx, x.t + (x.b - x.t) * fy);
              const ti = st.findIndex((e) => e === T.el || T.el.contains(e)),
                si = st.findIndex((e) => e === S.el || S.el.contains(e));
              if (ti < 0 || si < 0) continue;
              if (si < ti) {
                over++;
                continue;
              }
              under++;
              const between = st.slice(ti, si); // the words' own element counts: a solid tag hides what's behind it
              if (
                !between.some((e) => {
                  const c2 = getComputedStyle(e);
                  return (
                    (alpha(c2.backgroundColor) > 0.85 ||
                      (c2.backgroundImage.includes("gradient") &&
                        !/rgba\([^)]*, 0(\.\d+)?\)/.test(c2.backgroundImage))) &&
                    +c2.opacity > 0.85 &&
                    !e.contains(S.el)
                  );
                })
              )
                bare++;
            }
          const lum = (c) => {
            const m = (c || "").match(/rgba?\(([^)]+)\)/);
            if (!m) return null;
            const v = m[1]
              .split(",")
              .slice(0, 3)
              .map((x) => {
                x = +x / 255;
                return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
              });
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
          };
          const lt = lum(getComputedStyle(T.el).color),
            ls = lum(paint);
          const contrast = lt == null || ls == null ? 1 : (Math.max(lt, ls) + 0.05) / (Math.min(lt, ls) + 0.05);
          const need = strokeOnly ? 1 : 2,
            frac = x.a / ta,
            isTitle = !!T.el.closest("[data-title]");
          let kind = null;
          // a label with a halo (an SVG text stroked in the ground color, painted first) cuts any line under it around
          // its letters: a ring that runs on through the gaps between words is the design (the kit's hub), not a crossing
          const tcs = getComputedStyle(T.el),
            halo =
              T.el instanceof SVGElement &&
              /^stroke/.test(tcs.paintOrder || "") &&
              parseFloat(tcs.strokeWidth) >= 4 &&
              tcs.stroke !== "none";
          if (halo && strokeOnly && !over) continue;
          if (over >= need) kind = "covers";
          else if (bare >= need && (strokeOnly || img || contrast < 3))
            kind = strokeOnly ? "line-through" : img ? "on-photo" : "low-contrast";
          else if (isTitle && !S.el.closest("[data-title]") && over + under >= need) kind = "title-on-scene";
          else if (!strokeOnly && !outline && under >= 2 && frac < 0.9 && bare >= 1) kind = "straddles";
          if (!kind) continue;
          const sr = S.r;
          out.push({
            kind,
            a: window.__names.addr(T.el),
            b: window.__names.addr(S.el),
            text: T.label,
            shape: `${S.el.tagName.toLowerCase()}${S.el.className && typeof S.el.className === "string" ? "." + S.el.className.split(" ")[0] : ""}${where(S.el)} ${Math.round(sr.left)},${Math.round(sr.top)} ${Math.round(sr.width)}×${Math.round(sr.height)}`,
            box: [x.l, x.t, x.r, x.b],
          });
        }
      }
      // words that run past the edge of their own card (the check above skips a word's own card): the nearest painted box
      // around the words is their card; sideways any overhang counts, up and down a font's tall line box is allowed
      for (const T of texts) {
        if (T.el.closest("[data-title]")) continue;
        let q = T.r;
        for (let e = T.el; e && e !== document.body; e = e.parentElement) {
          const cs = getComputedStyle(e),
            r = e.getBoundingClientRect();
          if (r.width * r.height > 0.35 * W * H) break;
          const bw = parseFloat(cs.borderTopWidth) || 0;
          if (e !== T.el && cs.overflow === "hidden" && !(alpha(cs.backgroundColor) > 0.15)) {
            // a bare clip (a sweep, a ticker): only what shows counts
            const l = Math.max(q.left, r.left),
              rr = Math.min(q.right, r.right),
              tp = Math.max(q.top, r.top),
              bt = Math.min(q.bottom, r.bottom);
            if (rr <= l || bt <= tp) break;
            q = { left: l, right: rr, top: tp, bottom: bt, height: bt - tp };
          }
          const painted =
            alpha(cs.backgroundColor) > 0.15 ||
            cs.backgroundImage.includes("gradient") ||
            (bw > 0 && alpha(cs.borderTopColor) > 0.05 && cs.borderTopStyle !== "none");
          if (!painted) continue;
          const side = Math.max(r.left + bw - q.left, q.right - (r.right - bw)),
            vert = Math.max(r.top - q.top, q.bottom - r.bottom);
          if (side > 2 || vert > 0.15 * q.height)
            out.push({
              kind: "spills",
              a: window.__names.addr(T.el),
              b: window.__names.addr(e),
              text: T.label,
              shape: `${e.tagName.toLowerCase()}.${String(e.className || "").split(" ")[0]}${where(e)} ${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}×${Math.round(r.height)}`,
              box: [q.left, q.top, q.right, q.bottom],
            });
          break;
        }
      }
      // a vertical cut: the phone's full-screen player crops each side and covers the top, the bottom and the right edge's
      // button rail (engine/contracts.json → phone_safe). Titles are the build's business; a scene's own words are checked here
      if (H > W)
        for (const T of texts) {
          if (T.el.closest("[data-title]")) continue;
          const q = T.r,
            z = [];
          if (q.left < W * Z.side - 2 || q.right > W * (1 - Z.side) + 2) z.push("the side crop");
          if (q.top < H * Z.status_bar - 2) z.push("the status bar");
          if (q.bottom > H * Z.caption + 2) z.push("the caption");
          if (q.bottom > H * Z.rail.y && q.right > W * Z.rail.x + 2) z.push("the button rail");
          if (z.length)
            out.push({
              kind: "phone-safe",
              a: window.__names.addr(T.el),
              text: T.label,
              shape: z.join(" + "),
              box: [q.left, q.top, q.right, q.bottom],
            });
        }
      for (let i = 0; i < texts.length; i++)
        for (let j = i + 1; j < texts.length; j++) {
          const A = texts[i],
            B = texts[j];
          if (A.group === B.group || A.group.contains(B.el) || B.group.contains(A.el)) continue;
          const x = inter(A.r, B.r);
          if (!x || x.a < 0.12 * Math.min(A.r.width * A.r.height, B.r.width * B.r.height)) continue;
          out.push({
            kind: "on-text",
            a: window.__names.addr(A.el),
            b: window.__names.addr(B.el),
            text: A.label,
            shape: B.label,
            box: [x.l, x.t, x.r, x.b],
          });
        }
      // two reading zones: a title up while the scene shows words of its own (readable: the visibility test above)
      const titled = texts.filter((T) => T.el.closest("[data-title]")),
        scene = texts.filter((T) => !T.el.closest("[data-title]"));
      const nWords = (s) => (s.match(/[\p{L}\p{N}][\p{L}\p{N}'’.,%$-]*/gu) || []).length,
        sceneWords = [...new Set(scene.map((T) => T.el))].reduce((n, el) => n + nWords(el.textContent || ""), 0);
      if (titled.length && scene.length && sceneWords >= Z2) {
        const u = scene.reduce((q, T) => ({ l: Math.min(q.l, T.r.left), t: Math.min(q.t, T.r.top), r: Math.max(q.r, T.r.right), b: Math.max(q.b, T.r.bottom) }),
          { l: W, t: H, r: 0, b: 0 });
        out.push({
          kind: "two-zones",
          a: window.__names.addr(titled[0].el),
          text: `${titled[0].label} while the scene shows its own words`,
          shape: [...new Set(scene.map((T) => T.label))].slice(0, 3).join(", "),
          box: [u.l, u.t, u.r, u.b],
        });
      }
      return out;
    },
    t,
    W,
    H,
    CONTRACTS.phone_safe,
    C.two_zones_words,
  ));
  found.forEach((f) => hits.push({ t: +t.toFixed(2), ...f }));
  // where every named element is right now (fractions of the frame), if it's on screen at all
  const els = await step(`inspect: map the elements at ${t.toFixed(2)}s`, () => p.evaluate(
    (t, W, H, seek) => {
      if (seek) window.__timelines.main.seek(t, false);
      const op = new Map(),
        q = (v) => Math.round(v * 10000) / 10000;
      const eff = (e) => {
        if (!e || e.nodeType !== 1) return 1;
        if (op.has(e)) return op.get(e);
        const cs = getComputedStyle(e),
          v = cs.display === "none" || cs.visibility === "hidden" ? 0 : +cs.opacity * eff(e.parentElement);
        op.set(e, v);
        return v;
      };
      const out = [],
        clips = {}; // i → the part of its box a clipping ancestor (overflow hidden) lets show, where that's less
      window.__inspectEls.forEach((el, i) => {
        if (eff(el) < 0.02) return;
        const r = el.getBoundingClientRect();
        if (r.width * r.height < 4 || r.right < 0 || r.bottom < 0 || r.left > W || r.top > H) return;
        out.push([i, q(r.left / W), q(r.top / H), q(r.right / W), q(r.bottom / H)]);
        let [l, tp, rt, bt] = [r.left, r.top, r.right, r.bottom];
        for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
          const cs = getComputedStyle(e);
          if (cs.overflowX === "visible" && cs.overflowY === "visible") continue;
          const c = e.getBoundingClientRect();
          // a box the size of the frame (the stage, the root) clips at the frame's own edges: that's the frame, which
          // the check measures against, not a window inside it
          if (c.left <= 0.5 && c.top <= 0.5 && c.right >= W - 0.5 && c.bottom >= H - 0.5) continue;
          [l, tp, rt, bt] = [Math.max(l, c.left), Math.max(tp, c.top), Math.min(rt, c.right), Math.min(bt, c.bottom)];
        }
        if (l > r.left || tp > r.top || rt < r.right || bt < r.bottom)
          clips[i] = rt > l && bt > tp ? [q(l / W), q(tp / H), q(rt / W), q(bt / H)] : null;
      });
      return [out, clips];
    },
    t,
    W,
    H,
    near,
  ));
  seenAt.push([+t.toFixed(2), els[0], els[1]]);
  if (Math.round(t / STEP) % 200 === 0) console.log(`  … ${t.toFixed(1)}s`);
}

// merge each (check, elements) into time spans
const spans = new Map();
for (const h of hits) {
  const k = `${h.kind}|${h.a}|${h.b || ""}`;
  const L = spans.get(k) || [];
  const last = L[L.length - 1];
  if (last && h.t - last.t1 <= STEP * 2.1) {
    last.t1 = h.t;
    last.boxes.push([h.t, h.box]);
  } else L.push({ t0: h.t, t1: h.t, boxes: [[h.t, h.box]], h });
  spans.set(k, L);
}
const HINT = {
  covers: "a shape paints over these words: move it beside them, or bring the words above it",
  "line-through": "a line runs through these words: route it along an edge, or under a solid card",
  "on-photo": "words on a picture with nothing solid behind them: give them a solid tag",
  "low-contrast": "words on a shape too close in brightness: a solid, darker card behind them",
  "title-on-scene": "a title lands on the drawing: the scene moves aside or goes wordless while a title is up",
  straddles: "words half on a shape, half off: put them wholly on it or wholly beside it",
  spills: "words run past the edge of their own card: widen the card or shorten the words",
  "phone-safe": "a phone hides this: keep a vertical cut's words in design x 120–960, y 220 and below",
  "on-text": "two sets of words overlap: one moves, or waits for the other to leave",
  "two-zones": "a title and the scene's own words at once: the scene goes wordless while a title is up, or the title waits",
};
const WARN = new Set(["two-zones", "fast-text", "cut-short", "offscreen-at-rest"]); // can be by design: the human confirms or dismisses
const key = (a) => String(a).replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "");
const list = [],
  ids = new Map();
for (const [k, L] of spans)
  for (const s of L)
    if (s.t1 - s.t0 + STEP >= (k.startsWith("phone-safe") ? 1.0 : MIN)) {
      // a word flying in or out may cross the edge
      const { kind, a, b: el2, text, shape } = s.h;
      const mid = (s.t0 + s.t1) / 2,
        [bt, bb] = s.boxes.reduce((x, y) => (Math.abs(y[0] - mid) < Math.abs(x[0] - mid) ? y : x));
      let id = `f-${kind}-${key(a)}${el2 ? "-x-" + key(el2) : ""}`;
      ids.set(id, (ids.get(id) || 0) + 1);
      if (ids.get(id) > 1) id += `-${ids.get(id)}`;
      list.push({
        id,
        check: kind,
        severity: WARN.has(kind) ? "warning" : "error",
        elements: [a, el2].filter(Boolean),
        text,
        ...(kind === "phone-safe" || kind === "on-text" || kind === "two-zones" ? { detail: shape } : {}),
        t0: s.t0,
        t1: s.t1,
        at: bt,
        box: bb.map(Math.round),
        box_n: [bb[0] / W, bb[1] / H, bb[2] / W, bb[3] / H].map((v) => Math.round(v * 10000) / 10000),
        hint: HINT[kind],
      });
    }
// the human's standing rules (Review Studio): keep-clear zones from the map just made, done scenes by snapshot
const RULES = readRules();
const ruled = [];
if (RULES.keep.length) {
  const k = keepClear({ rules: RULES, TL, META, seenAt, W, H, near: nearCut, MIN, STEP });
  ruled.push(...k.out);
  k.warn.forEach((w) => console.log(`⚠️  ${w}`));
}
if (RULES.done.length) {
  const d = await lockedScenes({ rules: RULES, TL, browser: b, W, H, COMP, seenAt, META });
  ruled.push(...d.out);
  d.warn.forEach((w) => console.log(`⚠️  ${w}`));
}
for (const f of ruled) {
  let id = `f-${f.check}-${key(f.elements[0] || f.detail.split(",")[0])}${f.check === "keep-clear" ? "-x-" + key(f.detail) : ""}`;
  ids.set(id, (ids.get(id) || 0) + 1);
  if (ids.get(id) > 1) id += `-${ids.get(id)}`;
  const { zone, ...rest } = f;
  list.push({ id, severity: "error", ...rest, ...(zone ? { zone } : {}) });
}
// from the map: words gone too fast, things parked half off the frame (warnings)
for (const f of [...fastText({ META, seenAt, STEP, C, END, near: nearCut }), ...parked({ META, seenAt, STEP, C, near: nearCut }), ...deadAir({ META, seenAt, STEP, C, cuts })]) {
  let id = `f-${f.check}-${key(f.elements[0] ?? f.t0)}`;
  ids.set(id, (ids.get(id) || 0) + 1);
  if (ids.get(id) > 1) id += `-${ids.get(id)}`;
  // a pixel box from the normalized one, so its still is marked like every other finding's
  const box = f.box_n && [f.box_n[0] * W, f.box_n[1] * H, f.box_n[2] * W, f.box_n[3] * H].map(Math.round);
  list.push({ id, severity: "warning", ...f, ...(box ? { box } : {}) });
}
// the first frame, empty (a warning; only a scrub from the start can say)
if (FROM <= STEP)
  for (const f of blankStart({ META, seenAt })) list.push({ id: "f-blank-start", severity: "warning", ...f });
// words the build made that never reach the screen (an error; only a whole scrub can say "never")
if (FROM <= STEP && TO >= END)
  for (const f of neverSeen({ META, seenAt, TL })) {
    let id = `f-${f.check}-${key(f.elements[0])}`;
    ids.set(id, (ids.get(id) || 0) + 1);
    if (ids.get(id) > 1) id += `-${ids.get(id)}`;
    list.push({ id, severity: "error", ...f });
  }
list.sort((a, b) => a.t0 - b.t0 || a.id.localeCompare(b.id));

// the element map: when each one is on screen, and its box whenever it moves (a box holds until the next one)
const SRC = fs.existsSync(SOURCES) ? JSON.parse(fs.readFileSync(SOURCES, "utf8")) : [];
const lineOf = (h) => {
  let pc = null;
  for (const m of SRC) if (m.from <= h) pc = m;
  return pc && `${pc.file}:${pc.line0 + h - pc.from}`;
};
// the line that made it: the first frame in the project's own files, else the first outside div()/svg() themselves
const srcOf = (m) => {
  if (m.addr.startsWith("title/")) return `reel.json titles.${m.addr.slice(6)}`;
  if (!m.stack) return m.addr.startsWith("frame/") ? "engine:js/pipeline/compose.mjs" : "engine:js/pipeline/media.mjs";
  const locs = [...String(m.stack || "").matchAll(/index\.html:(\d+):\d+/g)]
    .map((x) => lineOf(+x[1]))
    .filter((l) => l && !l.startsWith("engine:js/reel/00-core.js"));
  return locs.find((l) => !/^(engine|studio):/.test(l)) || locs[0] || null;
};
const segOf = (addr) =>
  addr.startsWith("title/")
    ? TL.titles.find((x) => x.el === addr)?.segment || null
    : addr.startsWith("frame/")
      ? null
      : addr.split("/")[0];
const E = META.map((m) => {
  const seg = segOf(m.addr),
    S = TL.segments.find((x) => x.name === seg);
  return {
    id: m.addr,
    segment: seg,
    scene: S ? S.scene || S.kind : null,
    kind: m.kind,
    named: m.named,
    up: m.up,
    text: m.text,
    src: srcOf(m),
    on: [],
    boxes: [],
  };
});
const last = new Map(); // element index → [moment index, last stored box]
seenAt.forEach(([t, els], k) => {
  for (const [i, ...bx] of els) {
    const e = E[i],
      L = last.get(i),
      cont = L && L[0] === k - 1;
    if (cont) e.on[e.on.length - 1][1] = t;
    else e.on.push([t, t]);
    if (!cont || bx.some((v, j) => Math.abs(v - L[1][j]) > 0.002)) {
      e.boxes.push([t, ...bx]);
      last.set(i, [k, bx]);
    } else last.set(i, [k, L[1]]);
  }
});
// dead tweens (an error): one finding per element, naming the values and the line of scenes.js that made the tween
{
  const by = new Map();
  for (const b of BAD) {
    if (!b.addr) continue;
    const f = by.get(b.addr) || { props: new Set(), stack: b.stack };
    b.props.forEach((x) => f.props.add(x));
    by.set(b.addr, f);
  }
  for (const [addr, f] of by) {
    const m = { addr, stack: f.stack },
      seg = segOf(addr),
      S = TL.segments.find((x) => x.name === seg),
      props = [...f.props].join(", ");
    let id = `f-dead-tween-${key(addr)}`;
    ids.set(id, (ids.get(id) || 0) + 1);
    if (ids.get(id) > 1) id += `-${ids.get(id)}`;
    list.push({
      id,
      check: "dead-tween",
      severity: "error",
      elements: [addr],
      text: `an animation of ${props} gets a value that isn't a number, so it never runs${srcOf(m) ? ` (${srcOf(m)})` : ""}`,
      t0: S ? S.t0 : 0,
      t1: S ? S.t1 : 0,
      at: S ? +((S.t0 + S.t1) / 2).toFixed(2) : 0,
      hint: "an object or NaN where a number goes (exPath returns {x, y}: use .x and .y): log the value where the tween is made",
    });
  }
  list.sort((a, b) => a.t0 - b.t0 || a.id.localeCompare(b.id));
}
const range = [Math.max(0, FROM), Math.min(END, TO)].map((v) => +v.toFixed(2));
fs.writeFileSync(
  ELEMENTS,
  JSON.stringify({ elements: 1, fingerprint: TL.fingerprint, size: [W, H], step: STEP, moments: seenAt.length, range, items: E }),
);
fs.writeFileSync(
  FINDINGS,
  JSON.stringify({ findings: 1, fingerprint: TL.fingerprint, checked, range, items: list }, null, 1),
);
list.forEach((o, i) =>
  console.log(
    `${String(i + 1).padStart(2)}. ${o.t0.toFixed(1).padStart(6)}–${o.t1.toFixed(1).padStart(6)}s  ${o.severity === "warning" ? "⚠ " : ""}${o.check.padEnd(14)} ${o.elements.join("  ×  ")}  ${o.text}${o.detail && /phone-safe|done|two-zones/.test(o.check) ? " (" + o.detail + ")" : ""}`,
  ),
);
// say how much was looked at, so a check that silently looked at nothing can't pass for a clean one
const span = `${checked} moments, ${range[0].toFixed(1)}–${range[1].toFixed(1)}s`;
if (!checked) {
  console.error(`⛔ checked 0 moments (${span}): nothing was inspected`);
  process.exit(1);
}
const nErr = list.filter((f) => f.severity === "error").length,
  nWarn = list.length - nErr;
console.log(
  !list.length
    ? `no findings (checked ${span})`
    : `${nErr ? `${nErr} error${nErr > 1 ? "s" : ""}` : "no errors"}${nWarn ? `, ${nWarn} warning${nWarn > 1 ? "s" : ""} (for the human to confirm or dismiss)` : ""} → ${FINDINGS} (checked ${span})`,
);
const onScreen = E.filter((e) => e.on.length).length;
console.log(`${E.length} elements → ${ELEMENTS} (${onScreen} on screen, mapped at ${seenAt.length} moments)`);

if (SHOTS && list.length) {
  fs.rmSync(`${QA}/findings`, { recursive: true, force: true });
  fs.mkdirSync(`${QA}/findings`, { recursive: true });
  for (const [i, o] of list.entries()) {
    const t = o.at;
    await p.evaluate(
      (t, box) => {
        window.__timelines.main.seek(t, false);
        let m = document.getElementById("__mark");
        if (!m) {
          m = document.createElement("div");
          m.id = "__mark";
          document.body.appendChild(m);
        }
        // a warning about the whole frame (two-zones, fast-text on a title) has no box: shoot the moment unmarked
        m.style.cssText = !box
          ? "display:none"
          : `position:fixed;z-index:99999;left:${box[0] - 6}px;top:${box[1] - 6}px;width:${box[2] - box[0] + 12}px;height:${box[3] - box[1] + 12}px;border:4px solid #0af;pointer-events:none`;
      },
      t,
      o.box || null,
    );
    await p.screenshot({ path: `${QA}/findings/${String(i + 1).padStart(2, "0")}-${t}s.png` });
  }
  await p.evaluate(() => document.getElementById("__mark")?.remove());
  console.log(`shots: ${QA}/findings/`);
}
await b.close();
