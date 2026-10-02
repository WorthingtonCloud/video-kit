// Build step 1, the timing: every segment and title on the music's grid (an explainer's grid is the voice's word times).
// Worked out here ONCE. compose.mjs writes it to build/timeline.json beside the composition, and everything downstream
// (inspect, snap, mix, music, qa, the review page) reads that file instead of summing reel.json on its own: four copies
// of this sum once disagreed, and a beat-timed reel was audited at zero frames (1.0.1).
import fs from "node:fs";
import { R, W, H, FPS, B, HIT, die } from "./context.mjs";
import { timeSegments } from "../lib/time.mjs";
import { hash, engineHash } from "../lib/paths.mjs";

// ───────── timing: every segment on the music's grid (lib/time.mjs) ─────────
let timed;
try {
  timed = timeSegments(R);
} catch (e) {
  die(e.message);
}
export const SEGS = timed.segs,
  END = timed.end;

// build/timeline.json: when every segment, title and word-pinned cue happens, in seconds. "fingerprint" is the
// composition it was built with (a reader checks it, so a stale file is caught); "reel" is the reel.json it was timed
// from (Python checks that, since it never opens the composition); "engine" is the runtime it was built by (a build
// from before a kit update can't be read by the newer inspect).
export function timeline(fingerprint) {
  return {
    timeline: 1,
    fingerprint,
    reel: hash(fs.readFileSync("reel.json")),
    engine: engineHash(),
    name: R.name,
    version: R.version || 1,
    size: [W, H],
    fps: FPS,
    beat: B,
    first_hit: Number.isFinite(HIT) ? HIT : null,
    end: END,
    segments: SEGS.map(({ name, t0, t1, in: inn, source }) => ({
      name,
      t0,
      t1,
      in: inn,
      kind: Object.keys(source)[0],
      ...(source.scene ? { scene: source.scene } : {}),
    })),
    titles: SEGS.flatMap((s) => s.titles.map(({ id, t0, t1 }) => ({ id, el: `title/${id}`, segment: s.name, t0, t1 }))),
    // a narrated video's acts, first word to last (plan.py writes them into reel.json)
    voice: (R.acts || []).map(({ act, t0, t1 }) => ({ act, el: `voice/act-${act}`, t0, t1 })),
    // every scene's word-pinned cues (an explainer's plan.py pins them to the voice), absolute seconds
    cues: Object.fromEntries(Object.entries(R.scenes || {}).map(([k, v]) => [k, v?.cues || {}])),
    punches: R.punches || [],
  };
}
