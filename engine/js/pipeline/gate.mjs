// Build step 8, the render gate: a render costs minutes, so it waits until vs inspect has looked at THIS composition,
// the whole of it, and found no open errors. The cheap-first ladder, each rung cheaper than the one after it:
//   vs build --no-render → vs inspect → vs build --storyboard (or vs snap) → vs build
// `vs build --anyway` renders past open errors and says so. A finding dismissed in review (review/state.json →
// findings.<id>.status "dismissed") no longer blocks.
import fs from "node:fs";
import { TIMELINE, FINDINGS } from "../lib/paths.mjs";
import { ARGS, die, OUT } from "./context.mjs";

// Versions are never overwritten: a review round plays them, Compare puts an old one beside its answer, and a final is
// one of them. A render onto an existing version stops and says to bump the number (Oct 1, 2026: a re-render without
// the bump silently replaced the v1 a review round was looking at). --replace renders over one nobody has reviewed.
function fresh() {
  if (!fs.existsSync(OUT)) return;
  const bump = `bump "version" in ${fs.existsSync("plan.json") ? "plan.json (then vs plan)" : "reel.json"}`;
  let used = false;
  try {
    const base = OUT.replace(/\.mp4$/, "");
    used = JSON.parse(fs.readFileSync("review/state.json", "utf8")).rounds.some((r) => r.video.replace(/-(take\d+|sfx|mixed)\.mp4$/, "").replace(/\.mp4$/, "") === base);
  } catch {}
  if (used) die(`${OUT} exists and a review round played it: versions are never overwritten. ${bump}`);
  if (!ARGS.includes("--replace")) die(`${OUT} exists: versions are never overwritten. ${bump}, or vs build --replace (nobody has reviewed it)`);
  console.log(`  ⚠️  replacing ${OUT} (--replace; no review round has played it)`);
}

export function gate() {
  fresh();
  const ANYWAY = ARGS.includes("--anyway"),
    tl = JSON.parse(fs.readFileSync(TIMELINE, "utf8")),
    ladder = "vs build --no-render → vs inspect → vs build --storyboard → vs build";
  const stop = (msg) => {
    if (!ANYWAY) die(`${msg}\n   the ladder: ${ladder}   (vs build --anyway renders regardless)`);
    console.log(`  ⚠️  ${msg} — rendering anyway (--anyway)`);
  };
  if (!fs.existsSync(FINDINGS)) return stop("not inspected yet: vs inspect looks at the composition first");
  const F = JSON.parse(fs.readFileSync(FINDINGS, "utf8"));
  if (F.fingerprint !== tl.fingerprint)
    return stop("the composition changed since vs inspect last looked at it: run vs inspect again");
  if (!(F.range?.[0] <= 0.05 && F.range?.[1] >= tl.end - 0.05))
    return stop(`vs inspect only looked at ${F.range?.[0]}–${F.range?.[1]}s: run it over the whole video`);
  let dismissed = {};
  try {
    dismissed = JSON.parse(fs.readFileSync("review/state.json", "utf8")).findings || {};
  } catch {}
  const open = F.items.filter((f) => f.severity === "error" && dismissed[f.id]?.status !== "dismissed");
  if (open.length)
    return stop(
      `${open.length} open error${open.length > 1 ? "s" : ""} from vs inspect (${FINDINGS}), first: ${open[0].check} ` +
        `${open[0].elements.join(" × ")} at ${open[0].t0.toFixed(1)}s`,
    );
  const n = F.items.filter((f) => f.severity === "error").length - open.length; // errors dismissed in review
  console.log(`  render gate: inspected, no open errors${n ? ` (${n} dismissed in review)` : ""}`);
}
