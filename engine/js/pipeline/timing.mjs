// Build step 1, the timing: every segment and title on the music's grid (an explainer's grid is the voice's word times).
import { R, B, HIT, die, r3 } from "./context.mjs";

// ───────── timing: every segment on the music's grid ─────────
let t = 0;
export const SEGS = R.segments.map((seg, i) => {
  const unit = seg.to_hit || seg.secs != null ? 1 : B;
  const len = seg.to_hit ? HIT - t : seg.secs != null ? +seg.secs : +seg.beats * B;
  if (!(len > 0)) die(`${seg.name}: length ${len}s (a to_hit segment must come before the hit)`);
  const s = {
    name: seg.name,
    t0: r3(t),
    t1: r3(t + len),
    in: i ? seg.in || "whip" : "cut",
    source: seg.source,
    push: seg.push,
    scrim: seg.scrim,
    fx: seg.fx,
    titles: (seg.titles || []).map(([id, a, b]) => ({
      id,
      t0: r3(t + a * unit),
      t1: r3(b === "end" ? t + len : t + b * unit),
    })),
  };
  t += len;
  return s;
});
export const END = r3(t);
