// Checks vs inspect makes from its own element map once the scrub is done (no extra browser work). Both are warnings:
// each has a reason to be by design, so the human confirms or dismisses it in Review Studio.
//   fast-text          words on screen for less time than it takes to read them: words ÷ reading speed, never under the
//                      shortest title that read (contracts.json → reading; profile.json → checks tunes both)
//   offscreen-at-rest  something parked partly off the frame, not moving, for a second or more (Sep 30, 2026: 15 of the
//                      "twenty people" parked off a vertical frame through v3; an exit sized for a vertical frame stopped
//                      in plain sight on the wide cut)
// META[i] = {addr, kind, text, up}; seenAt = [[t, [[i, x0, y0, x1, y1], …]], …] in fractions of the frame.

const words = (s) => (String(s || "").match(/[\p{L}\p{N}][\p{L}\p{N}'’.,%$-]*/gu) || []).length;
const area = (b) => Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]);

// the words a person reads: an element with words that holds no other element with words (a card holding its label
// is read once, as the label)
function readers(META) {
  const holds = new Set();
  META.forEach((m) => {
    if (!m.text) return;
    const seen = new Set();
    for (let u = m.up; u && !seen.has(u); u = META.find((x) => x.addr === u)?.up) {
      seen.add(u);
      holds.add(u);
    }
  });
  return META.map((m, i) => [m, i]).filter(([m]) => m.text && words(m.text) && !holds.has(m.addr) && !m.addr.startsWith("frame/"));
}

// when each element is on screen, as spans of consecutive moments
function spans(seenAt, STEP) {
  const on = new Map();
  seenAt.forEach(([t, els]) => {
    for (const [i] of els) {
      const L = on.get(i) || [];
      const last = L.at(-1);
      if (last && t - last[1] <= STEP * 1.5) last[1] = t;
      else L.push([t, t]);
      on.set(i, L);
    }
  });
  return on;
}

// an element's box (normalized) at the mapped moment nearest t: what a finding's still and Review Studio outline
function boxAt(seenAt, i, t) {
  let best = null, d = Infinity;
  for (const [tt, els] of seenAt) {
    if (Math.abs(tt - t) >= d) continue;
    const e = els.find(([j]) => j === i);
    if (e) (best = e.slice(1)), (d = Math.abs(tt - t));
  }
  return best;
}

export function fastText({ META, seenAt, STEP, C, END, near }) {
  const on = spans(seenAt, STEP),
    out = [];
  for (const [m, i] of readers(META)) {
    const n = words(m.text),
      title = m.addr.startsWith("title/"),
      need = Math.max(title ? C.title_min_secs : 0, n / C.words_per_sec);
    for (const [a, b] of on.get(i) || []) {
      const secs = b - a + STEP;
      if (b >= END - STEP * 1.5) continue; // on until the end: the video stops, the words don't leave
      if (near(a) || near(b)) continue; // arriving or leaving with its scene: the transition is the reading time's edge
      const at = +((a + b) / 2).toFixed(2),
        bx = boxAt(seenAt, i, at);
      if (secs + STEP < need)
        out.push({
          check: "fast-text",
          elements: [m.addr],
          text: `${n} word${n > 1 ? "s" : ""} on screen ${secs.toFixed(1)}s; reading them takes ${need.toFixed(1)}s (“${m.text.slice(0, 40)}”)`,
          t0: a,
          t1: b,
          at,
          ...(bx ? { box_n: bx.map((v) => +v.toFixed(4)) } : {}),
          hint: `give it ${need.toFixed(1)}s, or fewer words (${C.words_per_sec} words a second${title ? `, a title at least ${C.title_min_secs}s` : ""}: profile.json → checks)`,
        });
    }
  }
  return out;
}

export function parked({ META, seenAt, STEP, C, near }) {
  const out = [],
    holders = new Set(META.map((m) => m.up).filter(Boolean)),
    runs = new Map(); // i → current run {t0, t1, box}
  const finish = (i, r) => {
    if (r && r.t1 - r.t0 + STEP >= C.offscreen_rest_secs) {
      const b = r.box,
        m = META[i];
      out.push({
        check: "offscreen-at-rest",
        elements: [m.addr],
        text: `parked partly off the frame for ${(r.t1 - r.t0 + STEP).toFixed(1)}s (${Math.round(100 * r.inside)}% of it shows)`,
        t0: r.t0,
        t1: r.t1,
        at: +((r.t0 + r.t1) / 2).toFixed(2),
        box_n: b.map((v) => +v.toFixed(4)),
        hint: "a resting element half off the frame reads as a mistake: bring it in, or take it all the way out (an exit sized for the other cut?)",
      });
    }
  };
  seenAt.forEach(([t, els]) => {
    const now = new Set();
    for (const [i, ...b] of els) {
      const m = META[i];
      if (m.addr.startsWith("frame/") || holders.has(m.addr) || area(b) > 0.35) continue;
      const inside = area([Math.max(0, b[0]), Math.max(0, b[1]), Math.min(1, b[2]), Math.min(1, b[3])]) / (area(b) || 1);
      const off = b[0] < -0.005 || b[1] < -0.005 || b[2] > 1.005 || b[3] > 1.005;
      if (!off || inside < 0.05 || inside > 0.95 || near(t)) continue;
      now.add(i);
      // at rest: no faster than a slow drift (an explainer's camera breathes, ~1 px a step) from one moment to the next
      const r = runs.get(i),
        still = r && t - r.t1 <= STEP * 1.5 && b.every((v, k) => Math.abs(v - r.last[k]) <= 0.004);
      if (still) (r.t1 = t), (r.last = b);
      else {
        finish(i, r);
        runs.set(i, { t0: t, t1: t, box: b, last: b, inside });
      }
    }
    for (const [i, r] of runs) if (!now.has(i)) finish(i, r), runs.delete(i);
  });
  for (const [i, r] of runs) finish(i, r);
  return out;
}

// Dead air: nothing on screen but the backdrop (the frame, its light, its dust) for a stretch: a scene waiting for its
// word, a handoff left empty. Oct 1, 2026: three ~1 s stretches in the Jev explainer survived 45 stills and four inspect
// passes; this scan of the map found all three. A blink at a cut is the transition, not dead air: a stretch must last
// C.dead_air_secs, and one that never leaves a cut's window is skipped.
const AMBIENT = /(^frame\/)|\/~ex-(spot|mote|dust)(#\d+)?$/;
export function deadAir({ META, seenAt, STEP, C, cuts = [] }) {
  const content = (els) =>
    els.some(([i, ...b]) => {
      const m = META[i];
      if (AMBIENT.test(m.addr)) return false;
      return !!m.text || !(["group", "box"].includes(m.kind) && area(b) >= 0.6); // an empty full-frame box is a backdrop
    });
  const out = [],
    inCut = (t) => cuts.some((c) => t > c - 0.5 && t < c + 0.6);
  let run = null;
  const finish = () => {
    if (!run) return;
    const secs = run[1] - run[0] + STEP;
    if (secs >= C.dead_air_secs && !(inCut(run[0]) && inCut(run[1]) && run[1] - run[0] < 1.1))
      out.push({
        check: "dead-air",
        elements: [],
        text: `nothing on screen but the backdrop for ${secs.toFixed(1)}s`,
        t0: run[0],
        t1: run[1],
        at: +((run[0] + run[1]) / 2).toFixed(2),
        hint: "bring the next thing in sooner (a panel waiting for its word can arrive with the line before), or hold what was there until it does",
      });
    run = null;
  };
  for (const [t, els] of seenAt) {
    if (content(els)) finish();
    else if (run && t - run[1] <= STEP * 1.5) run[1] = t;
    else (finish(), (run = [t, t]));
  }
  finish();
  return out;
}
