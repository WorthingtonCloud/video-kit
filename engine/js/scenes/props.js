// Explainer scene library, part 3 of 4: props promoted from finished videos (the Socrates explainer, Oct 1, 2026), each
// one a move that read well and will again: a stamp that slams down, a strike-through, a ring that starts outside what it
// surrounds (so it never crosses its words), a boxing bell, a "ROUND N" card, keyframes, a photo with its own camera.
{
  const css = document.createElement("style");
  css.textContent = `.ex-big{position:absolute;left:0;right:0;text-align:center;font-weight:800;color:${P.ink};letter-spacing:-.02em;white-space:nowrap;line-height:1}`;
  document.head.appendChild(css);
}
// an SVG drawing in a 200-unit box (a prop: a bust, a robe, a pill), placed in scene space
const exSvgBox = (parent, x, y, size, inner) =>
  div(
    "ex-ic",
    parent,
    `<svg viewBox="0 0 200 200" width="${size}" height="${size}" style="overflow:visible">${inner}</svg>`,
    `left:${x}px;top:${y}px;width:${size}px;height:${size}px`,
  );
// a stamp slams down and the camera feels it
function exStamp(el, t, rot = -8, big = 2.6) {
  tl.fromTo(
    el,
    { scale: big, rotation: rot * 3, opacity: 0 },
    { scale: 1, rotation: rot, opacity: 1, duration: 0.26, ease: "power4.in" },
    t - 0.26,
  );
  punch(t, 0.022);
}
const exSlam = (el, t, from = 2.2, dur = 0.4) =>
  tl.fromTo(
    el,
    { scale: from, opacity: 0, filter: "blur(18px)" },
    { scale: 1, opacity: 1, filter: "blur(0px)", duration: dur, ease: "expo.out" },
    t,
  );
// a strike line across an element (its own child, sized to it)
function exStrike(el, t, col = P.accent) {
  const s = div(
    "",
    el,
    "",
    `position:absolute;left:-6px;right:-6px;top:50%;height:6px;margin-top:-3px;border-radius:3px;background:${col};transform-origin:0 50%`,
  );
  tl.fromTo(s, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, t);
  return s;
}
// a ring that starts OUTSIDE what it surrounds (r0) and grows to r1, so it never crosses the words inside it
function exRing2(parent, t0, x, y, r0, r1, dur = 0.7, col = "#fff") {
  const s = svg(
    "svg",
    { width: 1, height: 1, style: `position:absolute;left:${x}px;top:${y}px;overflow:visible` },
    parent,
  );
  const c = svg("circle", { cx: 0, cy: 0, r: r0, fill: "none", stroke: col, "stroke-width": 5, opacity: 0 }, s);
  ticks.push((t) => {
    const p = (t - t0) / dur;
    if (p < 0 || p > 1) {
      c.setAttribute("opacity", 0);
      return;
    }
    c.setAttribute("r", (r0 + easeOut(p) * (r1 - r0)).toFixed(1));
    c.setAttribute("opacity", ((1 - p) * 0.9).toFixed(3));
  });
}
// the bell: two rings out of the edge of what rang it (r0 = clear of its words), and a punch
function exBell(parent, t, x, y, r0 = 300) {
  exRing2(parent, t, x, y, r0, r0 * 1.5, 0.8);
  exRing2(parent, t + 0.2, x, y, r0 * 1.1, r0 * 1.85, 0.9);
  punch(t + 0.02, 0.035);
}
// "ROUND N": slams in big, the bell rings, then it shrinks to a chip in the corner and the round's picture takes over
function exRound(parent, big, sub, t, t2, t3) {
  const g = div(
    "",
    parent,
    "",
    "position:absolute;left:0;top:0;width:1080px;height:1400px;transform-origin:540px 420px",
  );
  const b = div("ex-big", g, big, "top:310px;font-size:160px");
  const s = div("ex-k", g, sub, "left:0;right:0;top:520px;text-align:center;font-size:30px;color:#fff");
  exSlam(b, t - 0.08, 2.6);
  exBell(g, t + 0.05, 540, 395, 380);
  exIn(s, t2 - 0.1, { y: 24 }, 0.35);
  tl.fromTo(g, { opacity: 1, scale: 1 }, { opacity: 0, scale: 0.55, duration: 0.32, ease: "power3.in", ...IR }, t3);
  const chip = div("ex-chip", parent, `${big} · ${sub}`, "left:130px;top:168px;font-size:22px");
  exPop(chip, t3 + 0.22, 0.6, 0.4);
  return chip;
}
// [[t, a, b, …]] → [a, b, …] at time t, eased between keys
function exKeys(keys) {
  keys = keys.slice().sort((p, q) => p[0] - q[0]);
  return (t) => {
    if (t <= keys[0][0]) return keys[0].slice(1);
    for (let k = 1; k < keys.length; k++)
      if (t < keys[k][0]) {
        const a = keys[k - 1],
          b = keys[k],
          p = easeInOut((t - a[0]) / (b[0] - a[0]));
        return a.slice(1).map((v, i) => v + (b[i + 1] - v) * p);
      }
    return keys[keys.length - 1].slice(1);
  };
}
// a photo with its own camera: keys [t, u, v, scale] (u, v = the point of the picture at the box's center, 0..1);
// the picture never shows an edge. `ov` is pinned to the picture (things that ride with it).
function exPhoto(stage, img, keys, seg, box = { x: 0, y: 60, w: 1080, h: 1100 }) {
  const H0 = box.h * 1.15,
    W0 = H0 * 1.5;
  const clip = div("ex-clip", stage, "", `left:${box.x}px;top:${box.y}px;width:${box.w}px;height:${box.h}px`);
  const cam = div(
    "",
    clip,
    `<img src="${img}" style="width:100%;height:100%;display:block">`,
    `position:absolute;left:0;top:0;width:${W0.toFixed(1)}px;height:${H0.toFixed(1)}px;transform-origin:0 0`,
  );
  const ov = div("", cam, "", "position:absolute;inset:0");
  const at = exKeys(keys);
  ticks.push((t) => {
    if (t < seg.t0 - 0.6 || t > seg.t1 + 0.8) return;
    const [u, v, s] = at(t),
      hw = box.w / 2 / s,
      hh = box.h / 2 / s;
    const fx = clamp(u * W0, hw, W0 - hw),
      fy = clamp(v * H0, hh, H0 - hh);
    cam.style.transform = `translate(${(box.w / 2 - fx * s).toFixed(1)}px,${(box.h / 2 - fy * s).toFixed(1)}px) scale(${s.toFixed(4)})`;
  });
  div(
    "",
    clip,
    "",
    `position:absolute;left:0;right:0;bottom:0;height:380px;background:linear-gradient(180deg,rgba(${exRGB(P.ground)},0),${P.ground})`,
  );
  div(
    "",
    clip,
    "",
    `position:absolute;left:0;right:0;top:0;height:150px;background:linear-gradient(0deg,rgba(${exRGB(P.ground)},0),${P.ground})`,
  );
  if (LAND) {
    div(
      "",
      clip,
      "",
      `position:absolute;left:0;top:0;bottom:0;width:200px;background:linear-gradient(90deg,${P.ground},rgba(${exRGB(P.ground)},0))`,
    );
    div(
      "",
      clip,
      "",
      `position:absolute;right:0;top:0;bottom:0;width:200px;background:linear-gradient(270deg,${P.ground},rgba(${exRGB(P.ground)},0))`,
    );
  }
  return { clip, cam, ov, W0, H0 };
}
