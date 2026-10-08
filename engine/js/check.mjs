#!/usr/bin/env node
// vs check: the project's files against their contracts (engine/schema/*.schema.json), then the rules a schema can't
// express: every title, scene, shot and cue that's named exists; every time range sits inside its segment and ends after
// it starts; every word spec finds its word in the right act; every media path (lib: too) resolves; the size is one the
// kit lays out; an emphasis word is really in its title. A misspelled scene used to fail inside the browser mid-build,
// an unknown key was silently ignored, and a wrong path failed deep in ffmpeg.
//   vs check            prints ✗ errors and ⚠ warnings (file › path: what's wrong, and the likely fix); exits 1 on errors
// vs plan runs it after writing reel.json; vs build runs it before anything else. A reel.json or plan.json from before
// schema_version 2 is checked too, but its problems are warnings until vs migrate marks it.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { ENGINE, studioRoot, CONTRACTS, forShape, activeShape, scenesFile } from "./lib/paths.mjs";
import { wordAt } from "./lib/words.mjs";

const require = createRequire(path.join(ENGINE, "package.json"));
const SIZES = [CONTRACTS.sizes.vertical, CONTRACTS.sizes.wide];
const EM_FX = ["pulse", "box", "check", "beats", "ruler"];

// ── did you mean ──
function lev(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
const near = (x, opts) => {
  const best = [...opts].map((o) => [o, lev(String(x).toLowerCase(), String(o).toLowerCase())]).sort((p, q) => p[1] - q[1])[0];
  return best && best[1] <= Math.max(2, Math.floor(String(x).length / 4)) ? ` (did you mean "${best[0]}"?)` : "";
};
const list = (xs, n = 8) => [...xs].slice(0, n).join(", ") + ([...xs].length > n ? "…" : "");

// ── the scenes a project can name: the kit's, the studio's promoted ones (explainers), its own scenes.js ──
function sceneNames(text) {
  const out = new Set();
  for (const re of [
    /^\s*([A-Za-z_$][\w$]*)\s*\(\s*stage\b[^)]*\)\s*\{/gm, // pitch(stage, seg) {   (a method, not a call)
    /^\s*([A-Za-z_$][\w$]*)\s*:\s*(?:function\s*[\w$]*\s*)?\(\s*stage\b[^)]*\)\s*(?:=>|\{)/gm,
    /SCENES\.([A-Za-z_$][\w$]*)\s*=/g,
    /SCENES\[["']([^"']+)["']\]\s*=/g,
  ])
    for (const m of text.matchAll(re)) out.add(m[1]);
  return out;
}
function availableScenes(R, dir) {
  const read = (f) => (fs.existsSync(f) ? fs.readFileSync(f, "utf8") : "");
  const all = new Set(sceneNames(read(path.join(ENGINE, "js/reel/30-scenes.js"))));
  const add = (t) => sceneNames(t).forEach((s) => all.add(s));
  if (R.scene_lib === "explainer") {
    const ld = studioRoot() && path.join(studioRoot(), "library/scenes");
    if (ld && fs.existsSync(ld)) fs.readdirSync(ld).filter((f) => f.endsWith(".js")).forEach((f) => add(read(path.join(ld, f))));
  }
  add(read(path.join(dir, scenesFile(activeShape(dir), dir))));
  return all;
}

export { near, sceneNames };

export function check({ dir = process.cwd(), quiet = false } = {}) {
  const Ajv = require("ajv/dist/2020").default;
  const ajv = new Ajv({ allErrors: true, strict: false, verbose: true });
  const SD = path.join(ENGINE, "schema");
  for (const f of fs.readdirSync(SD).filter((f) => f.endsWith(".schema.json")))
    ajv.addSchema(JSON.parse(fs.readFileSync(path.join(SD, f), "utf8")));

  const errors = [],
    warnings = [];
  let files = 0;
  const S = studioRoot();
  const lib = (p) => (typeof p === "string" && p.startsWith("lib:") && S ? path.join(S, "library", p.slice(4)) : p);
  const exists = (p) => p && fs.existsSync(path.isAbsolute(lib(p)) ? lib(p) : path.join(dir, lib(p)));

  // a JSON pointer → segments[4] "s05_proof" › titles[1]
  const where = (doc, ptr) => {
    const parts = ptr.split("/").slice(1).map((p) => p.replace(/~1/g, "/").replace(/~0/g, "~"));
    let node = doc,
      out = [];
    for (const p of parts) {
      const isIdx = Array.isArray(node) && /^\d+$/.test(p);
      node = node?.[p];
      if (isIdx) {
        const nm = node && typeof node === "object" && !Array.isArray(node) && node.name ? ` "${node.name}"` : "";
        out[out.length - 1] = `${out[out.length - 1]}[${p}]${nm}`;
      } else out.push(p);
    }
    return out.join(" › ");
  };

  const say = (bag, label, ptrOrPath, msg) => bag.push(`${label}${ptrOrPath ? " › " + ptrOrPath : ""}: ${msg}`);

  // ── one file against its schema; old reel/plan files (no schema_version) only warn ──
  function validate(label, file, schema, { versioned = false } = {}) {
    let doc;
    try {
      doc = JSON.parse(fs.readFileSync(file, "utf8"));
    } catch (e) {
      say(errors, label, "", `not readable JSON (${e.message})`);
      return null;
    }
    files++;
    const old = versioned && doc?.schema_version == null,
      bag = old ? warnings : errors;
    const v = ajv.getSchema(`video-kit/${schema}.schema.json`);
    if (!v(doc)) {
      const errs = v.errors.filter((e) => e.keyword !== "if" && !/\/anyOf\/\d/.test(e.schemaPath));
      const seen = new Set();
      for (const e of errs) {
        const p = e.instancePath;
        let msg;
        const prm = e.params;
        if (e.keyword === "additionalProperties")
          msg = `unknown key "${prm.additionalProperty}"${near(prm.additionalProperty, Object.keys(e.parentSchema.properties || {}))}`;
        else if (e.keyword === "required") msg = `missing "${prm.missingProperty}"`;
        else if (e.keyword === "enum") msg = `${JSON.stringify(e.data)} isn't one of: ${list(prm.allowedValues, 13)}${near(e.data, prm.allowedValues)}`;
        else if (e.keyword === "type") msg = `should be ${prm.type === "number" || prm.type === "integer" ? "a " + prm.type : prm.type === "string" ? "text" : prm.type === "object" ? "an object {…}" : prm.type === "array" ? "a list […]" : prm.type}, not ${JSON.stringify(e.data)?.slice(0, 40)}`;
        else if (e.keyword === "const") msg = `should be ${JSON.stringify(prm.allowedValue)}`;
        else if (e.keyword === "pattern") msg = `${JSON.stringify(e.data)} isn't usable here (${e.parentSchema.description || "letters, digits, - and _ only"})`;
        else if (e.keyword === "anyOf") msg = `${JSON.stringify(e.data)?.slice(0, 40)} isn't usable here${e.parentSchema.description ? ` (${e.parentSchema.description})` : ""}`;
        else if (e.keyword === "propertyNames") continue; // its pattern error says it better
        else msg = `${JSON.stringify(e.data)?.slice(0, 40)} ${e.message}`;
        const line = `${where(doc, p)}|${msg}`;
        if (seen.has(line)) continue;
        seen.add(line);
        say(bag, label, where(doc, p), msg + (old ? " (an older file: vs migrate)" : ""));
      }
    }
    return { doc, bag };
  }

  // ── reel.json: the cross-references ──
  function reelRules(R, bag) {
    const L = "reel.json",
      titles = R.titles || {},
      shots = R.shots || {},
      used = new Set();
    if (Array.isArray(R.size) && !SIZES.some(([w, h]) => w === R.size[0] && h === R.size[1]))
      say(warnings, L, "size", `[${R.size}]: the kit lays out ${SIZES.map((s) => s.join("×")).join(" and ")}`);
    if (R.fps != null && !CONTRACTS.fps.proven.includes(R.fps))
      say(warnings, L, "fps", `${R.fps}: the kit is proven at ${CONTRACTS.fps.proven.join(", ")} fps`);
    const scenes = availableScenes(R, dir);
    const names = new Map();
    const B = +R.music?.beat,
      HIT = +R.music?.first_hit;
    let t = 0;
    (R.segments || []).forEach((s, i) => {
      const at = `segments[${i}] "${s.name}"`;
      if (names.has(s.name)) say(bag, L, at, `the name "${s.name}" is used twice (segments[${names.get(s.name)}] too): names are addresses`);
      names.set(s.name, i);
      const lens = ["beats", "secs", "to_hit"].filter((k) => s[k] != null);
      if (lens.length !== 1)
        say(bag, L, at, lens.length ? `give it ONE length, not ${lens.join(" and ")}` : `no length: give it "beats", "secs" or "to_hit"`);
      const unit = s.to_hit || s.secs != null ? 1 : B;
      const len = s.to_hit ? HIT - t : s.secs != null ? +s.secs : +s.beats * B;
      if (s.to_hit && !(len > 0)) say(bag, L, at, `to_hit: the music's first hit (${HIT}s) comes before this segment starts (${t.toFixed(2)}s)`);
      const src = s.source || {},
        kinds = ["scene", "shot", "clip", "still", "card", "grid"].filter((k) => src[k] != null);
      if (kinds.length !== 1)
        say(bag, L, `${at} › source`, kinds.length ? `one source only, not ${kinds.join(" + ")}` : "no source: scene, shot, clip, still, card or grid");
      if (src.scene != null && !scenes.has(src.scene))
        say(bag, L, `${at} › source.scene`, `no scene "${src.scene}"${near(src.scene, scenes)} (scenes.js and the kit have: ${list(scenes)})`);
      if (s.overlay != null && !scenes.has(s.overlay))
        say(bag, L, `${at} › overlay`, `no scene "${s.overlay}"${near(s.overlay, scenes)} (scenes.js and the kit have: ${list(scenes)})`);
      if (s.overlay != null && !(src.clip != null || src.still != null))
        say(bag, L, `${at} › overlay`, "an overlay draws over footage: give the segment a clip or still source");
      if (src.card != null) {
        used.add(src.card);
        if (!titles[src.card]) say(bag, L, `${at} › source.card`, `no title "${src.card}"${near(src.card, Object.keys(titles))}`);
      }
      if (src.shot != null && !shots[src.shot])
        say(bag, L, `${at} › source.shot`, `no shot "${src.shot}" in reel.json → shots${near(src.shot, Object.keys(shots))}`);
      for (const k of ["clip", "still"])
        if (src[k] != null && !exists(src[k])) say(bag, L, `${at} › source.${k}`, `${src[k]} doesn't exist`);
      (src.grid || []).forEach((g, j) => {
        const f = String(g).split("@")[0];
        if (f && !exists(f)) say(bag, L, `${at} › source.grid[${j}]`, `${f} doesn't exist (vs collage makes the tiles)`);
      });
      (s.titles || []).forEach((tt, j) => {
        if (!Array.isArray(tt)) return;
        const [id, a, b] = tt,
          w = `${at} › titles[${j}]`;
        used.add(id);
        if (!titles[id]) say(bag, L, w, `no title "${id}"${near(id, Object.keys(titles))}`);
        if (len > 0 && Number.isFinite(len / unit)) {
          const n = len / unit,
            u = unit === 1 ? "s" : " beats";
          if (a > n + 1e-6) say(bag, L, w, `starts at ${a}${u}, after its segment ends (${+n.toFixed(3)}${u})`);
          if (b !== "end" && b > n + 1e-6) say(bag, L, w, `ends at ${b}${u}, after its segment ends (${+n.toFixed(3)}${u}): use "end"`);
          if (b !== "end" && b <= a) say(bag, L, w, `ends (${b}) before it starts (${a})`);
        }
      });
      if (len > 0) t += len;
    });
    for (const [id, tt] of Object.entries(titles)) {
      if (!used.has(id)) say(warnings, L, `titles.${id}`, "never shown: no segment uses it");
      // an emphasis whose word isn't in its title shows nothing, silently ("word" must match with its punctuation)
      const em = typeof tt.em === "string" ? { fx: tt.em } : tt.em;
      if (!em || !EM_FX.includes(em.fx)) continue;
      const words = String(tt.text ?? "")
        .replace(/<br\s*\/?>/gi, " ")
        .replace(/<[^>]+>/g, " ")
        .split(/\s+/)
        .filter(Boolean);
      if (em.word ? !words.includes(em.word) : !/class=["']?a[\s"'>]/.test(String(tt.text ?? "")))
        say(bag, L, `titles.${id}.em`, em.word ? `"${em.word}" isn't a word of the title (punctuation counts): ${list(words)}` : 'nothing to land on: no <span class=a> word and no "word"');
    }
    // media: the clock, the shots' frames, and any picture a scene names
    if (R.music?.file && !exists(R.music.file)) say(bag, L, "music.file", `${R.music.file} doesn't exist yet (vs music, or bring your own track: vs ingest --as music)`);
    // a page the human ruled out (reel.json → "never"), or whose headline IS the closing line: showing it spends the end
    const nrm = (u) => String(u || "").replace(/[#?].*$/, "").replace(/\/+$/, "").toLowerCase(),
      NEVER = new Set((R.never || []).map(nrm));
    for (const [k, sh] of Object.entries(shots))
      if (sh.url && NEVER.has(nrm(sh.url))) say(bag, L, `shots.${k}.url`, `${sh.url} is in "never": that page can't be on screen`);
    for (const [k, sh] of Object.entries(shots)) {
      for (const f of ["dir", "video"]) if (sh[f] && !exists(sh[f])) say(bag, L, `shots.${k}.${f}`, `${sh[f]} doesn't exist`);
      if (!sh.dir && !sh.video && !sh.url) say(bag, L, `shots.${k}`, "needs a url to record, or a dir / video you recorded");
    }
    const walk = (v, p) => {
      if (typeof v === "string" && /\.(jpe?g|png|webp|gif|svg|mp4|mov)$/i.test(v) && !/^https?:/.test(v) && !exists(v))
        say(bag, L, p, `${v} doesn't exist`);
      else if (v && typeof v === "object") for (const [k, x] of Object.entries(v)) walk(x, `${p}${Array.isArray(v) ? `[${k}]` : "." + k}`);
    };
    walk(R.scenes || {}, "scenes");
  }

  // ── plan.json: word specs against the words file, the way vs plan reads them ──
  function planRules(P, bag) {
    const L = "plan.json";
    if (Array.isArray(P.size) && !SIZES.some(([w, h]) => w === P.size[0] && h === P.size[1]))
      say(warnings, L, "size", `[${P.size}]: the kit lays out ${SIZES.map((s) => s.join("×")).join(" and ")}`);
    const titles = P.titles || {},
      scenes = availableScenes({ scene_lib: "explainer" }, dir);
    if (P.voice && !exists(P.voice)) say(bag, L, "voice", `${P.voice} doesn't exist yet (vs narrate)`);
    if (!P.words || !exists(P.words)) {
      say(bag, L, "words", `${P.words} doesn't exist yet (vs narrate writes it): word specs not checked`);
      return;
    }
    const WORDS = JSON.parse(fs.readFileSync(path.join(dir, P.words), "utf8"));
    const at = (spec, acts) => {
      const r = wordAt(WORDS, spec, acts);
      if (r.err && r.pool) r.err += near(String(spec).replace(/^\d+:|#\d+|[+-][\d.]+$/g, ""), new Set(r.pool.map((w) => w.w.replace(/[^\w'-]/g, ""))));
      return r;
    };
    const lead = P.lead ?? 0.3,
      first = (a) => Math.min(...WORDS.filter((w) => w.act === a).map((w) => w.t0));
    (P.segments || []).forEach((s, i) => {
      const w0 = `segments[${i}] "${s.name}"`,
        acts = s.acts || [];
      if (s.source?.scene && !scenes.has(s.source.scene))
        say(bag, L, `${w0} › source.scene`, `no scene "${s.source.scene}"${near(s.source.scene, scenes)} (scenes.js and the kit have: ${list(scenes)})`);
      let start = null;
      if (i && acts.length) {
        if (s.start) {
          const r = at(s.start, acts);
          if (r.err) say(bag, L, `${w0} › start`, r.err);
          else start = r.t - lead;
        } else start = first(acts[0]) - lead;
      }
      const pin = (spec, p) => {
        const r = at(spec, acts);
        if (r.err) say(bag, L, `${w0} › ${p}`, r.err);
        else if (start != null && r.t < start) {
          const [, base, n, sh] = String(spec).match(/^(.*?)(?:#(\d+))?([+-][\d.]+)?$/);
          say(bag, L, `${w0} › ${p}`, `"${spec}" matches act ${r.w.act}'s "${r.w.w}" at ${r.t.toFixed(2)}s, before this segment starts (${start.toFixed(2)}s): try "${base}#${+(n || 1) + 1}${sh || ""}"`);
        }
        return r.t;
      };
      for (const [k, spec] of Object.entries(s.cues || {})) pin(spec, `cues.${k}`);
      (s.titles || []).forEach(([id, a, b], j) => {
        if (!titles[id]) say(bag, L, `${w0} › titles[${j}]`, `no title "${id}"${near(id, Object.keys(titles))}`);
        const ta = pin(a, `titles[${j}][1]`),
          tb = b === "end" ? Infinity : pin(b, `titles[${j}][2]`);
        if (ta != null && tb != null && tb <= ta + 1.5)
          say(bag, L, `${w0} › titles[${j}]`, `ends at "${b}" ${(tb - ta).toFixed(2)}s after it starts at "${a}": a word that matched too early never lets it leave`);
      });
    });
    for (const p of P.punches || []) {
      const r = at(p, Array.from({ length: 19 }, (_, k) => k + 1));
      if (r.err) say(bag, L, "punches", r.err);
    }
  }

  // ── narration.txt: eleven_v4 PERFORMS a described vocal action instead of saying it ("clears its throat" came back as
  //    an "ahem", the words missing, on two takes): say so unless the sound is the point. [bracketed] tags are direction.
  function narrationRules(text) {
    const VOCAL =
      /\b(clears? (?:his|her|its|their|my|your) throat|sigh(?:s|ed)?|laugh(?:s|ed)?|chuckles?|giggles?|cough(?:s|ed)?|whispers?|gasps?|sneezes?|yawns?|groans?|sniffs?|hums?)\b/gi;
    text
      .split(/\n\s*\n/)
      .filter((b) => b.trim())
      .forEach((act, i) => {
        const spoken = act.replace(/\[[^\]]*\]/g, " ");
        for (const m of spoken.matchAll(VOCAL))
          say(warnings, "narration.txt", `act ${i + 1}`, `"${m[0]}" is a vocal action: the voice performs it instead of saying it (an "ahem" for "clears its throat"); keep it only if the sound is the point`);
      });
  }

  // ── what's here ──
  const has = (f) => fs.existsSync(path.join(dir, f));
  if (has("narration.txt")) narrationRules(fs.readFileSync(path.join(dir, "narration.txt"), "utf8"));
  if (has("plan.json")) {
    const r = validate("plan.json", path.join(dir, "plan.json"), "plan", { versioned: true });
    if (r?.doc) planRules(r.doc, r.bag);
  }
  if (has("reel.json")) {
    const r = validate("reel.json", path.join(dir, "reel.json"), "reel", { versioned: true });
    if (r?.doc) reelRules(forShape(r.doc, activeShape(dir)), r.bag); // the reel as the shape being built sees it
  } else if (!has("plan.json")) say(errors, "reel.json", "", "not found: run from a project folder (or vs plan, for an explainer)");
  for (const [f, s] of [
    ["music.json", "music"],
    ["sfx.json", "sfx"],
    ["mix.json", "mix"],
    ["media.json", "media"],
    ["music/takes.json", "takes"],
    ["review/state.json", "review"],
    ["video.json", "video"],
  ])
    if (has(f)) validate(f, path.join(dir, f), s);
  if (S) {
    for (const [f, s] of [
      ["profile.json", "profile"],
      ["studio.json", "studio"],
      ["library/sfx/index.json", "sounds"],
      ["library/music/index.json", "media"],
      ["library/media/index.json", "media"],
      ["library/brand/index.json", "media"],
    ])
      if (fs.existsSync(path.join(S, f))) validate(`studio › ${f}`, path.join(S, f), s);
  }
  if (!quiet) {
    errors.forEach((e) => console.log(`✗ ${e}`));
    warnings.forEach((w) => console.log(`⚠ ${w}`));
    console.log(
      errors.length
        ? `${errors.length} error${errors.length > 1 ? "s" : ""}, ${warnings.length} warning${warnings.length === 1 ? "" : "s"} in ${files} files`
        : `✓ ${files} files check out${warnings.length ? ` (${warnings.length} warning${warnings.length > 1 ? "s" : ""})` : ""}`,
    );
  }
  return { errors, warnings, files };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { errors } = check();
  process.exit(errors.length ? 1 : 0);
}
