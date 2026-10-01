// Build step 0, the context every step reads: the reel (with the studio's brand filled in), its size and palette,
// where things go, and the small helpers (run a tool, cut with ffmpeg, only redo work whose inputs changed).
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { loadReel, NODE_MODULES, COMP as COMP_DIR, QA } from "../lib/paths.mjs";

export const ARGS = process.argv.slice(2),
  STORY = ARGS.includes("--storyboard"),
  NORENDER = ARGS.includes("--no-render") || STORY;
export const R = loadReel(),
  [W, H] = R.size,
  FPS = R.fps || 30,
  LAND = W > H,
  P = R.palette;
export const M = R.music,
  B = +M.beat,
  HIT = +M.first_hit;
export const COMP = COMP_DIR,
  A = `${COMP}/assets`,
  OUT = `out/${R.name}-v${R.version || 1}.mp4`;
for (const d of [A, `${A}/tiles`, `${A}/fonts`, "out", QA]) fs.mkdirSync(d, { recursive: true });
export const env = { ...process.env, HYPERFRAMES_NO_TELEMETRY: "1", DO_NOT_TRACK: "1", HYPERFRAMES_SKIP_SKILLS: "1" };
export const die = (msg) => {
  console.error(`⛔ ${msg}`);
  process.exit(1);
};
export const run = (cmd, args, opts = {}) => {
  const r = spawnSync(cmd, args, { stdio: "inherit", env, ...opts });
  if (r.status !== 0) die(`${cmd} ${args.slice(0, 3).join(" ")} … failed`);
};
export const ff = (...a) => run("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...a]);
// HyperFrames from the engine's own install (vs setup), so a project folder carries no packages
export const hf = (args) =>
  run(path.join(NODE_MODULES, ".bin", process.platform === "win32" ? "hyperframes.cmd" : "hyperframes"), args, {
    cwd: COMP,
  });
export const probe = (f) =>
  +spawnSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], {
    encoding: "utf8",
  }).stdout.trim();
export const r3 = (x) => Math.round(x * 1000) / 1000;
export const hex6 = (c) => (/^#[0-9a-f]{3}$/i.test(c) ? "#" + [...c.slice(1)].map((x) => x + x).join("") : c);
for (const k in P) P[k] = hex6(P[k]);

// Only redo work whose inputs changed: each output keeps a small .key file describing what made it.
export const fresh = (out, key) =>
  fs.existsSync(out) && fs.existsSync(out + ".key") && fs.readFileSync(out + ".key", "utf8") === key;
export const stamp = (out, key) => fs.writeFileSync(out + ".key", key);
export const mtime = (f) => (fs.existsSync(f) ? fs.statSync(f).mtimeMs : 0);
export const copy = (from, to) => {
  if (!fs.existsSync(from)) die(`${from} not found`);
  if (mtime(to) < mtime(from) || fs.statSync(to).size !== fs.statSync(from).size) fs.copyFileSync(from, to);
};
