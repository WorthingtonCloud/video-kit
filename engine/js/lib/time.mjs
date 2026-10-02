// Every segment and title on the music's grid (an explainer's grid is the voice's word times), worked out once. The
// build times with it (pipeline/timing.mjs), and Python's fallback (vslib.timeline) must agree with it to the
// millisecond: tests/contract/cases.json holds both to the same answers.
export const r3 = (x) => Math.round(x * 1000) / 1000;

// A segment lasts "secs", or "beats" × the music's beat, or (to_hit) until the music's first hit; its title times count
// in the segment's own unit ("end" = the segment's end). Throws on a length that isn't positive.
export function timeSegments(R) {
  const B = +R.music.beat,
    HIT = +R.music.first_hit;
  let t = 0;
  const segs = R.segments.map((seg, i) => {
    const unit = seg.to_hit || seg.secs != null ? 1 : B;
    const len = seg.to_hit ? HIT - t : seg.secs != null ? +seg.secs : +seg.beats * B;
    if (!(len > 0)) throw new Error(`${seg.name}: length ${len}s (a to_hit segment must come before the hit)`);
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
  return { segs, end: r3(t) };
}
