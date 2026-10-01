// Where things live. Three places, kept apart on purpose:
//   the kit     this engine, read-only: code, the scene library, the bundled sounds, the templates
//   the studio  everything the user keeps between videos: profile.json (their settled choices), lessons.md, the library
//               (sounds, music beds, brand, reusable media, promoted scenes), finals/, ledger.csv
//   a project   one video inside the studio (studio/projects/<slug>); every script runs with it as the working folder.
//               Its build/ folder (comp, qa, mix, rec, mixer) is regenerated and safe to delete.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ENGINE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const KIT = path.dirname(ENGINE);
export const NODE_MODULES = path.join(ENGINE, "node_modules");
export const BUILD = "build";
export const COMP = "build/comp";
export const QA = "build/qa";
export const REC = "build/rec";

// The studio: $VIDEO_STUDIO, else the nearest folder above this one with a studio.json, else the one `vs setup` wrote
// to ~/.config/video-studio/config.json. null = no studio yet (the engine still runs; nothing is filled in from a profile).
export function studioRoot() {
  if (process.env.VIDEO_STUDIO) return path.resolve(process.env.VIDEO_STUDIO);
  for (let d = process.cwd(); ; d = path.dirname(d)) {
    if (fs.existsSync(path.join(d, "studio.json"))) return d;
    if (path.dirname(d) === d) break;
  }
  const cfg = path.join(os.homedir(), ".config", "video-studio", "config.json");
  try {
    const s = JSON.parse(fs.readFileSync(cfg, "utf8")).studio;
    if (s && fs.existsSync(s)) return s;
  } catch {}
  return null;
}

const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);
export function deepMerge(a, b) {
  const out = { ...a };
  for (const [k, v] of Object.entries(b || {})) out[k] = isObj(v) && isObj(a?.[k]) ? deepMerge(a[k], v) : v;
  return out;
}

// The profile: the kit's defaults, overlaid with the studio's profile.json (what this user has settled on).
export function profile() {
  const read = (f) => (fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, "utf8")) : {});
  const S = studioRoot();
  return deepMerge(read(path.join(KIT, "templates/studio/profile.json")), S ? read(path.join(S, "profile.json")) : {});
}

// A font's css (written by fonts.mjs): the studio's library first (downloaded once, shared by every video), then the
// project's own fonts/ folder (older projects kept a copy).
export function fontCss(family) {
  const name = `${String(family).replace(/\W+/g, "")}.css`,
    S = studioRoot();
  for (const f of [S && path.join(S, "library/brand/fonts", name), path.join("fonts", name)])
    if (f && fs.existsSync(f)) return path.resolve(f);
  return null;
}

// Fill what a reel leaves out from the studio's brand: palette, fonts, finish, fps, and the end card. A value the reel
// sets always wins, so a video can break from the house look without touching the profile.
export function withBrand(R) {
  const pr = profile(),
    b = pr.brand || {};
  if (!R.palette && b.palette) R.palette = { ...b.palette };
  for (const k of ["font", "mono"]) {
    if (!R[k] && b[k]?.family) R[k] = { family: b[k].family, css: fontCss(b[k].family) };
    else if (R[k]?.family && (!R[k].css || !fs.existsSync(R[k].css))) R[k].css = fontCss(R[k].family) || R[k].css;
  }
  if (!R.finish && b.finish) R.finish = { ...b.finish };
  if (!R.fps && pr.render?.fps) R.fps = pr.render.fps;
  const usesEnd = (R.segments || []).some((s) => s.source?.scene === "endcard"),
    end = R.scenes?.endcard || (usesEnd ? {} : null);
  if (end && !end.mark && !end.logo && !end.wordmark && b.endcard) {
    const e = { ...b.endcard },
      S = studioRoot();
    if (e.logo && S && !path.isAbsolute(e.logo)) e.logo = path.join(S, e.logo);
    R.scenes = { ...(R.scenes || {}), endcard: { ...e, ...end } };
  }
  return R;
}

// reel.json is the single source of truth for every script (plan.py writes it for an explainer).
// "lib:media/headshot.jpg" anywhere in a reel names a file in the studio's library (vs ingest --to library puts it there).
export function loadReel(file = "reel.json") {
  if (!fs.existsSync(file)) throw new Error(`${file} not found — run from the project folder (vs build does)`);
  const S = studioRoot();
  const lib = (k, v) => (typeof v === "string" && v.startsWith("lib:") && S ? path.join(S, "library", v.slice(4)) : v);
  return withBrand(JSON.parse(fs.readFileSync(file, "utf8"), lib));
}

// A page recording's frames: older projects keep them in rec/<shot>; new ones in build/rec/<shot>.
export const recDir = (name) => (fs.existsSync(path.join("rec", name)) ? path.join("rec", name) : path.join(REC, name));
