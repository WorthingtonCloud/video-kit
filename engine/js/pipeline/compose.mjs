// Build step 5, the composition: ONE HyperFrames page (build/comp/index.html). The data and the runtime go in ONE inline
// script: HyperFrames' compiler reorders separate scripts, and a runtime that ran before its data painted 27 black
// storyboard frames (Sep 29, 2026).
import fs from "node:fs";
import path from "node:path";
import { ENGINE, studioRoot, hash, TIMELINE, SOURCES, scenesFile } from "../lib/paths.mjs";
import { R, W, H, FPS, P, B, COMP, A, copy, SHAPE } from "./context.mjs";
import { SEGS, END, timeline } from "./timing.mjs";

// The runtime: js/reel/*.js in name order (one closure), with the scenes inlined at /*__EXTRA_SCENES__*/. An explainer
// (reel.json → "scene_lib": "explainer", plan.py sets it) gets the engine's scene library around its own scenes: base,
// icons and props first, then the studio's promoted scenes (library/scenes/*.js), then the project's scenes.js, then the
// layout that wraps them. A sizzle reel gets only its own scenes.js.
// Returns the text and where each file's lines start in it, so vs inspect can trace an element to its line in scenes.js.
const PH = "/*__EXTRA_SCENES__*/";
function runtime() {
  const dir = path.join(ENGINE, "js/reel"),
    read = (f) => fs.readFileSync(f, "utf8");
  const sf = scenesFile(SHAPE),
    own = fs.existsSync(sf) ? [{ file: sf, text: read(sf) }] : [];
  let scenes = own;
  if (R.scene_lib === "explainer") {
    const lib = (f) => ({ file: `engine:js/scenes/${f}`, text: read(path.join(ENGINE, "js/scenes", f)) }),
      S = studioRoot(),
      ld = S && path.join(S, "library/scenes");
    const promoted =
      ld && fs.existsSync(ld)
        ? fs
            .readdirSync(ld)
            .filter((f) => f.endsWith(".js"))
            .sort()
            .map((f) => ({ file: `studio:library/scenes/${f}`, text: read(path.join(ld, f)) }))
        : [];
    scenes = [lib("base.js"), lib("icons.js"), lib("props.js"), ...promoted, ...own, lib("layout.js")];
  }
  // the pieces in order, each with the line of its file it starts on (text after the placeholder continues its line)
  const pieces = [];
  fs.readdirSync(dir)
    .filter((f) => f.endsWith(".js"))
    .sort()
    .forEach((f, i) => {
      const text = read(path.join(dir, f)),
        at = text.indexOf(PH),
        file = `engine:js/reel/${f}`;
      if (i) pieces.push({ text: "\n" });
      if (at < 0) return pieces.push({ file, text, line0: 1 });
      pieces.push({ file, text: text.slice(0, at), line0: 1 });
      scenes.forEach((sc, k) => {
        if (k) pieces.push({ text: "\n" });
        pieces.push({ ...sc, line0: 1 });
      });
      pieces.push({ file, text: text.slice(at + PH.length), line0: text.slice(0, at).split("\n").length });
    });
  let out = "",
    lines = 0;
  const map = [];
  for (const pc of pieces) {
    if (pc.file) map.push({ file: pc.file, from: lines, line0: pc.line0 });
    out += pc.text;
    lines += pc.text.split("\n").length - 1;
  }
  return { text: out, map };
}

export function compose({ segHTML, media, CSS }) {
  const sceneData = JSON.parse(JSON.stringify(R.scenes || {}), (k, v) => {
    if (typeof v === "string" && /\.(jpe?g|png|webp)$/i.test(v) && fs.existsSync(v)) {
      fs.mkdirSync(`${A}/img`, { recursive: true });
      copy(v, `${A}/img/${path.basename(v)}`);
      return `assets/img/${path.basename(v)}`;
    }
    return v;
  });
  const REEL = {
    size: R.size,
    fps: FPS,
    palette: P,
    beat: B,
    end: END,
    finish: R.finish,
    titles: R.titles,
    scenes: sceneData,
    media,
    punches: R.punches || [],
    scene_lib: R.scene_lib || "reel", // an explainer's layout.js centers its own scenes in widescreen; a reel's runtime does
    segments: SEGS.map(({ name, t0, t1, in: inn, source, push, titles, fx, overlay }) => ({
      name,
      t0,
      t1,
      in: inn,
      source,
      push,
      titles,
      fx,
      ...(overlay ? { overlay } : {}),
    })),
  };
  const rt = runtime();
  const html = `<!doctype html>
<!-- Written by vs build from reel.json. Edit reel.json or scenes.js (or the engine's js/reel/), never this file. -->
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=${W}, height=${H}">
<script src="gsap.min.js"></script>
<style>${CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="${END}" data-width="${W}" data-height="${H}">
<audio id="bed" src="assets/bed.wav" data-start="0" data-duration="${END}" data-track-index="30" data-volume="1"></audio>
<div id="camrig"><div id="paper" data-el="paper"></div>
${segHTML.join("\n")}
<svg id="fx" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"></svg><div id="dot" data-el="dot"></div><div id="ring" data-el="ring"></div></div><div class="vignette" data-el="vignette"></div><div id="titles"></div><div id="grain" data-el="grain"></div>
</div>
<script>
window.REEL = ${JSON.stringify(REEL)};
${rt.text}
window.__timelines = window.__timelines || {};
window.__timelines["main"] = window.__reelTimeline;
</script>
</body></html>
`;
  fs.writeFileSync(`${COMP}/index.html`, html);
  // which line of index.html is which file's line (vs inspect maps the stack that made an element back to its source)
  const first = html.slice(0, html.indexOf(rt.text)).split("\n").length;
  fs.writeFileSync(SOURCES, JSON.stringify(rt.map.map((m) => ({ ...m, from: first + m.from })), null, 1));
  // the one timing everything downstream reads, stamped with this composition's fingerprint
  fs.writeFileSync(TIMELINE, JSON.stringify(timeline(hash(html)), null, 1));
  console.log(`composition: ${COMP}/index.html + ${TIMELINE}  (${SEGS.length} segments, ${END.toFixed(2)}s)`);
  SEGS.forEach((s) =>
    console.log(`  ${s.t0.toFixed(2).padStart(6)}–${s.t1.toFixed(2).padStart(6)}  ${s.in.padEnd(5)} ${s.name}`),
  );
}
