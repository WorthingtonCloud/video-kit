// Explainer scene library, part 1 of 4: the look (CSS), the helpers (ex*) and the overlap rules. build inlines
// scenes/base.js, icons.js, props.js, then the studio's own library scenes, then the project's scenes.js, then layout.js,
// into the renderer at /*__EXTRA_SCENES__*/, so everything shares the renderer's helpers: tl, ticks, svg, div, tw3, punch,
// easeOut, easeInOut, clamp, IR, TP, mulberry32, P (the palette), and W, H, LAND (true on a widescreen cut).
// Names: div(cls, parent, html, style, name), svg(tag, attrs, parent, name), exName(el, name), and the ex* helpers' last
// argument name what a reviewer will point at ("tier-episodic-label"); the rest gets a derived name (js/reel/55-names.js).
// The voice is the clock: every cue in R.scenes.<scene>.cues is the absolute time of a word the narrator says (plan.py).
// Look: flat diagrams (3px rules, near-square panels, mono kickers, one accent color) lit like a dark room: one soft
// spotlight, dust in the light. Motion carries the meaning; words live in the title zone (below the picture on a vertical
// cut, left of it on a widescreen one).
// Rules as in the renderer: everything a pure function of time, 1080×1400 design space, content above design y ≈ 1130,
// a first tween paints its start state at load (entrances), every later tween on the same property uses IR.
// "#e8402c" → "232,64,44", for an rgba() in the accent color
const exRGB = (hex) => {
  const h = hex.replace("#", ""),
    f = h.length === 3 ? [...h].map((c) => c + c).join("") : h;
  return [0, 2, 4].map((i) => parseInt(f.slice(i, i + 2), 16)).join(",");
};
const exM = R.mono?.family || "monospace",
  GREEN = "#3fb950",
  KIT_SCENES = new Set(Object.keys(SCENES));
// a move that must LEAVE the frame: a widescreen frame is about twice as wide in scene units, so a vertical-sized
// exit (Joe walking 1000 to the right) stops in plain sight on it. Multiply every exit distance by EXIT.
const EXIT = LAND ? 2 : 1;
{
  const css = document.createElement("style");
  css.textContent = `
  .ex-p{position:absolute;background:linear-gradient(180deg,#212227 0%,${P.card} 42%);border:3px solid ${P.line};border-radius:8px;box-shadow:0 50px 120px rgba(0,0,0,.72),inset 0 1px 0 rgba(255,255,255,.06)}
  .ex-k{position:absolute;font-family:"${exM}",monospace;font-size:22px;font-weight:700;letter-spacing:.16em;color:${P.dim};white-space:nowrap}
  .ex-k.red{color:${P.accent}}.ex-k.green{color:${GREEN}}
  .ex-t{position:absolute;font-weight:700;color:${P.ink};white-space:nowrap}
  .ex-m{position:absolute;font-family:"${exM}",monospace;font-weight:700;color:${P.ink};white-space:nowrap;font-variant-numeric:tabular-nums}
  .ex-spot{position:absolute;border-radius:50%;pointer-events:none;background:radial-gradient(closest-side,rgba(255,255,255,.12),rgba(255,255,255,.045) 50%,rgba(255,255,255,0))}
  .ex-glow{position:absolute;border-radius:50%;pointer-events:none;background:radial-gradient(closest-side,rgba(${exRGB(P.accent)},.62),rgba(${exRGB(P.accent)},.16) 45%,rgba(${exRGB(P.accent)},0))}
  .ex-mote{position:absolute;left:0;top:0;border-radius:50%;background:#fff}
  .ex-chip{position:absolute;padding:8px 18px;border-radius:6px;border:3px solid ${P.line};background:#18191d;font-family:"${exM}",monospace;font-weight:700;font-size:24px;letter-spacing:.12em;color:${P.ink};white-space:nowrap}
  .ex-chip.red{border-color:${P.accent};background:#331918}
  .ex-chip.green{border-color:${GREEN};background:#17271c;color:${GREEN}}
  .ex-blk{position:absolute;border-radius:5px;border:3px solid ${P.line};background:#24252b;display:flex;align-items:center;padding:0 18px;font-weight:700;color:${P.ink};white-space:nowrap;overflow:hidden}
  .ex-bar{position:absolute;height:44px;border-radius:4px;transform-origin:0 50%}
  .ex-ic{position:absolute;display:block}
  .ex-clip{position:absolute;overflow:hidden}
  `;
  document.head.appendChild(css);
}

