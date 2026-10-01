// Overlap audit: scrub the composition and find every place where words and pictures fight.
//   covers        a shape paints OVER words (a reviewer, Sep 30: the email bar grew over "28 h", then it lit up red)
//   on-graphic    words sit on a shape with nothing solid between them (words on a see-through background)
//   on-text       two sets of words overlap
//   spills        words run past the edge of their own card ("OTHER TEAM" hung off its box through v3; nothing else saw it)
//   phone-safe    (vertical cuts) a scene's words where a phone hides them: under the status bar, in the side crop, under the
//                 button rail or the caption, for a second or more. build.mjs checks only the titles, and qa.py finds these
//                 only after a 4-minute render (the Socrates explainer's v1, Oct 1, 2026: 30 hits, every scene's kicker)
// Near cuts (the transitions blur and overlap on purpose) is skipped. Needs `vs build --no-render` first.
//   vs audit [--step 0.15] [--min 0.3] [--from s] [--to s] [--shots]   → build/qa/overlaps.json (+ build/qa/overlaps/*.png)
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { launch, loadReel } from "./lib/browser.mjs";
import { COMP, QA } from "./lib/paths.mjs";

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > 0 ? process.argv[i + 1] : d;
};
const STEP = +arg("--step", 0.15),
  MIN = +arg("--min", 0.45),
  SHOTS = process.argv.includes("--shots"),
  FROM = +arg("--from", 0),
  TO = +arg("--to", 1e9);
const R = loadReel(),
  [W, H] = R.size;

const b = await launch(),
  p = await b.newPage();
await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await p.goto(pathToFileURL(path.resolve(COMP, "index.html")).href, { waitUntil: "load" });
// the cuts and the length come from the composition itself, exactly as the build timed it. Summing reel.json's "secs"
// read a beat-timed reel's length as NaN, so the audit checked nothing and said "no overlaps" (fixed in 1.0.1).
const { cuts, END } = await p.evaluate(() => ({ cuts: window.REEL.segments.map((s) => s.t0), END: window.REEL.end }));
if (!(END > 0)) {
  console.error(`⛔ the composition's length is ${END}: run vs build --no-render first`);
  process.exit(1);
}
await p.evaluate(async () => {
  await document.fonts.ready;
  const s = document.createElement("style");
  s.textContent = "*{pointer-events:auto !important}";
  document.head.appendChild(s);
});

