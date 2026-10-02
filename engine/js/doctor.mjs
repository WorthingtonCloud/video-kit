// Preflight: run this before anything else (vs doctor; vs setup runs it last), so a missing tool fails here with a plain
// message instead of deep inside a build with a confusing one.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { findPuppeteer, findChrome } from "./lib/browser.mjs";
import { ENGINE, NODE_MODULES, studioRoot, profile, fontCss, findKey } from "./lib/paths.mjs";

const rows = [];
const add = (need, name, ok, detail, fix) => rows.push({ need, name, ok, detail, fix });
const sh = (cmd, args) => {
  try {
    return execFileSync(cmd, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  } catch {
    return null;
  }
};

add("required", "node 22+", Number(process.versions.node.split(".")[0]) >= 22, process.versions.node, "install Node 22 or newer (HyperFrames needs it)");
const ffv = sh("ffmpeg", ["-hide_banner", "-version"]);
const filters = sh("ffmpeg", ["-hide_banner", "-filters"]) || "";
// A stripped ffmpeg reports a missing filter as a syntax error in your command. Check the ones the engine uses.
const needF = ["scale", "crop", "fps", "format", "overlay", "fade", "zoompan", "tpad", "tile", "drawbox", "signalstats", "metadata",
  "ebur128", "ametadata", "setparams", "afade", "atrim", "aformat", "alimiter", "apad", "aresample", "acrossfade", "volume", "hstack", "vstack"];
const encoders = sh("ffmpeg", ["-hide_banner", "-encoders"]) || "";
const missing = [...needF.filter((f) => !new RegExp(`\\s${f}\\s`).test(filters)),
  ...["libx264", "aac", "pcm_s16le", "libmp3lame"].filter((e) => !new RegExp(`\\s${e}\\s`).test(encoders)).map((e) => `${e} encoder`)];
add("required", "ffmpeg (full build)", !!ffv && missing.length === 0,
  ffv ? (missing.length ? `missing: ${missing.join(", ")}` : ffv.split("\n")[0].slice(0, 40)) : "not found",
  "install a full ffmpeg (macOS: brew install ffmpeg · Linux: your package manager, or a static build)");
add("required", "ffprobe", !!sh("ffprobe", ["-version"]), "", "comes with ffmpeg");
add("required", "curl", !!sh("curl", ["--version"]), "", "install curl (the take check uploads with it)");

const hfBin = path.join(NODE_MODULES, ".bin", process.platform === "win32" ? "hyperframes.cmd" : "hyperframes");
const hfv = fs.existsSync(hfBin) ? sh(hfBin, ["--version"]) : null;
add("required", "hyperframes", !!hfv, (hfv || "not installed").trim().split("\n").pop(), "vs setup   (installs the engine's packages once)");
add("required", "gsap", fs.existsSync(path.join(NODE_MODULES, "gsap/dist/gsap.min.js")), "engine/node_modules/gsap", "vs setup");
add("required", "ajv", fs.existsSync(path.join(NODE_MODULES, "ajv/package.json")), "engine/node_modules/ajv (vs check)", "vs setup");
const pp = findPuppeteer();
add("required", "puppeteer", !!pp, pp ? pp.name : "not found", "vs setup");
if (pp?.name === "puppeteer-core") add("required", "Chrome", !!findChrome(), findChrome() || "not found", "set CHROME=/path/to/chrome");

const S = studioRoot();
const sj = S && fs.existsSync(path.join(S, "studio.json")) ? JSON.parse(fs.readFileSync(path.join(S, "studio.json"), "utf8")) : {};
const pys = [process.env.PYTHON, sj.python, path.join(ENGINE, ".venv/bin/python"), "python3"].filter(Boolean);
const py = pys.map((p) => [p, sh(p, ["-c", "import numpy, sys; print(sys.version.split()[0], numpy.__version__)"])]).find(([, v]) => v);
add("required", "python + numpy", !!py, py ? `${py[0]} (${py[1].trim()})` : "no Python with numpy", "vs setup   (makes one for the engine)");

add("required", "studio", !!S, S || "none yet", "vs setup   (where your profile, library, projects and finals live)");
const pr = profile(), b = pr.brand || {};
for (const k of ["font", "mono"]) {
  const fam = b[k]?.family;
  if (fam) add("required", `${k}: ${fam}`, !!fontCss(fam), fontCss(fam) || "not downloaded", `vs fonts "${fam}"`);
}
add("optional", "narrator", !!pr.narrator?.voice, pr.narrator?.voice || "not chosen yet", "vs voices (free previews), then profile.json → narrator.voice");

// keys: the environment, else the nearest .env in this folder or above, the studio's .env, or ~/.config/video-studio/.env
const envKey = (k) => !!findKey(k);
add("paid", "ELEVENLABS_API_KEY", envKey("ELEVENLABS_API_KEY"), "narration, new sound effects", "ElevenLabs → API key → .env (library voices need a paid plan over the API)");
add("paid, optional", "OPENAI_API_KEY", envKey("OPENAI_API_KEY"), "checking a take; word timings for your own narration (about a cent)", "OpenAI → API key → .env");
add("paid, optional", "KIE_AI_API_KEY", envKey("KIE_AI_API_KEY"), "music beds, stills (or bring your own)", "kie.ai → API key → .env");
add("paid, optional", "HIGGSFIELD_API_KEY", envKey("HIGGSFIELD_API_KEY"), "Seedance clips (sizzle reels)", "Higgsfield → API key → .env");

let bad = 0;
for (const r of rows) {
  const mark = r.ok ? "✓" : r.need === "required" ? "✗" : "·";
  if (!r.ok && r.need === "required") bad++;
  console.log(`${mark} ${r.name.padEnd(22)} ${r.need.padEnd(15)} ${r.ok ? r.detail : `${r.detail} → ${r.fix}`}`);
}
console.log(bad ? `\n${bad} required item(s) missing.` : "\nReady. Drawing, the checks (vs inspect), the mix and anything you bring cost nothing; voices, music, new sounds and clips are paid, and each asks first.");
console.log("HyperFrames telemetry: vs build turns it off (HYPERFRAMES_NO_TELEMETRY=1). Running hyperframes by hand? Set it yourself.");
process.exit(bad ? 1 : 0);