// the room's light: one soft spotlight, breathing, and dust hanging in it (seeded; a pure function of time)
function exLight(stage, x, y, r, seg, n = 26, seed = 7) {
  const s = div("ex-spot", stage, "", `left:${x - r}px;top:${y - r}px;width:${2 * r}px;height:${2 * r}px`);
  tl.fromTo(
    s,
    { opacity: 0.65, scale: 0.94 },
    { opacity: 1, scale: 1.05, duration: seg.t1 - seg.t0 + 0.8, ease: "sine.inOut" },
    seg.t0 - 0.4,
  );
  const rnd = mulberry32(seed),
    dust = div("", stage, "", "position:absolute;inset:0;pointer-events:none");
  const ms = Array.from({ length: n }, () => ({
    el: div("ex-mote", dust),
    a: rnd() * 6.283,
    rr: Math.sqrt(rnd()) * r * 0.8,
    sz: 2 + rnd() * 4,
    sp: 0.2 + rnd() * 0.4,
    ph: rnd() * 6.283,
    o: 0.1 + rnd() * 0.25,
  }));
  ms.forEach((m) => {
    m.el.style.width = m.el.style.height = m.sz.toFixed(1) + "px";
  });
  ticks.push((t) => {
    if (t < seg.t0 - 0.8 || t > seg.t1 + 0.8) return;
    ms.forEach((m) => {
      const q = (((t * 0.06 * m.sp + m.ph / 6.283) % 1) + 1) % 1,
        a = m.a + t * 0.04 * m.sp;
      const px = x + Math.cos(a) * m.rr + Math.sin(t * m.sp + m.ph) * 16,
        py = y + Math.sin(a) * m.rr * 0.75 + 70 - q * 140;
      m.el.style.transform = `translate(${px.toFixed(1)}px,${py.toFixed(1)}px)`;
      m.el.style.opacity = (m.o * Math.sin(Math.PI * q)).toFixed(3);
    });
  });
  return s;
}
// a stroke that draws itself
function exDraw(p, t, dur = 0.6, ease = "power2.inOut") {
  const L = Math.max(1, p.getTotalLength ? p.getTotalLength() : 1000);
  // the gap runs past both ends, so a round cap doesn't leave a dot where the line will start
  p.setAttribute("stroke-dasharray", `${L.toFixed(1)} ${(L + 40).toFixed(1)}`);
  tl.fromTo(p, { attr: { "stroke-dashoffset": L + 20 } }, { attr: { "stroke-dashoffset": 0 }, duration: dur, ease }, t);
}
const exPop = (el, t, s = 0.5, dur = 0.5, ease = "back.out(1.8)") =>
  tl.fromTo(el, { scale: s, opacity: 0 }, { scale: 1, opacity: 1, duration: dur, ease }, t);
const exIn = (el, t, from, dur = 0.6, ease = "expo.out") =>
  tl.fromTo(el, { opacity: 0, ...from }, { opacity: 1, x: 0, y: 0, rotation: 0, scale: 1, duration: dur, ease }, t);
const exFade = (el, t, to = 0, dur = 0.35, from = 1) =>
  tl.fromTo(el, { opacity: from }, { opacity: to, duration: dur, ease: "power2.inOut", ...IR }, t);