const hits = [];
let checked = 0;
for (let t = Math.max(0.05, FROM); t < Math.min(END, TO); t += STEP) {
  if (cuts.some((c) => t > c - 0.5 && t < c + 0.6)) continue;
  checked++;
  const found = await p.evaluate(
    (t, W, H) => {
      window.__timelines.main.seek(t, false);
      const alpha = (c) => {
        const m = c.match(/rgba?\(([^)]+)\)/);
        if (!m) return 0;
        const v = m[1].split(",").map(Number);
        return v.length > 3 ? v[3] : 1;
      };
      const vis = (el) => {
        let o = 1;
        for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
          const cs = getComputedStyle(e);
          if (cs.display === "none" || cs.visibility === "hidden") return 0;
          o *= +cs.opacity;
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
        const r = rg.getBoundingClientRect();
        if (r.width < 3 || r.right < 0 || r.left > W || r.bottom < 0 || r.top > H) continue;
        texts.push({
          el,
          r,
          label: label(el),
          group: el.closest("[data-title]") || el.closest(".ex-chip,.ex-blk,.ex-k,.ex-t,.ex-m") || el,
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
          if (over >= need) kind = "covers";
          else if (bare >= need && (strokeOnly || img || contrast < 3))
            kind = strokeOnly ? "line-through" : img ? "on-photo" : "low-contrast";
          else if (isTitle && !S.el.closest("[data-title]") && over + under >= need) kind = "title-on-scene";
          else if (!strokeOnly && !outline && under >= 2 && frac < 0.9 && bare >= 1) kind = "straddles";
          if (!kind) continue;
          const sr = S.r;
          out.push({
            kind,
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
              text: T.label,
              shape: `${e.tagName.toLowerCase()}.${String(e.className || "").split(" ")[0]}${where(e)} ${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}×${Math.round(r.height)}`,
              box: [q.left, q.top, q.right, q.bottom],
            });
          break;
        }
      }
      // a vertical cut: the phone's full-screen player crops ~9% off each side and covers the top 10%, the bottom 16%, and the
      // right fifth below 62% height. Titles are build.mjs's business; a scene's own words are checked here
      if (H > W)
        for (const T of texts) {
          if (T.el.closest("[data-title]")) continue;
          const q = T.r,
            z = [];
          if (q.left < W * 0.11 - 2 || q.right > W * 0.89 + 2) z.push("the side crop");
          if (q.top < H * 0.1 - 2) z.push("the status bar");
          if (q.bottom > H * 0.84 + 2) z.push("the caption");
          if (q.bottom > H * 0.62 && q.right > W * 0.8 + 2) z.push("the button rail");
          if (z.length)
            out.push({
              kind: "phone-safe",
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
          out.push({ kind: "on-text", text: A.label, shape: B.label, box: [x.l, x.t, x.r, x.b] });
        }
      return out;
    },
    t,
    W,
    H,
  );
  found.forEach((f) => hits.push({ t: +t.toFixed(2), ...f }));
  if (Math.round(t / STEP) % 200 === 0) console.log(`  … ${t.toFixed(1)}s`);
}

// merge each (kind, words, shape) into time spans
const spans = new Map();
for (const h of hits) {
  const k = `${h.kind}|${h.text}|${h.shape.replace(/ -?\d+,-?\d+ \d+×\d+$/, "")}`;
  const L = spans.get(k) || [];
  const last = L[L.length - 1];
  if (last && h.t - last.t1 <= STEP * 2.1) {
    last.t1 = h.t;
    last.boxes.push([h.t, h.box]);
  } else L.push({ t0: h.t, t1: h.t, boxes: [[h.t, h.box]], shape: h.shape });
  spans.set(k, L);
}
const list = [];
for (const [k, L] of spans)
  for (const s of L)
    if (s.t1 - s.t0 + STEP >= (k.startsWith("phone-safe") ? 1.0 : MIN)) {
      // a word flying in or out may cross the edge
      const [kind, text] = k.split("|");
      const mid = (s.t0 + s.t1) / 2,
        [bt, bb] = s.boxes.reduce((a, b) => (Math.abs(b[0] - mid) < Math.abs(a[0] - mid) ? b : a));
      list.push({ kind, text, shape: s.shape, t0: s.t0, t1: s.t1, at: bt, box: bb.map(Math.round) });
    }
list.sort((a, b) => a.t0 - b.t0);
fs.mkdirSync(QA, { recursive: true });
fs.writeFileSync(`${QA}/overlaps.json`, JSON.stringify(list, null, 1));
list.forEach((o, i) =>
  console.log(
    `${String(i + 1).padStart(2)}. ${o.t0.toFixed(1).padStart(6)}–${o.t1.toFixed(1).padStart(6)}s  ${o.kind.padEnd(12)} ${o.text}  ×  ${o.shape}`,
  ),
);
// say how much was looked at, so a check that silently looked at nothing can't pass for a clean one
const span = `${checked} moments, ${Math.max(0, FROM).toFixed(1)}–${Math.min(END, TO).toFixed(1)}s`;
if (!checked) {
  console.error(`⛔ checked 0 moments (${span}): nothing was audited`);
  process.exit(1);
}
console.log(list.length ? `${list.length} overlaps → ${QA}/overlaps.json (checked ${span})` : `no overlaps (checked ${span})`);

if (SHOTS && list.length) {
  fs.rmSync(`${QA}/overlaps`, { recursive: true, force: true });
  fs.mkdirSync(`${QA}/overlaps`);
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
        m.style.cssText = `position:fixed;z-index:99999;left:${box[0] - 6}px;top:${box[1] - 6}px;width:${box[2] - box[0] + 12}px;height:${box[3] - box[1] + 12}px;border:4px solid #0af;pointer-events:none`;
      },
      t,
      o.box,
    );
    await p.screenshot({ path: `${QA}/overlaps/${String(i + 1).padStart(2, "0")}-${t}s.png` });
  }
  await p.evaluate(() => document.getElementById("__mark")?.remove());
  console.log(`shots: ${QA}/overlaps/`);
}
await b.close();
