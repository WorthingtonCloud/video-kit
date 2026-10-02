// One place that finds a headless Chrome, so every script launches it the same way.
// Order: `puppeteer` (bundles its own Chrome) or `puppeteer-core` installed in the engine (vs setup), then the project
// folder, then PUPPETEER_FROM (a package.json whose node_modules holds either one). Chrome for puppeteer-core comes
// from CHROME, else the usual install paths.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { ENGINE, loadReel } from "./paths.mjs";

export { loadReel };

const CHROMES = [
  process.env.CHROME,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
].filter(Boolean);

export function findPuppeteer() {
  const bases = [path.join(ENGINE, "package.json"), path.join(process.cwd(), "package.json"), process.env.PUPPETEER_FROM].filter(Boolean);
  for (const base of bases) {
    for (const name of ["puppeteer", "puppeteer-core"]) {
      try {
        return { pp: createRequire(base)(name), name, base };
      } catch {}
    }
  }
  return null;
}

export function findChrome() {
  return (
    CHROMES.find((p) => {
      try {
        return fs.existsSync(p);
      } catch {
        return false;
      }
    }) || null
  );
}

export async function launch() {
  const found = findPuppeteer();
  if (!found) {
    throw new Error(
      "No puppeteer found. Run: vs setup   (it installs the engine's packages; or set PUPPETEER_FROM to a package.json that has it)",
    );
  }
  // protocolTimeout: every call here takes milliseconds; a rare hang (twice on Oct 1, 2026, cause not yet caught) used to
  // sit out puppeteer's 180 s default before failing
  const opts = { headless: true, protocolTimeout: 60_000, args: ["--hide-scrollbars", "--font-render-hinting=none"] };
  const chrome = findChrome();
  if (found.name === "puppeteer-core") {
    if (!chrome) throw new Error("puppeteer-core needs a Chrome: set CHROME=/path/to/chrome");
    opts.executablePath = chrome;
  } else if (process.env.CHROME) {
    opts.executablePath = process.env.CHROME;
  }
  return found.pp.launch(opts);
}

// A browser call that stalls or fails says which step it was: puppeteer's own stack ends inside puppeteer, so the
// failure used to name no step of ours (three one-off stalls on Oct 1, 2026, each a 60 s protocol timeout).
export async function step(label, call) {
  try {
    return await call();
  } catch (e) {
    throw new Error(`the browser stalled or failed at: ${label} (${String(e.message).split("\n")[0]})`);
  }
}

export function isLandscape(reel) {
  const [w, h] = reel.size;
  return w > h;
}
