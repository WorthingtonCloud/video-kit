// The reel runtime, part 2 of 7. build concatenates js/reel/*.js in name order into ONE closure (00 opens it, 60
// closes it), so a part is not a module on its own: it shares every const and helper defined in the parts before it.
  // ───────── tilt tracks: every 3D turn a page gets is also written down here, so its reflection can be worked out
  // from the time alone (reading the live transform mid-render lags a frame, and the renderer seeks out of order)
  const TRK = new Map();
  function tw3(el, from, to, t0) {
    tl.fromTo(el, from, to, t0);
    const e = gsap.parseEase(to.ease || "power1.out"),
      ir = to.immediateRender !== false,
      m = TRK.get(el) || {};
    for (const p of ["rotationX", "rotationY"])
      if (p in from || p in to) {
        (m[p] = m[p] || []).push({ t0, d: to.duration || 0.5, e, a: from[p] ?? 0, b: to[p] ?? 0, ir });
        m[p].sort((x, y) => x.t0 - y.t0);
      }
    TRK.set(el, m);
  }
  const tilt = (el, p, t) => {
    const L = TRK.get(el)?.[p];
    if (!L) return 0;
    let v = L[0].ir ? L[0].a : 0;
    for (const s of L) {
      if (t < s.t0) break;
      v = s.a + (s.b - s.a) * s.e(clamp((t - s.t0) / s.d));
    }
    return v;
  };

  // ───────── camera: a punch is a quick push-in that settles, on a drum hit. Words live outside the rig and never shake ─────────
  const punch = (t, a = 0.03, rot = 0) =>
    tl.fromTo(
      camrig,
      { scale: 1 + a, rotation: rot },
      { scale: 1, rotation: 0, duration: 0.55, ease: "power3.out", ...IR },
      t,
    );

  // a shockwave ring at a screen point
  function shock(t0, x, y, r1 = 260, dur = 0.7, w = 5) {
    const c = svg("circle", { cx: x, cy: y, r: 1, fill: "none", stroke: P.accent, "stroke-width": w, opacity: 0 }, fx);
    ticks.push((t) => {
      const p = (t - t0) / dur;
      if (p < 0 || p > 1) {
        c.setAttribute("opacity", 0);
        return;
      }
      c.setAttribute("r", 4 + easeOut(p) * r1);
      c.setAttribute("opacity", (1 - p) * 0.9);
      c.setAttribute("stroke-width", w * (1 - 0.7 * p));
    });
  }

  // a spark: a red head trailing a tail, from a to b along a gentle arc; a small burst where it lands
  function spark(t0, a, b, dur = 0.3, bend = 0.22) {
    const tail = svg(
      "path",
      { fill: "none", stroke: P.accent, "stroke-width": 6, "stroke-linecap": "round", opacity: 0 },
      fx,
    );
    const head = svg("circle", { r: 10, fill: P.accent, opacity: 0 }, fx);
    const mx = (a.x + b.x) / 2 - (b.y - a.y) * bend,
      my = (a.y + b.y) / 2 + (b.x - a.x) * bend;
    const at = (p) => ({
      x: (1 - p) * (1 - p) * a.x + 2 * (1 - p) * p * mx + p * p * b.x,
      y: (1 - p) * (1 - p) * a.y + 2 * (1 - p) * p * my + p * p * b.y,
    });
    ticks.push((t) => {
      const p = (t - t0) / dur;
      if (p < 0 || p > 1.4) {
        tail.setAttribute("opacity", 0);
        head.setAttribute("opacity", 0);
        return;
      }
      const ph = easeInOut(Math.min(p, 1)),
        pt = easeInOut(clamp((p - 0.4) / 1.0));
      let d = "";
      for (let k = 0; k <= 14; k++) {
        const q = at(pt + ((ph - pt) * k) / 14);
        d += `${k ? "L" : "M"}${q.x.toFixed(1)} ${q.y.toFixed(1)}`;
      }
      tail.setAttribute("d", d);
      tail.setAttribute("opacity", 0.9);
      const h = at(ph);
      head.setAttribute("cx", h.x);
      head.setAttribute("cy", h.y);
      head.setAttribute("opacity", p < 1 ? 1 : 0);
    });
    shock(t0 + dur, b.x, b.y, 90, 0.4, 4);
  }

  // ───────── the phone safe zone (vertical): words stay in x 11–89%, y 10–84%, and x ≤ 80% below 62% height ─────────
  const fitStage = (center) => {
    if (!LAND) {
      const s = Math.min(W / 1080, (0.64 * H) / 1200);
      return { s, x: W / 2 - 540 * s, y: (center ? H / 2 : H * 0.35) - 700 * s };
    }
    const s = center ? (0.92 * H) / 1200 : Math.min((0.52 * W) / 1080, (0.92 * H) / 1200);
    return { s, x: (center ? W / 2 : W * 0.72) - 540 * s, y: H / 2 - 700 * s };
  };
  const toScreen = (f, x, y) => ({ x: f.x + x * f.s, y: f.y + y * f.s });

