// Build step 5, the composition: ONE HyperFrames page (build/comp/index.html). The data and the runtime go in ONE inline
// script: HyperFrames' compiler reorders separate scripts, and a runtime that ran before its data painted 27 black
// storyboard frames (Sep 29, 2026).
import fs from "node:fs";
import path from "node:path";
import { ENGINE, studioRoot } from "../lib/paths.mjs";
import { R, W, H, FPS, P, B, COMP, A, OUT, copy } from "./context.mjs";
import { SEGS, END } from "./timing.mjs";

// The runtime: js/reel/*.js in name order (one closure), with the scenes inlined at /*__EXTRA_SCENES__*/. An explainer
// (reel.json → "scene_lib": "explainer", plan.py sets it) gets the engine's scene library around its own scenes: base,
// icons and props first, then the studio's promoted scenes (library/scenes/*.js), then the project's scenes.js, then the
// layout that wraps them. A sizzle reel gets only its own scenes.js.
function runtime() {
  const dir = path.join(ENGINE, "js/reel"),
    read = (f) => fs.readFileSync(f, "utf8");
  const parts = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".js"))
    .sort()
    .map((f) => read(path.join(dir, f)));
  const own = fs.existsSync("scenes.js") ? read("scenes.js") : "";
  let scenes = own;
  if (R.scene_lib === "explainer") {
    const lib = (f) => read(path.join(ENGINE, "js/scenes", f)),
      S = studioRoot(),
      ld = S && path.join(S, "library/scenes");
    const promoted =
      ld && fs.existsSync(ld)
        ? fs
            .readdirSync(ld)
            .filter((f) => f.endsWith(".js"))
            .sort()
            .map((f) => read(path.join(ld, f)))
        : [];
    scenes = [lib("base.js"), lib("icons.js"), lib("props.js"), ...promoted, own, lib("layout.js")].join("\n");
  }
  return parts.join("\n").replace("/*__EXTRA_SCENES__*/", () => scenes);
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
    segments: SEGS.map(({ name, t0, t1, in: inn, source, push, titles, fx }) => ({
      name,
      t0,
      t1,
      in: inn,
      source,
      push,
      titles,
      fx,
    })),
  };
  fs.writeFileSync(
    `${COMP}/index.html`,
    `<!doctype html>
<!-- Written by vs build from reel.json. Edit reel.json or scenes.js (or the engine's js/reel/), never this file. -->
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=${W}, height=${H}">
<script src="gsap.min.js"></script>
<style>${CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="${END}" data-width="${W}" data-height="${H}">
<audio id="bed" src="assets/bed.wav" data-start="0" data-duration="${END}" data-track-index="30" data-volume="1"></audio>
<div id="camrig"><div id="paper"></div>
${segHTML.join("\n")}
<svg id="fx" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"></svg><div id="dot"></div><div id="ring"></div></div><div class="vignette"></div><div id="titles"></div><div id="grain"></div>
</div>
<script>
window.REEL = ${JSON.stringify(REEL)};
${runtime()}
window.__timelines = window.__timelines || {};
window.__timelines["main"] = window.__reelTimeline;
</script>
</body></html>
`,
  );
  fs.writeFileSync(
    OUT.replace(".mp4", ".cuts.json"),
    JSON.stringify(
      SEGS.map(({ name, t0, t1, in: inn, source }) => ({ name, t0, t1, in: inn, kind: Object.keys(source)[0] })),
      null,
      1,
    ),
  );
  console.log(`composition: ${COMP}/index.html  (${SEGS.length} segments, ${END.toFixed(2)}s)`);
  SEGS.forEach((s) =>
    console.log(`  ${s.t0.toFixed(2).padStart(6)}–${s.t1.toFixed(2).padStart(6)}  ${s.in.padEnd(5)} ${s.name}`),
  );
}