function exRig(stage, seg, a, b, origin) {
  // the slow camera: one continuous move across the whole scene
  const r = div("rig3d", stage, "", origin ? `transform-origin:${origin}` : "");
  tw3(r, { ...a, ...TP }, { ...b, ...TP, duration: seg.t1 - seg.t0 + 0.7, ease: "sine.inOut" }, seg.t0 - 0.35);
  return r;
}
function exCount(el, t0, dur, a, b, fmt) {
  ticks.push((t) => {
    el.textContent = fmt(a + (b - a) * easeOut((t - t0) / dur));
  });
}
function exPath(keys, ease = easeInOut) {
  // [[t, x, y], …] → position at time t
  keys = keys.slice().sort((p, q) => p[0] - q[0]);
  return (t) => {
    if (t <= keys[0][0]) return { x: keys[0][1], y: keys[0][2] };
    for (let k = 1; k < keys.length; k++)
      if (t < keys[k][0]) {
        const [ta, xa, ya] = keys[k - 1],
          [tb, xb, yb] = keys[k],
          p = ease((t - ta) / (tb - ta));
        return { x: xa + (xb - xa) * p, y: ya + (yb - ya) * p };
      }
    const l = keys[keys.length - 1];
    return { x: l[1], y: l[2] };
  };
}
// the accent point, with its glow: the video's motif (in the demo it's the AI, wherever it goes)
function exPoint(parent, r = 20, name = "") {
  const g = div("", parent, "", "position:absolute;left:0;top:0;width:0;height:0", name);
  div("ex-glow", g, "", `left:${-r * 4}px;top:${-r * 4}px;width:${r * 8}px;height:${r * 8}px`);
  div(
    "",
    g,
    "",
    `position:absolute;left:${-r}px;top:${-r}px;width:${2 * r}px;height:${2 * r}px;border-radius:50%;background:${P.accent};box-shadow:0 0 30px ${P.accent}`,
  );
  return g;
}
const exAt = (el, x, y, s = 1) => {
  el.style.transform = `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) scale(${s.toFixed(3)})`;
};
// a ring that grows and fades from a point in the scene (scene space, so it moves with the camera)
function exRing(parent, t0, x, y, r1 = 160, dur = 0.7, col = P.accent, name = "") {
  const s = svg(
    "svg",
    { width: 1, height: 1, style: `position:absolute;left:${x}px;top:${y}px;overflow:visible` },
    parent,
    name,
  );
  const c = svg("circle", { cx: 0, cy: 0, r: 1, fill: "none", stroke: col, "stroke-width": 5, opacity: 0 }, s);
  ticks.push((t) => {
    const p = (t - t0) / dur;
    if (p < 0 || p > 1) {
      c.setAttribute("opacity", 0);
      return;
    }
    c.setAttribute("r", (4 + easeOut(p) * r1).toFixed(1));
    c.setAttribute("opacity", ((1 - p) * 0.9).toFixed(3));
  });
}

// ── Overlap rules (a reviewer, Sep 30, 2026: "a graphic moves over top of text and you can't see it"). vs inspect enforces them.
//   · Every tag, chip and label box is SOLID (no rgba backgrounds): a line or a notes page must never show through words.
//   · A bar or a moving thing stops BESIDE its number or label, never under or over it (the email bar ran under "10.28 h").
//   · A mover docks on the card's inner corner, not its center (the courier parked on "OTHER TEAM").
//   · A stamp or sticker lands beside the words it comments on (CHECK IT covered the A+).
//   · A connector runs along the edges or under solid cards, never through a label (the broken links crossed "ONE SYSTEM").
//   · A name under an icon sits below the icon's ring, not across it; a line starts below the name.
//   · Dim a whole scene with ONE scrim on top, never by fading each card (faded cards go see-through).
//   · A scrolling page gets a solid header strip, so its lines scroll under the kicker.

// Vertical: a phone's full-screen player hides the top 10% under its status bar. A scene that opens on a panel with its
// mono kicker near the top can ride lower on a vertical cut only, so the widescreen cut stays as approved. Call it at the
// end of the project's scenes.js: exRideLower(["paradox", "lights"], 60). Found by qa.py's frame scan (Sep 30, 2026).
function exRideLower(names, dy = 60) {
  if (LAND) return;
  for (const k of names) {
    const draw = SCENES[k];
    if (!draw) continue;
    SCENES[k] = (stage, seg, f) => {
      const out = draw(stage, seg, f);
      const low = document.createElement("div");
      low.style.cssText = `position:absolute;inset:0;transform:translateY(${dy}px)`;
      stage.before(low);
      low.appendChild(stage);
      return out;
    };
  }
}
