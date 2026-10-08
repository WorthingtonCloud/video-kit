// A version keeps its own maps: drafts/vN/data/<shape>/ (engine/protocol/files.md). build/ moves on with every rebuild,
// but a review round, Compare and an old version's outlines need the timing, the element map and the findings of the
// composition that made THAT render. vs build writes this beside every render; qa.py adds qa.json and vs mix cues.json.
//   timeline.json   when (build/timeline.json, as rendered)
//   elements.json   what is on screen and where (vs inspect's map, only if it was made from this composition)
//   findings.json   what vs inspect found in it (the same rule)
//   comp.html       the composition itself (its HTML: ~100–200 KB, the assets stay in build/comp): a scene the human
//                   marks done is checked against it later (js/lib/rules.mjs)
//   version.json    the version, its shape, its fingerprint, the engine, when it was rendered, and what's here
//   source/         the files that made it (reel.json, plan.json, scenes.js, cues.py, narration.txt …): vs reopen puts
//                   a final's back exactly
import fs from "node:fs";
import path from "node:path";
import { TIMELINE, ELEMENTS, FINDINGS, dataDir, parseDraft } from "./paths.mjs";

// what made a render (vslib.SOURCE_FILES: the same list)
export const SOURCE_FILES = ["reel.json", "plan.json", "scenes.js", "scenes.vertical.js", "scenes.widescreen.js", "cues.py",
  "narration.txt", "SCRIPT.md", "music.json", "sfx.json", "mix.json"];

export function archive(out, { dir = process.cwd(), now = new Date() } = {}) {
  const at = (f) => path.join(dir, f),
    read = (f) => (fs.existsSync(at(f)) ? JSON.parse(fs.readFileSync(at(f), "utf8")) : null);
  const tl = read(TIMELINE);
  if (!tl) throw new Error(`no ${TIMELINE}: nothing to archive for ${out}`);
  const home = at(dataDir(out));
  fs.mkdirSync(home, { recursive: true });
  const kept = ["timeline.json"],
    skipped = [];
  fs.copyFileSync(at(TIMELINE), path.join(home, "timeline.json"));
  for (const [f, name] of [[ELEMENTS, "elements.json"], [FINDINGS, "findings.json"]]) {
    const j = read(f);
    if (j && j.fingerprint === tl.fingerprint) {
      fs.copyFileSync(at(f), path.join(home, name));
      kept.push(name);
    } else {
      fs.rmSync(path.join(home, name), { force: true }); // a map from another composition would point at the wrong things
      skipped.push(name);
    }
  }
  const comp = at("build/comp/index.html");
  if (fs.existsSync(comp)) {
    fs.copyFileSync(comp, path.join(home, "comp.html"));
    kept.push("comp.html");
  }
  const src = path.join(home, "source");
  fs.rmSync(src, { recursive: true, force: true });
  fs.mkdirSync(src, { recursive: true });
  for (const f of SOURCE_FILES) if (fs.existsSync(at(f))) fs.copyFileSync(fs.realpathSync(at(f)), path.join(src, f)); // a linked scenes.js: its content
  kept.push("source/");
  fs.writeFileSync(
    path.join(home, "version.json"),
    JSON.stringify(
      { version: tl.version, shape: parseDraft(out).shape, video: out, fingerprint: tl.fingerprint, reel: tl.reel, engine: tl.engine, size: tl.size, rendered: now.toISOString(), kept },
      null,
      1,
    ),
  );
  return { home: path.relative(dir, home), kept, skipped };
}
