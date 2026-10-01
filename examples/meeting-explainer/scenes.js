// The demo explainer, "This meeting could have been a prompt" (Sep 30, 2026): ten scenes as a worked example. A project's
// scenes.js holds only its own scenes (and its own props); the helpers come from the engine's scene library.
Object.assign(SCENES, {
  // ── 1. The paradox: the rollout dashboard goes green, use climbs, and the payroll line stays flat ──
  paradox(stage, seg) {
    const c = R.scenes.paradox.cues,
      len = seg.t1 - seg.t0;
    exLight(stage, 540, 600, 760, seg, 30, 11);
    const rig = exRig(stage, seg, { rotationX: 9, rotationY: -9 }, { rotationX: 2, rotationY: 7 });
    const zoom = div("rig3d", rig);
    const A = div("ex-p", zoom, "", "left:110px;top:130px;width:860px;height:520px");
    div("ex-k", A, "AI ROLLOUT · SEATS LICENSED", "left:34px;top:28px");
    const cnt = div("ex-m", A, "", `right:34px;top:26px;font-size:24px;color:${P.dim}`);
    exCount(cnt, c.license - 0.1, 1.45, 0, 48, (v) => `${Math.round(v)} / 48`);
    const rnd = mulberry32(3),
      seats = [];
    for (let r = 0; r < 4; r++)
      for (let q = 0; q < 12; q++) {
        const s = div(
          "",
          A,
          "",
          `position:absolute;left:${34 + q * 66}px;top:${84 + r * 56}px;width:52px;height:42px;border-radius:5px;border:3px solid ${P.line};background:#18191d`,
        );
        seats.push(s);
        tl.fromTo(
          s,
          { backgroundColor: "#18191d", borderColor: P.line, scale: 1 },
          { backgroundColor: GREEN, borderColor: GREEN, scale: 1, duration: 0.2, ease: "power2.out" },
          c.license - 0.1 + rnd() * 1.3,
        );
      }
    // "a beautiful shade of green": the whole dashboard lights up, a green sweep crosses it
    const ring = div(
      "",
      A,
      "",
      `position:absolute;inset:-3px;border:3px solid ${GREEN};border-radius:8px;box-shadow:0 0 80px rgba(63,185,80,.45),inset 0 0 40px rgba(63,185,80,.12)`,
    );
    tl.fromTo(ring, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power2.out" }, c.green - 0.2);
    const sweep = div(
      "ex-clip",
      A,
      `<div style="position:absolute;top:0;bottom:0;width:40%;background:linear-gradient(90deg,rgba(63,185,80,0),rgba(63,185,80,.32),rgba(63,185,80,0))"></div>`,
      "inset:0",
    );
    tl.fromTo(
      sweep.firstChild,
      { xPercent: -110 },
      { xPercent: 260, duration: 0.9, ease: "power2.inOut" },
      c.green - 0.3,
    );
    const up = div("ex-k green", A, "ADOPTION ▲", "right:34px;top:26px;opacity:0");
    tl.fromTo(cnt, { opacity: 1 }, { opacity: 0, duration: 0.2, ...IR }, c.green - 0.1);
    tl.fromTo(up, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.35, ease: "back.out(2)" }, c.green);
    // weekly use at work: 28% → 39%, the two measured points (nothing invented in between)
    const ch = svg(
      "svg",
      {
        width: 792,
        height: 150,
        viewBox: "0 0 792 150",
        style: "position:absolute;left:34px;top:334px;overflow:visible",
      },
      A,
    );
    svg("line", { x1: 0, y1: 140, x2: 792, y2: 140, stroke: P.line, "stroke-width": 3 }, ch);
    const yv = (v) => 140 - (v / 50) * 140;
    const ln = svg(
      "path",
      {
        d: `M40 ${yv(28.2)} L752 ${yv(39.2)}`,
        fill: "none",
        stroke: GREEN,
        "stroke-width": 7,
        "stroke-linecap": "round",
      },
      ch,
    );
    exDraw(ln, c.four, 1.1);
    [
      [40, 28.2, c.four - 0.1, "28%", "2024"],
      [752, 39.2, c.four + 1.05, "39%", "2026"],
    ].forEach(([x, v, t, lab, yr]) => {
      const d = svg("circle", { cx: x, cy: yv(v), r: 0, fill: GREEN }, ch);
      tl.fromTo(d, { attr: { r: 0 } }, { attr: { r: 12 }, duration: 0.35, ease: "back.out(3)" }, t);
      const l = div(
        "ex-m",
        A,
        lab,
        `left:${34 + x - 40}px;top:${334 + yv(v) - 58}px;font-size:30px;color:${GREEN};width:80px;text-align:center`,
      );
      const y2 = div(
        "ex-m",
        A,
        yr,
        `left:${34 + x - 40}px;top:${334 + 148}px;font-size:20px;color:${P.dim};width:80px;text-align:center`,
      );
      tl.fromTo([l, y2], { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.3 }, t + 0.05);
    });
    // "they really ARE faster": a streak crosses the dashboard
    const fast = div(
      "ex-clip",
      A,
      `<div class="ex-m" style="left:0;top:0;font-size:150px;color:#fff;letter-spacing:-.1em">›››</div>`,
      "inset:0",
    );
    tl.fromTo(
      fast.firstChild,
      { x: -330, y: 150, opacity: 0, filter: "blur(10px)" },
      { x: 1000, y: 150, opacity: 0.9, filter: "blur(4px)", duration: 0.55, ease: "power2.in" },
      c.faster - 0.1,
    );
    // the payroll records: a panel rises into view; its line stays flat inside the ±2% band
    const Bp = div("ex-p", zoom, "", "left:110px;top:700px;width:860px;height:410px");
    div("ex-k", Bp, "PAY &amp; HOURS · 25,000 WORKERS", "left:34px;top:28px");
    tw3(
      Bp,
      { y: 520, rotationX: -48, opacity: 0, ...TP },
      { y: 0, rotationX: 0, opacity: 1, ...TP, duration: 0.85, ease: "expo.out" },
      c.payroll - 0.4,
    );
    const pc = svg(
      "svg",
      {
        width: 792,
        height: 260,
        viewBox: "0 0 792 260",
        style: "position:absolute;left:34px;top:110px;overflow:visible",
      },
      Bp,
    );
    const band = svg(
      "rect",
      {
        x: 0,
        y: 100,
        width: 792,
        height: 64,
        fill: "rgba(255,255,255,.05)",
        stroke: P.line,
        "stroke-width": 2,
        "stroke-dasharray": "10 7",
      },
      pc,
    );
    tl.fromTo(band, { opacity: 0 }, { opacity: 1, duration: 0.5 }, c.payroll + 0.25);
    const bl = div("ex-m", Bp, "±2%", `left:${34 + 800 - 96}px;top:${110 + 58}px;font-size:22px;color:${P.dim}`);
    tl.fromTo(bl, { opacity: 0 }, { opacity: 1, duration: 0.4 }, c.payroll + 0.4);
    const flat = svg(
      "path",
      {
        d: "M0 132 C 90 128, 170 137, 260 131 S 440 134, 540 131 S 700 133, 792 132",
        fill: "none",
        stroke: P.ink,
        "stroke-width": 7,
        "stroke-linecap": "round",
      },
      pc,
    );
    exDraw(flat, c.payoff - 0.15, 1.3, "power1.inOut");
    const end = svg("circle", { cx: 792, cy: 132, r: 0, fill: P.accent }, pc);
    tl.fromTo(end, { attr: { r: 0 } }, { attr: { r: 15 }, duration: 0.3, ease: "back.out(3)" }, c.payoff + 1.1);
    exRing(Bp, c.barely + 0.5, 34 + 792, 110 + 132, 90, 0.7);
    // "where did all that time go?": the saved hours float up out of the dashboard and away
    const rn = mulberry32(21);
    for (let k = 0; k < 16; k++) {
      const col = k % 12,
        row = Math.floor(rn() * 4),
        sx = 110 + 34 + col * 66 + 26,
        sy = 130 + 84 + row * 56 + 21;
      const tok = exIcon(zoom, "clock", 58, sx - 29, sy - 29);
      tl.fromTo(
        tok,
        { x: 0, y: 0, opacity: 0, scale: 0.3, rotation: 0 },
        {
          x: 260 + rn() * 520,
          y: -260 - rn() * 520,
          opacity: 1,
          scale: 1.1,
          rotation: 220 + rn() * 140,
          duration: 1.25,
          ease: "power2.in",
        },
        c.where - 0.25 + k * 0.06,
      );
    }
    tl.fromTo(zoom, { scale: 1, y: 0 }, { scale: 1.07, y: -30, duration: 1.3, ease: "power2.inOut" }, c.where - 0.2);
    return "own-push";
  },

  // ── 2. Coordination grows faster than teams: five people, ten lines; twenty people, a switchboard ──
  web(stage, seg) {
    const c = R.scenes.web.cues,
      len = seg.t1 - seg.t0;
    exLight(stage, 540, 640, 760, seg, 30, 5);
    const rig = exRig(
      stage,
      seg,
      { rotationX: 18, rotationY: 12, scale: 0.9 },
      { rotationX: 3, rotationY: -8, scale: 1 },
      "540px 640px",
    );
    const spin = div("rig3d", rig, "", "transform-origin:540px 640px");
    tl.fromTo(spin, { rotation: -8 }, { rotation: 22, duration: len + 0.6, ease: "none" }, seg.t0 - 0.3);
    const S = svg(
      "svg",
      { width: 1080, height: 1400, viewBox: "0 0 1080 1400", style: "position:absolute;left:0;top:0;overflow:visible" },
      spin,
    );
    const N = 20,
      cx = 540,
      cy = 640,
      RR = 410,
      five = [0, 4, 8, 12, 16];
    const pos = Array.from({ length: N }, (_, i) => {
      const a = -Math.PI / 2 + (i * 2 * Math.PI) / N;
      return { x: cx + RR * Math.cos(a), y: cy + RR * Math.sin(a) };
    });
    const gl = svg("g", {}, S),
      gh = svg("g", {}, S),
      gn = svg("g", {}, S);
    const L = [],
      rn = mulberry32(9);
    for (let i = 0; i < N; i++)
      for (let j = i + 1; j < N; j++) {
        const e = svg(
          "line",
          {
            x1: pos[i].x,
            y1: pos[i].y,
            x2: pos[j].x,
            y2: pos[j].y,
            stroke: P.ink,
            "stroke-width": 2.5,
            "stroke-linecap": "round",
            opacity: 0.3,
          },
          gl,
        );
        L.push({ e, i, j, core: five.includes(i) && five.includes(j), h: rn() });
      }
    let kc = 0;
    L.forEach((l) =>
      l.core
        ? exDraw(l.e, c.coord - 0.15 + kc++ * 0.07, 0.5)
        : exDraw(l.e, c.twenty + 0.4 + l.h * 1.1, 0.35, "power2.out"),
    );
    const coreIdx = L.map((l, k) => (l.core ? k : -1)).filter((k) => k >= 0);
    // every line's color is a function of time: the count flashes, then the switchboard blinks
    ticks.push((t) => {
      if (t < seg.t0 - 0.5 || t > seg.t1 + 0.5) return;
      L.forEach((l, k) => {
        let red = false;
        const ci = coreIdx.indexOf(k);
        if (ci >= 0 && t >= c.ten - 0.05 + ci * 0.075 && t < c.ten + 0.2 + ci * 0.075) red = true;
        if (t >= c.switch - 0.1) {
          const slot = Math.floor(t * 7);
          red = red || (((Math.sin(k * 12.9898 + slot * 78.233) * 43758.5453) % 1) + 1) % 1 < 0.07;
        }
        l.e.setAttribute("stroke", red ? P.accent : P.ink);
        l.e.setAttribute("opacity", red ? 1 : 0.3);
        l.e.setAttribute("stroke-width", red ? 5 : 2.5);
      });
    });
    // "every pair of people is another line": one pair lights up, a sync packet runs back and forth
    const pa = pos[0],
      pb = pos[8];
    const hl = svg(
      "line",
      { x1: pa.x, y1: pa.y, x2: pb.x, y2: pb.y, stroke: P.accent, "stroke-width": 7, "stroke-linecap": "round" },
      gh,
    );
    exDraw(hl, c.pair - 0.1, 0.45);
    tl.fromTo(hl, { opacity: 1 }, { opacity: 0, duration: 0.4, ...IR }, c.twenty);
    const pk = svg("circle", { r: 11, fill: P.accent, opacity: 0 }, gh);
    ticks.push((t) => {
      if (t < c.pair + 0.3 || t > c.twenty) {
        pk.setAttribute("opacity", 0);
        return;
      }
      const q = ((t - c.pair - 0.3) / 0.9) % 2,
        p = easeInOut(q < 1 ? q : 2 - q);
      pk.setAttribute("cx", pa.x + (pb.x - pa.x) * p);
      pk.setAttribute("cy", pa.y + (pb.y - pa.y) * p);
      pk.setAttribute("opacity", 1);
    });
    // the people: five at their desks first (each with a square of real work), fifteen more fly in on "Twenty"
    pos.forEach((p, i) => {
      const g = svg("g", { transform: `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)})` }, gn),
        inner = svg("g", {}, g);
      svg("circle", { r: 31, fill: P.card, stroke: P.ink, "stroke-width": 4 }, inner);
      svg("circle", { cx: 0, cy: -8, r: 8, fill: P.ink }, inner);
      svg(
        "path",
        { d: "M-15 17 C-13 4 13 4 15 17", fill: "none", stroke: P.ink, "stroke-width": 4, "stroke-linecap": "round" },
        inner,
      );
      if (five.includes(i)) {
        const k = five.indexOf(i);
        tl.fromTo(
          inner,
          { scale: 0, svgOrigin: "0 0" },
          { scale: 1, svgOrigin: "0 0", duration: 0.5, ease: "back.out(2.2)" },
          seg.t0 + 0.1 + k * 0.12,
        );
        const wx = (p.x - cx) * 0.2,
          wy = (p.y - cy) * 0.2;
        const w = svg("rect", { x: wx - 13, y: wy - 13, width: 26, height: 26, rx: 3, fill: P.ink }, g);
        tl.fromTo(
          w,
          { opacity: 0, scale: 0, svgOrigin: `${wx} ${wy}` },
          { opacity: 1, scale: 1, svgOrigin: `${wx} ${wy}`, duration: 0.35, ease: "back.out(2)" },
          c.work + k * 0.06,
        );
        tl.fromTo(w, { opacity: 1 }, { opacity: 0.18, duration: 0.6, ...IR }, c.coord);
      } else {
        const dx = (p.x - cx) * 1.3,
          dy = (p.y - cy) * 1.3;
        // smoothOrigin off: with it, GSAP "keeps the element still" through the origin change by adding to x/y, and
        // the fifteen never landed (they parked 2.3× out, off a vertical frame and in plain sight on a wide one)
        tl.fromTo(
          inner,
          { x: dx, y: dy, scale: 0.3, opacity: 0, svgOrigin: "0 0", smoothOrigin: false },
          { x: 0, y: 0, scale: 1, opacity: 1, svgOrigin: "0 0", smoothOrigin: false, duration: 0.6, ease: "expo.out" },
          c.twenty - 0.1 + (i % 7) * 0.05 + Math.floor(i / 7) * 0.03,
        );
      }
    });
    // the camera leans in as the web fills, and shivers once on "switchboard"
    const push = div("rig3d", rig, "", "transform-origin:540px 640px;pointer-events:none");
    push.appendChild(spin);
    tl.fromTo(push, { scale: 1 }, { scale: 1.12, duration: 1.6, ease: "power2.inOut" }, c.twenty - 0.1);
    tl.fromTo(push, { scale: 1.12 }, { scale: 1.02, duration: 1.2, ease: "power2.inOut", ...IR }, c.team - 0.4);
    punch(c.switch, 0.02);
    return "own-push";
  },

  // ── 3. AI went into the inbox: email shrinks, meetings won't budge, and nobody can cancel the sync ──
  inbox(stage, seg) {
    const c = R.scenes.inbox.cues;
    exLight(stage, 540, 560, 760, seg, 26, 17);
    const rig = exRig(stage, seg, { rotationX: 8, rotationY: 10 }, { rotationX: 2, rotationY: -6 });
    div("ex-k", rig, "WHERE AI WENT", "left:110px;top:100px");
    // the inbox
    const I = div("ex-p", rig, "", "left:250px;top:170px;width:580px;height:260px");
    div("ex-k", I, "INBOX", "left:30px;top:24px");
    exIn(I, seg.t0 + 0.05, { y: -60, scale: 0.9 }, 0.6);
    for (let k = 0; k < 5; k++) exIcon(I, "mail", 78, 40 + k * 104, 110);
    const ir = div(
      "",
      I,
      "",
      `position:absolute;inset:-3px;border:3px solid ${P.accent};border-radius:8px;box-shadow:0 0 60px rgba(232,64,44,.4)`,
    );
    tl.fromTo(ir, { opacity: 0 }, { opacity: 1, duration: 0.15 }, c.inbox + 0.02);
    tl.fromTo(ir, { opacity: 1 }, { opacity: 0.35, duration: 0.8, ...IR }, c.inbox + 0.25);
    for (let k = 0; k < 9; k++) {
      // mail flies out, fast
      const m = exIcon(rig, "mail", 60, 520, 270);
      tl.fromTo(
        m,
        { x: 0, y: 0, opacity: 0, rotation: 0 },
        { x: 560 + k * 20, y: -220 + (k % 3) * 70, opacity: 1, rotation: 25, duration: 0.55, ease: "power2.in" },
        c.inbox + 0.15 + k * 0.12,
      );
      tl.fromTo(m, { opacity: 1 }, { opacity: 0, duration: 0.1, ...IR }, c.inbox + 0.7 + k * 0.12);
    }
    // the trial: hours a week on email and in meetings
    const Bp = div("ex-p", rig, "", "left:110px;top:480px;width:860px;height:320px");
    div("ex-k", Bp, "HOURS A WEEK · 6-MONTH TRIAL", "left:34px;top:28px");
    exIn(Bp, c.trial - 0.3, { y: 80 }, 0.6);
    const px = 38,
      bx = 215; // 38px per hour: the 12-hour track ends at 671, clear of the value column (from ~700) so a bar never runs under its number
    const row = (y, label) => {
      div("ex-t", Bp, label, `left:34px;top:${y + 4}px;font-size:32px`);
      div(
        "",
        Bp,
        "",
        `position:absolute;left:${bx}px;top:${y}px;width:${12 * px}px;height:44px;border-radius:4px;background:#18191d;border:2px solid ${P.line}`,
      );
    };
    row(100, "Email");
    row(200, "Meetings");
    const ghost = div(
      "ex-bar",
      Bp,
      "",
      `left:${bx}px;top:100px;width:${11.65 * px}px;background:rgba(255,255,255,.12)`,
    );
    const eb = div("ex-bar", Bp, "", `left:${bx}px;top:100px;width:${11.65 * px}px;background:${P.ink}`);
    tl.fromTo([ghost, eb], { scaleX: 0 }, { scaleX: 1, duration: 0.8, ease: "power3.out" }, c.trial);
    tl.fromTo(
      eb,
      { scaleX: 1 },
      { scaleX: 10.28 / 11.65, duration: 0.7, ease: "power3.inOut", ...IR },
      c.twelve - 0.05,
    );
    const gap = div(
      "",
      Bp,
      "",
      `position:absolute;left:${bx + 10.28 * px}px;top:92px;width:${1.37 * px}px;height:60px;border:3px solid ${P.accent};border-radius:4px;background:rgba(232,64,44,.15)`,
    );
    exPop(gap, c.twelve + 0.55, 0.6, 0.35);
    const ev = div("ex-m", Bp, "", `right:34px;top:104px;font-size:30px`);
    ticks.push((t) => {
      ev.textContent =
        (t < c.twelve ? 11.65 * easeOut((t - c.trial) / 0.8) : 11.65 - 1.37 * easeOut((t - c.twelve) / 0.7)).toFixed(
          2,
        ) + " h";
    });
    const mb = div("ex-bar", Bp, "", `left:${bx}px;top:200px;width:${5.32 * px}px;background:${P.ink}`);
    tl.fromTo(mb, { scaleX: 0 }, { scaleX: 5.22 / 5.32, duration: 0.7, ease: "power3.out" }, c.meetings - 0.1);
    tl.fromTo(mb, { scaleX: 5.22 / 5.32 }, { scaleX: 0.78, duration: 0.22, ease: "power2.out", ...IR }, c.move - 0.1);
    tl.fromTo(mb, { scaleX: 0.78 }, { scaleX: 1, duration: 0.9, ease: "elastic.out(1.2,0.35)", ...IR }, c.move + 0.12);
    const mv = div("ex-m", Bp, "", `right:34px;top:204px;font-size:30px`);
    ticks.push((t) => {
      mv.textContent =
        (t < c.move + 0.3
          ? 5.22 * easeOut((t - c.meetings + 0.1) / 0.7)
          : 5.22 + 0.1 * easeOut((t - c.move - 0.3) / 0.5)
        ).toFixed(2) + " h";
    });
    // the weekly sync nobody can cancel: eight people hold it in place
    const Cb = div("ex-p", rig, "", "left:260px;top:860px;width:560px;height:220px");
    div("ex-k", Cb, "WEEKLY SYNC · 60 MIN", "left:30px;top:26px");
    div("ex-t", Cb, "Every Tuesday", `left:30px;top:78px;font-size:40px`);
    const btn = div("ex-chip", Cb, "✕ CANCEL", "left:30px;top:146px");
    exIn(Cb, c.one - 0.3, { y: 90, rotation: -3 }, 0.6);
    tl.fromTo(
      btn,
      { backgroundColor: "#18191d", borderColor: P.line, scale: 1 },
      { backgroundColor: "rgba(232,64,44,.5)", borderColor: P.accent, scale: 0.92, duration: 0.1, ease: "power2.out" },
      c.cancel + 0.05,
    );
    tl.fromTo(btn, { scale: 0.92 }, { scale: 1, duration: 0.3, ease: "back.out(3)", ...IR }, c.cancel + 0.18);
    tl.fromTo(
      Cb,
      { x: 0 },
      {
        keyframes: [
          { x: -16, duration: 0.06 },
          { x: 14, duration: 0.07 },
          { x: -9, duration: 0.07 },
          { x: 5, duration: 0.07 },
          { x: 0, duration: 0.08 },
        ],
        ...IR,
      },
      c.cancel + 0.1,
    );
    const teth = svg(
      "svg",
      { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" },
      rig,
    );
    [
      [150, 880],
      [150, 960],
      [150, 1040],
      [150, 1120],
      [930, 880],
      [930, 960],
      [930, 1040],
      [930, 1120],
    ].forEach(([x, y], k) => {
      const ln = svg(
        "line",
        {
          x1: x,
          y1: y,
          x2: x < 540 ? 260 : 820,
          y2: 900 + (k % 4) * 50,
          stroke: P.accent,
          "stroke-width": 3,
          opacity: 0.8,
        },
        teth,
      );
      exDraw(ln, c.everyone - 0.25 + k * 0.05, 0.3);
      const a = exIcon(rig, "person", 60, x - 30, y - 30);
      exPop(a, c.cancel + 0.2 + k * 0.06, 0.3, 0.4);
    });
    // the AI itself: a red point that looks around, dives into the inbox, then tries the meetings and bounces off
    const pt = exPoint(rig, 18);
    const btnX = 260 + 30 + 80,
      btnY = 860 + 146 + 22;
    const path = exPath([
      [seg.t0 + 0.2, 540, 620],
      [c.guess - 0.3, 540, 520],
      [c.guess + 0.2, 380, 420],
      [c.guess + 0.55, 700, 420],
      [c.guess + 0.9, 540, 400],
      [c.inbox - 0.3, 540, 150],
      [c.inbox + 0.02, 540, 300],
      [c.move - 0.5, 540, 300],
      [c.move - 0.1, bx + 110 + 5.22 * px + 26, 702],
      [c.move + 0.12, bx + 110 + 0.78 * 5.32 * px + 26, 702],
      [c.move + 0.6, 800, 640],
      [c.cancel - 0.4, 760, 900],
      [c.cancel + 0.05, btnX, btnY],
      [c.cancel + 0.5, btnX + 90, btnY - 80],
      [seg.t1 + 1, btnX + 120, btnY - 90],
    ]);
    ticks.push((t) => {
      const p = path(t),
        s = clamp((t - seg.t0 - 0.2) / 0.3);
      exAt(pt, p.x, p.y, s);
    });
    return "own-push";
  },

  // ── 4. Faster between stops, and more stops: a car floors it light to light; the notes pile up ──
  lights(stage, seg) {
    const c = R.scenes.lights.cues;
    exLight(stage, 540, 520, 760, seg, 22, 23);
    const rig = exRig(stage, seg, { rotationX: 10, rotationY: -10 }, { rotationX: 3, rotationY: 6 });
    const Rd = div("ex-p", rig, "", "left:110px;top:140px;width:860px;height:330px;overflow:hidden");
    div("ex-k", Rd, "EVERY STOP IS A HANDOFF", "left:34px;top:26px;z-index:2");
    div(
      "",
      Rd,
      "",
      `position:absolute;left:0;right:0;top:200px;height:96px;background:#141518;border-top:3px solid ${P.line};border-bottom:3px solid ${P.line}`,
    );
    const dash = div(
      "",
      Rd,
      "",
      `position:absolute;left:-80px;right:-80px;top:245px;height:6px;background:repeating-linear-gradient(90deg,${P.dim} 0 40px,transparent 40px 80px);opacity:.45`,
    );
    const carX = 110,
      front = carX + 190,
      SP = 460,
      SP2 = 230,
      T1 = 1.05,
      D1 = 0.42,
      T2 = 0.62,
      D2 = 0.26;
    const tS = c.floor - 0.15,
      n0 = Math.ceil((c.more - tS) / T1),
      tb = tS + n0 * T1;
    const ease = (x) => {
      x = clamp(x);
      return x < 0.5 ? 16 * x ** 5 : 1 - Math.pow(-2 * x + 2, 5) / 2;
    };
    const offAt = (t) => {
      if (t < tS) return { off: 0, v: 0 };
      if (t < tb) {
        const n = Math.floor((t - tS) / T1),
          f = (t - tS - n * T1) / D1;
        return { off: SP * (n + ease(f)), v: f < 1 ? Math.sin(Math.PI * clamp(f)) : 0 };
      }
      const n = Math.floor((t - tb) / T2),
        f = (t - tb - n * T2) / D2;
      return { off: SP * n0 + SP2 * (n + ease(f)), v: f < 1 ? Math.sin(Math.PI * clamp(f)) : 0 };
    };
    const lamps = Array.from({ length: 90 }, (_, k) => {
      const e = div(
        "",
        Rd,
        `<div style="position:absolute;left:14px;top:60px;width:6px;height:70px;background:#3a3b41"></div><div style="position:absolute;left:0;top:0;width:34px;height:64px;border-radius:6px;background:#0c0c0e;border:3px solid #3a3b41"></div><div class="lamp" style="position:absolute;left:7px;top:9px;width:20px;height:20px;border-radius:50%;background:${P.accent}"></div>`,
        "position:absolute;left:0;top:78px;width:34px;height:130px",
      );
      return { e, lamp: e.querySelector(".lamp"), k, extra: k % 2 === 1, tOn: c.more - 0.1 + (k % 7) * 0.035 };
    });
    const car = exIcon(Rd, "car", 170, carX, 176);
    const streak = div(
      "",
      Rd,
      "",
      `position:absolute;left:${carX - 260}px;top:212px;width:260px;height:44px;background:repeating-linear-gradient(180deg,rgba(255,255,255,.55) 0 3px,transparent 3px 11px);-webkit-mask-image:linear-gradient(90deg,transparent,#000);mask-image:linear-gradient(90deg,transparent,#000);opacity:0`,
    );
    ticks.push((t) => {
      if (t < seg.t0 - 0.5 || t > seg.t1 + 0.5) return;
      const { off, v } = offAt(t);
      dash.style.transform = `translateX(${(-(off % 80)).toFixed(1)}px)`;
      streak.style.opacity = (v * 0.9).toFixed(3);
      car.style.transform = `translateX(${(v * 18).toFixed(1)}px) rotate(${(-v * 2).toFixed(2)}deg)`;
      lamps.forEach((L) => {
        const sx = L.k * SP2 - off + front,
          shown = !L.extra || t >= L.tOn,
          grow = L.extra ? easeOut((t - L.tOn) / 0.3) : 1;
        if (!shown || sx < -60 || sx > 900) {
          L.e.style.opacity = 0;
          return;
        }
        L.e.style.opacity = 1;
        L.e.style.transform = `translateX(${sx.toFixed(1)}px) scale(${grow.toFixed(3)})`;
        const near = clamp(1 - Math.abs(sx - front) / 70);
        L.lamp.style.boxShadow = `0 0 ${(8 + 40 * near).toFixed(0)}px ${(2 + 10 * near).toFixed(0)}px rgba(232,64,44,${(0.25 + 0.6 * near).toFixed(2)})`;
        L.lamp.style.opacity = (0.55 + 0.45 * near).toFixed(2);
      });
    });
    // the thirty-minute meeting and its two decisions…
    const chips = [
      div("ex-chip", rig, "MEETING · 30 MIN", "left:110px;top:520px"),
      div("ex-chip green", rig, "✓ DECISION", "left:450px;top:520px"),
      div("ex-chip green", rig, "✓ DECISION", "left:690px;top:520px"),
    ];
    chips.forEach((ch, k) => exPop(ch, c.meeting - 0.1 + k * 0.22, 0.6, 0.4));
    // …and the two pages of AI notes that land ten minutes later
    const Nt = div(
      "ex-p",
      rig,
      "",
      "left:110px;top:600px;width:860px;height:500px;overflow:hidden;transform-origin:50% 0%",
    );
    tl.fromTo(Nt, { scaleY: 0, opacity: 0 }, { scaleY: 1, opacity: 1, duration: 0.8, ease: "expo.out" }, c.pages - 0.2);
    // a solid header strip: the notes scroll up UNDER it, never through the kicker
    div("", Nt, "", "position:absolute;left:0;right:0;top:0;height:74px;background:#212227;z-index:2");
    const pg = div("ex-k", Nt, "AI NOTES · PAGE 1 OF 2", "left:34px;top:26px;z-index:2");
    ticks.push((t) => {
      pg.textContent = t < c.pages + 1.8 ? "AI NOTES · PAGE 1 OF 2" : "AI NOTES · PAGE 2 OF 2";
    });
    const sc = div("", Nt, "", "position:absolute;left:34px;right:34px;top:80px");
    const rn = mulberry32(31);
    for (let k = 0; k < 44; k++) {
      const w = k % 7 === 0 ? 30 + rn() * 20 : 60 + rn() * 38;
      div(
        "",
        sc,
        "",
        `position:relative;height:16px;margin:0 0 ${k % 7 === 6 ? 34 : 16}px;width:${w.toFixed(1)}%;border-radius:4px;background:${k % 7 === 0 ? "#4a4b52" : "#303137"}`,
      );
    }
    tl.fromTo(sc, { y: 0 }, { y: -900, duration: 7.5, ease: "power1.inOut" }, c.pages + 0.3);
    const act = div(
      "ex-blk",
      Nt,
      `<span style="font-family:'${exM}',monospace;font-size:26px;letter-spacing:.12em;color:${P.accent}">ACTION ITEM →&nbsp;</span><span style="font-size:32px">YOU</span>`,
      `left:34px;top:140px;height:72px;border-color:${P.accent};background:rgb(57,34,35);z-index:3`,
    ); // solid: the notes must not show through the words
    tl.fromTo(act, { x: -900, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "expo.out" }, c.your - 0.3);
    punch(c.your, 0.018);
    const q = div(
      "ex-t",
      Nt,
      "?",
      `left:420px;top:112px;font-size:110px;line-height:1.1;padding:0 18px;border-radius:12px;background:#1c1d21;color:${P.accent};z-index:3`,
    );
    tl.fromTo(
      q,
      { scale: 0, rotation: -30, opacity: 0 },
      { scale: 1, rotation: 8, opacity: 1, duration: 0.5, ease: "back.out(3)" },
      c.remember,
    );
    // writing got cheap, reading didn't
    const wr = div("ex-p", rig, "", `left:130px;top:880px;width:390px;height:190px;z-index:4`),
      rd = div("ex-p", rig, "", `left:560px;top:880px;width:390px;height:190px;z-index:4`);
    exIcon(wr, "pen", 76, 24, 26);
    div("ex-k", wr, "WRITING", "left:118px;top:44px");
    exIcon(rd, "eye", 76, 24, 26);
    div("ex-k", rd, "READING", "left:118px;top:44px");
    const wbar = div("ex-bar", wr, "", `left:24px;top:124px;width:342px;height:36px;background:${GREEN}`),
      rbar = div("ex-bar", rd, "", `left:24px;top:124px;width:342px;height:36px;background:${P.accent}`);
    exIn(wr, c.writing - 0.3, { y: 60 }, 0.5);
    exIn(rd, c.reading - 0.3, { y: 60 }, 0.5);
    tl.fromTo(wbar, { scaleX: 1 }, { scaleX: 0.08, duration: 0.8, ease: "power3.inOut" }, c.writing + 0.25);
    tl.fromTo(rbar, { scaleX: 0.2 }, { scaleX: 1, duration: 0.9, ease: "power3.out" }, c.reading + 0.15);
    // the point of it all: the scene steps back while the title says it
    // one scrim over the whole scene, not a fade on each card: faded cards go see-through and the notes show through their words
    const scrim = div(
      "",
      rig,
      "",
      `position:absolute;left:-300px;top:-300px;width:1680px;height:2000px;background:${P.ground};z-index:10`,
    );
    tl.fromTo(scrim, { opacity: 0 }, { opacity: 0.7, duration: 0.6 }, c.paperwork - 0.3);
    return "own-push";
  },

  // ── 5+6. Everyone builds their own agent, a hundred ways — then one shared foundation, built once ──
  found(stage, seg) {
    const c = R.scenes.found.cues,
      D = R.scenes.found;
    exLight(stage, 540, 620, 780, seg, 34, 41);
    const rig = exRig(stage, seg, { rotationX: 10, rotationY: 8 }, { rotationX: 4, rotationY: -8 });
    // A. one model, handed to five people
    const five = div("rig3d", rig, "", "transform-origin:540px 700px");
    const M = div("ex-p", five, "", "left:390px;top:180px;width:300px;height:170px");
    div("ex-k", M, "MODEL", "left:26px;top:22px");
    const mc = exPoint(M, 16);
    exAt(mc, 150, 100);
    exIn(M, c.hand - 1.3, { y: -60, scale: 0.8 }, 0.6);
    tl.fromTo(M, { opacity: 1 }, { opacity: 0.0, duration: 0.4, ...IR }, c.hand + 0.4);
    const xs = [150, 345, 540, 735, 930],
      rn = mulberry32(5);
    const PARTS = ["memory", "notes", "tools", "access", "prompts", "scripts", "docs", "keys"];
    xs.forEach((x, i) => {
      const per = exIcon(five, "person", 84, x - 42, 900);
      exPop(per, c.hand - 1.0 + i * 0.08, 0.4, 0.4);
      const cp = div(
        "ex-blk",
        five,
        `<span style="font-family:'${exM}',monospace;font-size:18px;letter-spacing:.12em;color:${P.dim}">MODEL</span>`,
        `left:${x - 75}px;top:800px;width:150px;height:84px;justify-content:center;padding:0`,
      );
      tl.fromTo(
        cp,
        { x: 540 - x, y: 180 + 85 - 842, scale: 0.6, opacity: 0 },
        { x: 0, y: 0, scale: 1, opacity: 1, duration: 0.7, ease: "power3.inOut" },
        c.hand + 0.05 + i * 0.07,
      );
      // B. what a model doesn't know: two empty, dashed slots
      const slots = [0, 1].map((k) =>
        div(
          "",
          five,
          `<span style="position:absolute;left:0;right:0;top:12px;text-align:center;font-weight:800;font-size:32px;color:${P.accent}">?</span>`,
          `position:absolute;left:${x - 60}px;top:${720 - k * 74}px;width:120px;height:62px;border:3px dashed ${P.accent};border-radius:5px`,
        ),
      );
      slots.forEach((s, k) => {
        exPop(s, (k ? c.remember : c.know) - 0.1 + i * 0.05, 0.4, 0.35);
        tl.fromTo(s, { opacity: 1 }, { opacity: 0, duration: 0.2, ...IR }, c.builds + i * 0.05);
      });
      // C. everyone builds the rest themselves: a wobbly stack of homemade parts, different for every person
      const nb = 3 + Math.floor(rn() * 3);
      for (let k = 0; k < nb; k++) {
        const w = 110 + rn() * 70,
          h = 50 + rn() * 16,
          tilt = (rn() - 0.5) * 12,
          sh = (rn() - 0.5) * 30;
        const b = div(
          "ex-blk",
          five,
          `<span style="font-family:'${exM}',monospace;font-size:17px;letter-spacing:.08em;color:${P.dim}">${PARTS[Math.floor(rn() * PARTS.length)]}</span>`,
          `left:${x - w / 2 + sh}px;top:${730 - k * 66}px;width:${w.toFixed(0)}px;height:${h.toFixed(0)}px;justify-content:center;padding:0;background:${["#24252b", "#2b2c33", "#1f2025"][k % 3]}`,
        );
        tl.fromTo(
          b,
          { y: -300, opacity: 0, rotation: tilt * 3 },
          { y: 0, opacity: 1, rotation: tilt, duration: 0.5, ease: "bounce.out" },
          c.builds - 0.1 + i * 0.09 + k * 0.12,
        );
      }
    });
    // D. "a hundred science projects": the five shrink into a wall of a hundred different ones
    tl.fromTo(
      five,
      { scale: 1, opacity: 1 },
      { scale: 0.18, opacity: 0, duration: 0.9, ease: "power3.inOut" },
      c.strategy - 0.2,
    );
    const G = svg(
      "svg",
      { width: 1080, height: 1400, viewBox: "0 0 1080 1400", style: "position:absolute;left:0;top:0;overflow:visible" },
      rig,
    );
    const cells = [],
      rg = mulberry32(77);
    for (let r = 0; r < 10; r++)
      for (let q = 0; q < 10; q++) {
        const x = 135 + q * 90,
          y = 190 + r * 92,
          g = svg("g", {}, G),
          inner = svg("g", {}, g),
          nb = 2 + Math.floor(rg() * 3),
          blocks = [];
        for (let k = 0; k < nb; k++) {
          const w = 34 + rg() * 30,
            h = 11 + rg() * 5,
            tt = (rg() - 0.5) * 16;
          blocks.push(
            svg(
              "rect",
              {
                x: x - w / 2 + (rg() - 0.5) * 10,
                y: y + 18 - (k + 1) * (h + 3),
                width: w,
                height: h,
                rx: 2,
                fill: ["#3a3b42", "#2c2d33", "#46474f"][Math.floor(rg() * 3)],
                transform: `rotate(${tt.toFixed(1)} ${x} ${y})`,
              },
              inner,
            ),
          );
        }
        svg("circle", { cx: x, cy: y + 30, r: 6, fill: P.dim }, inner);
        const ck = svg(
          "path",
          {
            d: `M${x + 18} ${y - 34} l5 5 l10 -12`,
            fill: "none",
            stroke: GREEN,
            "stroke-width": 4,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
          },
          g,
        );
        const d = Math.hypot(q - 4.5, r - 4.5);
        tl.fromTo(
          inner,
          { scale: 0, opacity: 0, svgOrigin: `${x} ${y}` },
          { scale: 1, opacity: 1, svgOrigin: `${x} ${y}`, duration: 0.45, ease: "back.out(2)" },
          c.hundred - 0.4 + d * 0.09,
        );
        tl.fromTo(ck, { opacity: 0 }, { opacity: 1, duration: 0.2 }, c.quiet - 0.6 + d * 0.04);
        cells.push({ g, inner, blocks, x, y, d, fail: rg() < 0.14 });
      }
    // E. "the failures are quiet": some quietly fall apart, and the green check stays on
    cells
      .filter((cl) => cl.fail)
      .forEach((cl, k) => {
        const top = cl.blocks[cl.blocks.length - 1];
        tl.fromTo(
          top,
          { x: 0, y: 0, opacity: 1 },
          { x: 22, y: 30, opacity: 0.55, duration: 0.5, ease: "bounce.out" },
          c.quiet + 0.05 + k * 0.05,
        );
        const cr = svg(
          "path",
          { d: `M${cl.x - 14} ${cl.y - 6} l8 8 l-6 6 l10 8`, fill: "none", stroke: P.accent, "stroke-width": 3 },
          cl.g,
        );
        exDraw(cr, c.quiet + 0.1 + k * 0.05, 0.3);
      });
    // G. "build the rest ONCE, for everyone": the hundred projects pour down into one foundation
    const fx0 = 150,
      fy0 = 620,
      fw = 780,
      fh = 490;
    cells.forEach((cl, k) => {
      const tx = fx0 + 60 + (k % 10) * 66 - cl.x,
        ty = fy0 + fh - 40 - cl.y;
      tl.fromTo(
        cl.g,
        { x: 0, y: 0, scale: 1, opacity: 1, svgOrigin: `${cl.x} ${cl.y}` },
        { x: tx, y: ty, scale: 0.2, opacity: 0, svgOrigin: `${cl.x} ${cl.y}`, duration: 0.7, ease: "power3.in" },
        c.once - 0.5 + (9 - Math.floor(k / 10)) * 0.05 + (k % 10) * 0.015,
      );
    });
    const F = svg("svg", { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" }, rig);
    const frame = svg(
      "rect",
      {
        x: fx0,
        y: fy0,
        width: fw,
        height: fh,
        rx: 6,
        fill: "rgba(232,64,44,.04)",
        stroke: P.accent,
        "stroke-width": 4,
        "stroke-dasharray": "14 9",
      },
      F,
    );
    tl.fromTo(
      frame,
      { opacity: 0, scaleY: 0, svgOrigin: `540 ${fy0 + fh}` },
      { opacity: 1, scaleY: 1, svgOrigin: `540 ${fy0 + fh}`, duration: 0.7, ease: "expo.out" },
      c.everyone - 0.25,
    );
    exRing(rig, c.everyone + 0.1, 540, fy0 + fh - 40, 420, 0.9);
    const fk = div("ex-k red", rig, "ONE FOUNDATION · SET UP ONCE", `left:${fx0}px;top:${fy0 - 42}px`);
    tl.fromTo(fk, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.4 }, c.shared - 0.1);
    // H. the layers, each on its word, bottom up
    const cuesL = [c.l0, c.l1, c.l2, c.l3, c.l4],
      layers = D.layers.map((lab, i) => {
        const y = fy0 + fh - 22 - (i + 1) * 88;
        const b = div(
          "ex-blk",
          rig,
          `<span style="font-family:'${exM}',monospace;font-size:20px;color:${P.accent};letter-spacing:.1em;margin-right:22px">0${i + 1}</span><span style="font-size:32px">${lab}</span>`,
          `left:${fx0 + 20}px;top:${y}px;width:${fw - 40}px;height:74px`,
        );
        tw3(
          b,
          { x: i % 2 ? 900 : -900, rotationY: i % 2 ? -40 : 40, opacity: 0, ...TP },
          { x: 0, rotationY: 0, opacity: 1, ...TP, duration: 0.6, ease: "expo.out" },
          cuesL[i] - 0.25,
        );
        tl.fromTo(b, { borderColor: P.accent }, { borderColor: P.line, duration: 0.9, ...IR }, cuesL[i] + 0.3);
        return b;
      });
    // the agents that stand on it
    const ag = D.agents.map((lab, i) => {
      const b = div(
        "ex-blk",
        rig,
        `<span style="display:inline-block;width:18px;height:18px;border-radius:50%;background:${P.accent};box-shadow:0 0 16px ${P.accent};margin-right:14px"></span><span style="font-size:26px">${lab}</span>`,
        `left:${fx0 + i * 268}px;top:${fy0 - 150}px;width:244px;height:74px;justify-content:center;padding:0`,
      );
      tl.fromTo(
        b,
        { y: -380, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.6, ease: "bounce.out" },
        c.l4 + 0.7 + i * 0.12,
      );
      return b;
    });
    // I. build it or buy it — one system
    const bb = [
      div("ex-chip", rig, "BUILD", "left:260px;top:300px"),
      div("ex-chip", rig, "BUY", "left:720px;top:300px"),
    ];
    bb.forEach((b, k) => {
      exPop(b, c.build + k * 0.5, 0.5, 0.4);
      tl.fromTo(
        b,
        { x: 0, opacity: 1 },
        { x: k ? -190 : 180, opacity: 0, duration: 0.35, ease: "power3.in", ...IR },
        c.one - 0.3,
      );
    });
    const one = div("ex-chip red", rig, "ONE SYSTEM", "left:448px;top:300px");
    exPop(one, c.one, 0.4, 0.5);
    tl.fromTo(
      frame,
      { attr: { "stroke-width": 4 } },
      { attr: { "stroke-width": 9 }, duration: 0.15, yoyo: true, repeat: 1, ...IR },
      c.one + 0.05,
    );
    // J. not fifteen products that don't talk to each other, bought off a nice slide
    const spots = [
      [40, 150],
      [200, 110],
      [360, 150],
      [560, 110],
      [720, 150],
      [880, 110],
      [40, 300],
      [880, 300],
      [20, 460],
      [920, 460],
      [20, 640],
      [930, 640],
      [20, 820],
      [930, 820],
      [460, 170],
    ];
    const prods = spots.map(([x, y], k) => {
      const p = div(
        "ex-p",
        rig,
        `<div style="position:absolute;left:18px;top:14px;width:30px;height:30px;border-radius:${k % 3 === 0 ? "50%" : k % 3 === 1 ? "4px" : "0"};background:${["#5b5d64", "#7a7c84", "#3f4046"][k % 3]}"></div><div style="position:absolute;left:58px;top:20px;width:52px;height:8px;border-radius:4px;background:#3a3b41"></div><div style="position:absolute;left:58px;top:34px;width:34px;height:8px;border-radius:4px;background:#3a3b41"></div>`,
        `left:${x}px;top:${y}px;width:130px;height:62px;z-index:5`,
      );
      tl.fromTo(
        p,
        { scale: 0, opacity: 0, rotation: (k % 2 ? 1 : -1) * 30 },
        { scale: 1, opacity: 1, rotation: (k % 2 ? 1 : -1) * 4, duration: 0.45, ease: "back.out(2)" },
        c.fifteen - 0.1 + k * 0.045,
      );
      // the nice slide: a glossy little chart with an arrow pointing up
      const sl = div(
        "",
        p,
        `<svg viewBox="0 0 130 62" width="130" height="62"><rect x="0" y="0" width="130" height="62" rx="6" fill="#f4f4f2"/><rect x="18" y="36" width="14" height="14" fill="#9b9da4"/><rect x="40" y="28" width="14" height="22" fill="#9b9da4"/><rect x="62" y="18" width="14" height="32" fill="#e8402c"/><path d="M88 44 L110 16 M100 16h10v10" stroke="#e8402c" stroke-width="5" fill="none"/></svg>`,
        "position:absolute;inset:-3px",
      );
      tl.fromTo(
        sl,
        { opacity: 0, rotationY: -90, ...TP },
        { opacity: 1, rotationY: 0, ...TP, duration: 0.35, ease: "power3.out" },
        c.slide - 0.15 + k * 0.03,
      );
      const [ox, oy] = [(x < 540 ? -700 : 700) * EXIT, ((k % 5) - 2) * 120];
      tl.fromTo(p, { x: 0, y: 0 }, { x: ox, y: oy, duration: 0.5, ease: "power3.in", ...IR }, c.slide + 0.7 + k * 0.02);
      return p;
    });
    const links = svg(
      "svg",
      { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible;z-index:6" },
      rig,
    );
    // neighbors along the edges only: a link across the middle ran through the agents, ONE SYSTEM and the layers
    [
      [0, 1],
      [2, 14],
      [3, 4],
      [5, 7],
      [6, 8],
      [10, 12],
      [9, 11],
    ].forEach(([ia, ib], j) => {
      const k = j * 2,
        [a, b] = [spots[ia], spots[ib]],
        x1 = a[0] + 65,
        y1 = a[1] + 31,
        x2 = b[0] + 65,
        y2 = b[1] + 31;
      const l = svg("line", { x1, y1, x2, y2, stroke: P.dim, "stroke-width": 3, "stroke-dasharray": "6 6" }, links);
      tl.fromTo(l, { opacity: 0 }, { opacity: 0.8, duration: 0.2 }, c.talk - 0.3 + k * 0.03);
      const mx = (x1 + x2) / 2,
        my = (y1 + y2) / 2,
        xx = svg(
          "path",
          {
            d: `M${mx - 12} ${my - 12} L${mx + 12} ${my + 12} M${mx + 12} ${my - 12} L${mx - 12} ${my + 12}`,
            stroke: P.accent,
            "stroke-width": 6,
            "stroke-linecap": "round",
          },
          links,
        );
      tl.fromTo(
        xx,
        { opacity: 0, scale: 2.2, svgOrigin: `${mx} ${my}` },
        { opacity: 1, scale: 1, svgOrigin: `${mx} ${my}`, duration: 0.3, ease: "back.out(3)" },
        c.talk + 0.05 + k * 0.04,
      );
      tl.fromTo([l, xx], { opacity: 1 }, { opacity: 0, duration: 0.3, ...IR }, c.slide + 0.6);
    });
    // K. give the knowledge an owner
    const kn = layers[1],
      own = div("ex-chip red", rig, "OWNER", `left:${fx0 + fw - 150}px;top:${fy0 + fh - 22 - 2 * 88 + 16}px;z-index:4`);
    tl.fromTo(own, { x: 400, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.6)" }, c.owner - 0.35);
    tl.fromTo(
      kn,
      { borderColor: P.line, boxShadow: "0 0 0px rgba(232,64,44,0)" },
      { borderColor: P.accent, boxShadow: "0 0 50px rgba(232,64,44,.45)", duration: 0.35, ...IR },
      c.owner - 0.3,
    );
    // L. left uncurated, it made agents worse than having none
    tl.fromTo(
      [...layers, own, ...ag, one, fk],
      { opacity: 1 },
      { opacity: 0.12, duration: 0.5, ...IR },
      c.uncurated - 0.35,
    );
    const Bp = div(
      "ex-p",
      rig,
      "",
      `left:${fx0 + 20}px;top:${fy0 + 30}px;width:${fw - 40}px;height:${fh - 60}px;z-index:7`,
    );
    div("ex-k", Bp, "AGENT SUCCESS · HARDEST TASKS", "left:30px;top:26px");
    exIn(Bp, c.uncurated - 0.3, { y: 60, scale: 0.94 }, 0.5);
    const bw = 400 / 70; // px per point (440 pushed "66.4%" past the panel's edge)
    D.bars.forEach(([lab, v], i) => {
      const y = 100 + i * 96,
        red = i === 2;
      div("ex-t", Bp, lab, `left:30px;top:${y + 6}px;font-size:30px;color:${red ? P.accent : P.ink}`);
      const b = div(
        "ex-bar",
        Bp,
        "",
        `left:230px;top:${y}px;width:${(v * bw).toFixed(1)}px;background:${red ? P.accent : i === 1 ? P.dim : P.ink}`,
      );
      tl.fromTo(b, { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: "power3.out" }, c.uncurated + 0.1 + i * 0.28);
      const vx = Math.max(230 + v * bw + 16, v < 52.5 ? 230 + 52.5 * bw + 14 : 0); // a label never sits on the dashed 52.5 line
      const vv = div(
        "ex-m",
        Bp,
        v.toFixed(1) + "%",
        `left:${vx.toFixed(0)}px;top:${y + 6}px;font-size:28px;color:${red ? P.accent : P.ink}`,
      );
      tl.fromTo(vv, { opacity: 0 }, { opacity: 1, duration: 0.3 }, c.uncurated + 0.5 + i * 0.28);
    });
    const ref = div(
      "",
      Bp,
      "",
      `position:absolute;left:${(230 + 52.5 * bw).toFixed(0)}px;top:84px;width:0;height:290px;border-left:3px dashed ${P.dim}`,
    );
    tl.fromTo(ref, { opacity: 0 }, { opacity: 1, duration: 0.3 }, c.uncurated + 0.7);
    const wz = div("ex-chip red", Bp, "WORSE THAN NONE", "left:230px;top:354px");
    exPop(wz, c.worse - 0.1, 0.5, 0.4);
    punch(c.worse, 0.015);
    return "own-push";
  },

  // ── 7. The flip: the engineer stops being a courier; the agent runs around, the person decides, inside limits ──
  courier(stage, seg) {
    const c = R.scenes.courier.cues;
    exLight(stage, 540, 640, 780, seg, 28, 61);
    const rig = exRig(stage, seg, { rotationX: 14, rotationY: -10 }, { rotationX: 4, rotationY: 8 });
    const cx = 540,
      cy = 640;
    // [label, icon, x, y, width]: "OTHER TEAM" needs a wider card, grown to the left so the docks stay put; on a
    // vertical frame it starts at 120, not 60: a phone's full-screen player crops about 9% off each side
    const SYS = [
      ["TICKET", "ticket", 130, 260, 220],
      ["CODE", "code", 730, 260, 220],
      ["LOGS", "logs", 730, 910, 220],
      ["OTHER TEAM", "team", LAND ? 60 : 120, 910, 290],
    ];
    const ctr = SYS.map(([, , x, y, w]) => ({ x: x + w / 2, y: y + 55 }));
    const dock = SYS.map(([, , x, y, w]) => ({ x: x < cx ? x + w + 50 : x - 50, y: y < cy ? y + 160 : y - 50 }));
    const lines = svg(
      "svg",
      { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" },
      rig,
    );
    const spokes = ctr.map((p) =>
      svg("line", { x1: cx, y1: cy, x2: p.x, y2: p.y, stroke: P.line, "stroke-width": 4 }, lines),
    );
    const nodes = SYS.map(([lab, ic, x, y, w], k) => {
      const n = div("ex-p", rig, "", `left:${x}px;top:${y}px;width:${w}px;height:110px`);
      exIcon(n, ic, 62, 18, 22);
      div("ex-k", n, lab, "left:92px;top:42px");
      exIn(n, seg.t0 + 0.1 + k * 0.1, { scale: 0.7, y: 40 }, 0.5);
      return n;
    });
    // the engineer, carrying things between systems (a red trail of every trip), and the bill running
    const perPos = div("", rig, "", "position:absolute;left:0;top:0;width:0;height:0");
    const per = div(
      "ex-p",
      perPos,
      "",
      "left:-60px;top:-60px;width:120px;height:120px;border-radius:60px;border-color:#fff",
    );
    exIcon(per, "person", 84, 15, 14);
    const cost = div("ex-chip red", per, "$", "left:96px;top:-24px");
    exPop(cost, c.expensive, 0.4, 0.4);
    const hops = [c.s0, c.s1, c.s2, c.s3, c.s4],
      stops = [0, 1, 2, 3, 0];
    ticks.push((t) => {
      let n = 0;
      hops.forEach((h) => {
        if (t >= h) n++;
      });
      cost.textContent = "$".repeat(1 + n);
    });
    const keys = [[seg.t0, cx, cy]];
    hops.forEach((h, k) => {
      keys.push([h - 0.3, keys[keys.length - 1][1], keys[keys.length - 1][2]]);
      keys.push([h + 0.1, dock[stops[k]].x, dock[stops[k]].y]);
    });
    keys.push([c.instead - 0.1, dock[0].x, dock[0].y], [c.instead + 0.4, cx, 106]);
    const path = exPath(keys);
    exPop(per, seg.t0 + 0.35, 0.4, 0.45);
    tl.fromTo(
      per,
      { borderColor: "#fff", boxShadow: "0 0 0px rgba(255,255,255,0)" },
      {
        borderColor: "#fff",
        boxShadow: "0 0 60px rgba(255,255,255,.35)",
        duration: 0.25,
        yoyo: true,
        repeat: 1,
        ...IR,
      },
      c.engineer,
    );
    const trail = svg(
      "polyline",
      {
        fill: "none",
        stroke: P.accent,
        "stroke-width": 6,
        "stroke-linejoin": "round",
        "stroke-linecap": "round",
        opacity: 0.85,
      },
      lines,
    );
    ticks.push((t) => {
      const p = path(t);
      exAt(perPos, p.x, p.y);
      if (p.x > cx + 20) {
        cost.style.left = "auto";
        cost.style.right = "96px";
      } else {
        cost.style.right = "auto";
        cost.style.left = "96px";
      }
      if (t < c.s0 - 0.3 || t > c.instead + 0.6) {
        trail.setAttribute("points", "");
        return;
      }
      let pts = `${cx},${cy} `;
      for (let s = c.s0 - 0.3; s < Math.min(t, c.instead - 0.1); s += 0.05) {
        const q = path(s);
        pts += `${q.x.toFixed(0)},${q.y.toFixed(0)} `;
      }
      trail.setAttribute("points", pts);
      trail.setAttribute("opacity", (0.85 * clamp(1 - (t - c.instead + 0.1) / 0.4)).toFixed(3));
    });
    hops.forEach((h, k) =>
      tl.fromTo(nodes[stops[k]], { borderColor: "#fff" }, { borderColor: P.line, duration: 0.5, ...IR }, h + 0.1),
    );
    tl.fromTo(cost, { opacity: 1 }, { opacity: 0, duration: 0.3, ...IR }, c.instead + 0.1);
    const ask = div("ex-t", rig, "?", `left:${cx + 76}px;top:30px;font-size:96px;color:${P.accent}`);
    tl.fromTo(
      ask,
      { scale: 0, opacity: 0, rotation: -20 },
      { scale: 1, opacity: 1, rotation: 6, duration: 0.45, ease: "back.out(3)" },
      c.ask,
    );
    // the agent takes the middle and does the running around, all four at once
    const ag = exPoint(rig, 26);
    exAt(ag, cx, cy, 0);
    ticks.push((t) => {
      const s = clamp((t - c.agent + 0.3) / 0.35);
      exAt(ag, cx, cy, s < 1 ? easeOut(s) * 1.15 : 1 + 0.06 * Math.sin((t - c.agent) * 5));
    });
    exRing(rig, c.agent + 0.05, cx, cy, 260, 0.8);
    spokes.forEach((sp, k) =>
      tl.fromTo(
        sp,
        { stroke: P.line, opacity: 1 },
        { stroke: "#56575e", opacity: 1, duration: 0.3 },
        c.agent - 0.1 + k * 0.05,
      ),
    );
    const packets = [];
    ctr.forEach((p, k) =>
      [0, 0.33, 0.66].forEach((ph) =>
        packets.push({
          p,
          ph,
          head: svg("circle", { r: 11, fill: P.accent, opacity: 0 }, lines),
          tail: svg(
            "polyline",
            { fill: "none", stroke: P.accent, "stroke-width": 6, "stroke-linecap": "round", opacity: 0 },
            lines,
          ),
        }),
      ),
    );
    ticks.push((t) => {
      const on = t > c.agent + 0.15 && t < c.decides + 1.6;
      packets.forEach(({ p, ph, head, tail }) => {
        if (!on) {
          head.setAttribute("opacity", 0);
          tail.setAttribute("opacity", 0);
          return;
        }
        const q = ((t - c.agent) / 1.1 + ph) % 1,
          tri = q < 0.5 ? q * 2 : 2 - q * 2,
          e = easeInOut(tri);
        const at = (u) => ({ x: cx + (p.x - cx) * u, y: cy + (p.y - cy) * u });
        const h = at(e),
          back = at(clamp(e + (q < 0.5 ? -0.12 : 0.12)));
        head.setAttribute("cx", h.x);
        head.setAttribute("cy", h.y);
        head.setAttribute("opacity", 1);
        tail.setAttribute("points", `${back.x.toFixed(1)},${back.y.toFixed(1)} ${h.x.toFixed(1)},${h.y.toFixed(1)}`);
        tail.setAttribute("opacity", 0.6);
      });
    });
    // what it found goes up to the person, who decides; the agent writes it down in the ticket
    const up = svg(
      "line",
      { x1: cx, y1: cy - 40, x2: cx, y2: 214, stroke: P.accent, "stroke-width": 6, "stroke-linecap": "round" },
      lines,
    );
    exDraw(up, c.decides - 0.6, 0.45);
    const dec = div("ex-chip", rig, "✓ DECIDES", `left:${cx - 100}px;top:172px;border-color:#fff`);
    exPop(dec, c.decides - 0.1, 0.5, 0.4);
    const down = svg(
      "path",
      {
        d: `M${cx - 30} ${cy - 20} Q ${cx - 200} ${cy - 250} ${ctr[0].x + 60} ${ctr[0].y + 50}`,
        fill: "none",
        stroke: P.accent,
        "stroke-width": 6,
        "stroke-linecap": "round",
      },
      lines,
    );
    exDraw(down, c.writes - 0.2, 0.45);
    const note = div(
      "",
      nodes[0],
      `<div style="height:7px;border-radius:4px;background:${P.accent};margin-bottom:7px;width:90%"></div><div style="height:7px;border-radius:4px;background:${P.accent};width:60%"></div>`,
      "position:absolute;left:92px;top:76px;width:110px",
    );
    tl.fromTo(
      note.children,
      { scaleX: 0, transformOrigin: "0 50%" },
      { scaleX: 1, duration: 0.3, stagger: 0.12, ease: "power2.out" },
      c.writes + 0.2,
    );
    tl.fromTo(nodes[0], { borderColor: P.line }, { borderColor: P.accent, duration: 0.3, ...IR }, c.writes + 0.2);
    // humans decide, agents coordinate — inside hard limits
    const co = div("ex-chip red", rig, "COORDINATES", `left:${cx - 116}px;top:${cy + 70}px`);
    exPop(co, c.coord - 0.2, 0.5, 0.4);
    tl.fromTo(dec, { scale: 1 }, { scale: 1.15, duration: 0.18, yoyo: true, repeat: 1, ...IR }, c.humans);
    const box = svg(
      "rect",
      {
        x: 100,
        y: 236,
        width: 880,
        height: 816,
        rx: 10,
        fill: "none",
        stroke: P.accent,
        "stroke-width": 5,
        "stroke-dasharray": "16 10",
      },
      lines,
    );
    tl.fromTo(
      box,
      { opacity: 0, scale: 1.12, svgOrigin: `${cx} ${cy}` },
      { opacity: 1, scale: 1, svgOrigin: `${cx} ${cy}`, duration: 0.5, ease: "expo.out" },
      c.limits - 0.15,
    );
    ticks.push((t) => {
      if (t > c.limits - 0.2 && t < seg.t1 + 0.5)
        box.setAttribute("stroke-dashoffset", (-(t - c.limits) * 60).toFixed(1));
    });
    ctr.forEach((p, k) => {
      const lk = exIcon(rig, "lock", 58, (cx + p.x) / 2 - 29, (cy + p.y) / 2 - 29);
      exPop(lk, c.limits + 0.1 + k * 0.08, 0.3, 0.4);
    });
    return "own-push";
  },

  // ── 8. Give the agent to the job; when Joe leaves it stays. Count results, and check them ──
  joe(stage, seg) {
    const c = R.scenes.joe.cues;
    exLight(stage, 540, 560, 760, seg, 26, 71);
    const rig = exRig(stage, seg, { rotationX: 10, rotationY: 10 }, { rotationX: 3, rotationY: -7 });
    const part1 = div("rig3d", rig);
    const Cd = div("ex-p", part1, "", "left:140px;top:150px;width:800px;height:320px");
    div("ex-k", Cd, "THE JOB · REPORTING LEAD", "left:34px;top:28px");
    exIn(Cd, seg.t0 + 0.05, { y: -60, scale: 0.9 }, 0.6);
    const slot = div(
      "",
      Cd,
      "",
      `position:absolute;left:60px;top:100px;width:170px;height:170px;border-radius:85px;border:3px dashed ${P.dim}`,
    );
    exPop(slot, c.person - 0.2, 0.5, 0.35);
    const agb = div(
      "ex-blk",
      Cd,
      `<span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:${P.accent};box-shadow:0 0 20px ${P.accent};margin-right:16px"></span><span style="font-family:'${exM}',monospace;font-size:26px;letter-spacing:.14em">AGENT</span>`,
      "left:470px;top:140px;width:280px;height:92px;justify-content:center;padding:0",
    );
    tl.fromTo(
      agb,
      { x: 520, y: -300, rotation: 25, opacity: 0 },
      { x: 0, y: 0, rotation: 0, opacity: 1, duration: 0.55, ease: "power3.out" },
      c.job - 0.45,
    );
    exRing(part1, c.job + 0.1, 140 + 610, 150 + 186, 150, 0.6);
    // Joe, the only one who understands the big spreadsheet
    const joe = div("", part1, "", "position:absolute;left:200px;top:250px;width:170px;height:200px");
    exIcon(joe, "person", 130, 20, 6);
    div("ex-t", joe, "JOE", "left:0;right:0;top:178px;text-align:center;font-size:34px"); // below the dashed slot, not across it
    exIn(joe, c.joe - 0.3, { x: -500, rotation: -12 }, 0.5);
    const others = [
      [190, 1030],
      [330, 1060],
      [760, 1040],
      [900, 1010],
    ].map(([x, y], k) => {
      const o = div(
        "",
        part1,
        `<svg viewBox="0 0 84 84" width="84" height="84" style="opacity:.45">${GLX.person}</svg><div class="ex-t" style="left:52px;top:-34px;font-size:52px;color:${P.accent}">?</div>`,
        `position:absolute;left:${x - 42}px;top:${y - 42}px;width:84px;height:84px`,
      );
      exPop(o, c.only + k * 0.1, 0.4, 0.4);
      return o;
    });
    const Sh = div("ex-p", part1, "", "left:240px;top:560px;width:600px;height:380px");
    div("ex-k", Sh, "THE BIG SPREADSHEET", "left:30px;top:24px");
    exIn(Sh, c.sheet - 0.5, { y: 80, rotation: 3 }, 0.55);
    const rs = mulberry32(13);
    for (let r = 0; r < 6; r++)
      for (let q = 0; q < 6; q++) {
        const cell = div(
          "",
          Sh,
          `<div style="height:10px;margin:18px 12px 0;border-radius:4px;background:${(r + q) % 5 === 0 ? P.accent : "#3a3b41"};width:${(35 + rs() * 50).toFixed(0)}%"></div>`,
          `position:absolute;left:${30 + q * 90}px;top:${70 + r * 48}px;width:88px;height:46px;border:2px solid ${P.line}`,
        );
        tl.fromTo(cell, { opacity: 0 }, { opacity: 1, duration: 0.15 }, c.sheet - 0.3 + (r * 6 + q) * 0.018);
      }
    const L = svg(
      "svg",
      { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" },
      part1,
    );
    const jl = svg(
      "path",
      { d: "M285 478 C 285 530, 420 520, 460 560", fill: "none", stroke: "#fff", "stroke-width": 5 },
      L,
    );
    exDraw(jl, c.sheet - 0.1, 0.4);
    // when Joe leaves: he goes, his link snaps — and the agent's link holds, and what it knows stays
    tl.fromTo(
      joe,
      { x: 0, rotation: 0, opacity: 1 },
      { x: 1000 * EXIT, rotation: 14, opacity: 1, duration: 0.6, ease: "power3.in", ...IR },
      c.leaves - 0.25,
    );
    tl.fromTo(jl, { opacity: 1 }, { opacity: 0, duration: 0.2, ...IR }, c.leaves);
    const al = svg(
      "path",
      { d: "M750 382 C 750 470, 680 500, 640 560", fill: "none", stroke: P.accent, "stroke-width": 6 },
      L,
    );
    exDraw(al, c.stays - 0.4, 0.45);
    exRing(part1, c.stays + 0.05, 750, 336, 180, 0.7);
    const flow = [0, 1, 2, 3, 4].map(() => svg("circle", { r: 9, fill: P.accent, opacity: 0 }, L));
    ticks.push((t) =>
      flow.forEach((d, k) => {
        const q = (t - c.knows + 0.6) / 0.9 - k * 0.18;
        if (q < 0 || q > 1 || t > c.seats) {
          d.setAttribute("opacity", 0);
          return;
        }
        const u = easeInOut(q),
          x = 640 + (750 - 640) * u,
          y = 560 - (560 - 382) * u;
        d.setAttribute("cx", x);
        d.setAttribute("cy", y);
        d.setAttribute("opacity", 1);
      }),
    );
    const nh = div("", part1, "", "position:absolute;left:200px;top:250px;width:170px;height:200px");
    exIcon(nh, "person", 130, 20, 6);
    div("ex-t", nh, "NEW HIRE", `left:-20px;right:-20px;top:180px;text-align:center;font-size:30px;color:${P.accent}`);
    exIn(nh, c.knows - 0.2, { x: -600 }, 0.6);
    // stop counting seats, count results — and check them, because agents grade themselves generously
    tl.fromTo(
      part1,
      { y: 0, opacity: 1 },
      { y: -500, opacity: 0, duration: 0.6, ease: "power3.in", ...IR },
      c.seats - 1.0,
    );
    const Se = div("ex-p", rig, "", "left:140px;top:170px;width:800px;height:420px");
    div("ex-k", Se, "SEATS", "left:34px;top:28px");
    for (let k = 0; k < 24; k++) {
      const ch = exIcon(Se, "chair", 70, 40 + (k % 8) * 90, 90 + Math.floor(k / 8) * 96);
      exPop(ch, c.seats - 0.75 + k * 0.025, 0.3, 0.3);
    }
    exIn(Se, c.seats - 0.85, { y: 200, scale: 0.9 }, 0.45);
    const strike = svg(
      "svg",
      { width: 800, height: 420, style: "position:absolute;left:0;top:0;overflow:visible" },
      Se,
    );
    const st = svg(
      "line",
      { x1: 20, y1: 380, x2: 780, y2: 60, stroke: P.accent, "stroke-width": 12, "stroke-linecap": "round" },
      strike,
    );
    exDraw(st, c.seats + 0.05, 0.3, "power3.out");
    tw3(
      Se,
      { rotationY: 0, ...TP },
      { rotationY: 90, ...TP, duration: 0.25, ease: "power2.in", ...IR },
      c.results - 0.35,
    );
    const Rs = div("ex-p", rig, "", "left:140px;top:170px;width:800px;height:420px");
    div("ex-k", Rs, "RESULTS", "left:34px;top:28px");
    tw3(
      Rs,
      { rotationY: -90, opacity: 0, ...TP },
      { rotationY: 0, opacity: 1, ...TP, duration: 0.35, ease: "power3.out" },
      c.results - 0.1,
    );
    ["Outage investigated", "Month closed", "Customer onboarded"].forEach((lab, k) => {
      const r = div(
        "",
        Rs,
        `<svg viewBox="0 0 10 10" width="44" height="44" style="position:absolute;left:0;top:2px;overflow:visible"><path d="M1.2 5.4 L4 8.1 L8.9 1.8" fill="none" stroke="${GREEN}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg><div class="ex-t" style="left:66px;top:0;font-size:40px">${lab}</div>`,
        `position:absolute;left:44px;top:${110 + k * 92}px;width:700px;height:60px`,
      );
      exIn(r, c.results + 0.1 + k * 0.3, { x: 80 }, 0.4);
    });
    const mg = exIcon(rig, "mag", 150, 0, 0);
    tl.fromTo(
      mg,
      { x: 100, y: 230, opacity: 0, rotation: -10 },
      { x: 720, y: 400, opacity: 1, rotation: 10, duration: 1.3, ease: "power2.inOut" },
      c.check - 0.1,
    );
    tl.fromTo(mg, { opacity: 1 }, { opacity: 0, duration: 0.3, ...IR }, c.check + 1.4);
    // the agent's own report card: A+. Then the stamp
    const Rc = div("ex-p", rig, "", "left:290px;top:680px;width:500px;height:340px");
    div("ex-k", Rc, "AGENT SELF-GRADE", "left:30px;top:26px");
    exIn(Rc, c.grade - 0.6, { y: 120, rotation: -4 }, 0.5);
    const ap = div(
      "ex-t",
      Rc,
      "A+",
      `left:0;right:0;top:62px;text-align:center;font-size:140px;font-weight:800;color:${GREEN}`,
    );
    exPop(ap, c.grade - 0.1, 0.3, 0.5, "back.out(2.5)");
    // the stamp lands UNDER the grade, so the A+ stays readable
    const stamp = div(
      "ex-chip red",
      Rc,
      "CHECK IT",
      "left:105px;top:242px;font-size:36px;padding:10px 24px;border-width:5px;color:#e8402c",
    );
    tl.fromTo(
      stamp,
      { scale: 2.6, rotation: -24, opacity: 0 },
      { scale: 1, rotation: -6, opacity: 1, duration: 0.28, ease: "power4.in" },
      c.generously - 0.35,
    );
    punch(c.generously - 0.07, 0.025);
    return "own-push";
  },

  // ── 9. The better question: the empty room at night, the mic's red light — the point the logo lands on ──
  // ── 9. The better question: a model and a "good luck", an app for every task. Then the agent: the model is one
  //       ingredient, it gets swapped, and the scaffolding under it (data, tools, governance) stays ──
  meal(stage, seg) {
    const c = R.scenes.meal.cues;
    exLight(stage, 540, 560, 760, seg, 26, 97);
    const rig = exRig(stage, seg, { rotationX: 8, rotationY: -8 }, { rotationX: 2, rotationY: 6 });
    // A. the ask: people waiting to be given AI
    const ask = div("rig3d", rig);
    const kick = div("ex-k", ask, "GIVING PEOPLE AI", "left:110px;top:150px");
    exIn(kick, seg.t0 + 0.1, { x: -30 }, 0.4);
    const ppl = [170, 355, 540, 725, 910].map((x, k) => {
      const p = exIcon(ask, "person", 120, x - 60, 800);
      exPop(p, c.people - 0.3 + k * 0.07, 0.4, 0.4);
      return p;
    });
    // B. a model and a "good luck" (the sticker sits beside the name, never on it)
    const model = div("ex-chip", ask, "MODEL", "left:418px;top:420px;font-size:44px;padding:22px 40px");
    tl.fromTo(
      model,
      { y: -420, rotation: -8, opacity: 0 },
      { y: 0, rotation: 0, opacity: 1, duration: 0.5, ease: "back.out(1.6)" },
      c.model - 0.35,
    );
    punch(c.model + 0.12, 0.02);
    const luck = div("ex-chip red", ask, "GOOD LUCK", "left:560px;top:572px;font-size:30px;color:#e8402c");
    tl.fromTo(
      luck,
      { scale: 2.4, rotation: -20, opacity: 0 },
      { scale: 1, rotation: 6, opacity: 1, duration: 0.25, ease: "power4.in" },
      c.good - 0.2,
    );
    punch(c.good + 0.05, 0.02);
    // C. a different app for every task, each from a different vendor (a different mark on every tile)
    tl.fromTo(
      [model, luck],
      { scale: 1, opacity: 1 },
      { scale: 0.3, opacity: 0, duration: 0.3, ease: "power2.in", ...IR },
      c.different - 0.3,
    );
    const marks = [
      '<circle cx="11" cy="11" r="9" fill="#fff"/>',
      '<path d="M11 2l9 17H2z" fill="#9b9da4"/>',
      '<rect x="3" y="3" width="16" height="16" rx="2" fill="none" stroke="#fff" stroke-width="3"/>',
      '<path d="M11 1l10 10-10 10L1 11z" fill="#6b6d74"/>',
      '<circle cx="11" cy="11" r="8" fill="none" stroke="#9b9da4" stroke-width="4"/>',
      '<rect x="2" y="6" width="18" height="10" rx="5" fill="#fff"/>',
      '<path d="M3 3h16v16z" fill="#fff"/>',
      '<path d="M11 2v18M2 11h18" stroke="#9b9da4" stroke-width="4"/>',
    ];
    const apps = [
      ["SLIDES AI", 110, 250, -4],
      ["NOTES AI", 420, 235, 3],
      ["EMAIL AI", 730, 265, -2],
      ["CRM AI", 140, 410, 2],
      ["SEARCH AI", 700, 420, -3],
      ["MEETING AI", 100, 575, -2],
      ["CODE AI", 430, 590, 4],
      ["HR AI", 760, 580, 2],
    ].map(([lab, x, y, r], k) => {
      const el = div(
        "ex-chip",
        ask,
        `<svg viewBox="0 0 22 22" width="22" height="22" style="vertical-align:-3px;margin-right:14px">${marks[k]}</svg>${lab}`,
        `left:${x}px;top:${y}px`,
      );
      tl.fromTo(
        el,
        { scale: 0.3, opacity: 0, rotation: 0 },
        { scale: 1, opacity: 1, rotation: r, duration: 0.35, ease: "back.out(2)" },
        c.different + k * 0.15,
      );
      return { el, x, y };
    });
    // D. AI is an ingredient: the pile blows away, one model is left
    apps.forEach(({ el, x, y }, k) => {
      const dx = (x + 110 - 540) * 1.6,
        dy = (y - 430) * 1.8 - 200;
      tl.fromTo(
        el,
        { x: 0, y: 0, opacity: 1 },
        { x: dx, y: dy, opacity: 0, duration: 0.45, ease: "power3.in", ...IR },
        c.ai - 0.2 + k * 0.02,
      );
    });
    tl.fromTo([kick, ...ppl], { opacity: 1 }, { opacity: 0, duration: 0.35, ...IR }, c.ai - 0.15);
    // E. agents are the meal: a panel forms around the model, with empty places for what goes under it
    const ag = div("rig3d", rig);
    const Pn = div("ex-p", ag, "", "left:190px;top:200px;width:700px;height:800px");
    div(
      "ex-k red",
      Pn,
      `<span style="display:inline-block;width:18px;height:18px;border-radius:50%;background:${P.accent};box-shadow:0 0 16px ${P.accent};margin-right:14px;vertical-align:-1px"></span>AGENT`,
      "left:34px;top:30px",
    );
    exIn(Pn, c.agents - 0.25, { scale: 0.86, y: 30 }, 0.5);
    exRing(ag, c.meal, 540, 600, 440, 0.8);
    punch(c.meal, 0.025);
    const LY = [
      ["DATA", 480, "data"],
      ["TOOLS", 610, "tools"],
      ["GOVERNANCE", 740, "governance"],
    ];
    LY.forEach(([lab, y, w], k) => {
      const gh = div(
        "",
        ag,
        "",
        `position:absolute;left:265px;top:${y}px;width:550px;height:96px;border-radius:5px;border:3px dashed ${P.line}`,
      );
      exPop(gh, c.agents + 0.15 + k * 0.1, 0.8, 0.35);
      const b = div(
        "ex-blk",
        ag,
        lab,
        `left:265px;top:${y}px;width:550px;height:96px;font-size:36px;border-color:${P.ink}`,
      );
      exIn(b, c[w] - 0.1, { x: -60 }, 0.4);
      tl.fromTo(b, { borderColor: P.ink }, { borderColor: P.line, duration: 0.6, ...IR }, c[w] + 0.5);
    });
    // F. models get swapped; the scaffolding stays: A goes, B comes, then on "stays" B goes and C comes, and nothing
    //    under the model moves
    const chip = (lab) =>
      div("ex-chip", ag, lab, "left:395px;top:305px;width:290px;text-align:center;font-size:40px;padding:20px 0");
    const [mA, mB, mC] = ["MODEL A", "MODEL B", "MODEL C"].map(chip);
    // the ingredient lands big in the middle, then drops into its place as the agent forms around it
    tl.fromTo(
      mA,
      { scale: 0.5, opacity: 0, y: 260 },
      { scale: 1.5, opacity: 1, y: 260, duration: 0.45, ease: "back.out(1.8)" },
      c.ai - 0.05,
    );
    tl.fromTo(
      mA,
      { scale: 1.5, y: 260 },
      { scale: 1, y: 0, duration: 0.55, ease: "power3.inOut", ...IR },
      c.agents - 0.35,
    );
    const out = (m, t) =>
      tl.fromTo(
        m,
        { x: 0, rotation: 0, opacity: 1 },
        { x: 640, rotation: 12, opacity: 0, duration: 0.4, ease: "power3.in", ...IR },
        t,
      );
    const inn = (m, t) =>
      tl.fromTo(
        m,
        { x: -640, rotation: -12, opacity: 0 },
        { x: 0, rotation: 0, opacity: 1, duration: 0.45, ease: "power3.out" },
        t,
      );
    out(mA, c.models - 0.05);
    inn(mB, c.swapped - 0.35);
    punch(c.swapped + 0.1, 0.015);
    out(mB, c.stays - 0.25);
    inn(mC, c.stays + 0.05);
    // the scaffolding: a red bracket down the left of the three places, and it's yours
    const Bk = svg("svg", { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" }, ag);
    const br = svg(
      "path",
      {
        d: "M250 488 H228 V828 H250",
        fill: "none",
        stroke: P.accent,
        "stroke-width": 6,
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
      },
      Bk,
    );
    exDraw(br, c.scaffolding - 0.05, 0.5);
    const yo = div("ex-k red", ag, "STAYS YOURS", "left:265px;top:870px");
    exIn(yo, c.yours - 0.15, { x: -30 }, 0.35);
    return "own-push";
  },
  room(stage, seg) {
    const c = R.scenes.room.cues,
      D = R.scenes.room,
      len = seg.t1 - seg.t0;
    const box = div("ex-clip", stage, "", "left:0;top:40px;width:1080px;height:1130px");
    const W0 = 1700,
      H0 = (W0 * 1664) / 2496,
      mx = D.mic[0] * W0,
      my = D.mic[1] * H0,
      left = 540 - mx,
      top = 520 - my;
    const push = div(
      "",
      box,
      "",
      `position:absolute;left:${left.toFixed(1)}px;top:${top.toFixed(1)}px;width:${W0}px;height:${H0.toFixed(1)}px;transform-origin:${mx.toFixed(1)}px ${my.toFixed(1)}px`,
    );
    div("", push, `<img src="${D.img}" style="width:100%;height:100%;display:block">`, "position:absolute;inset:0");
    tl.fromTo(push, { scale: 1.02 }, { scale: 1.42, duration: len + 0.6, ease: "sine.inOut" }, seg.t0 - 0.3);
    div(
      "",
      box,
      "",
      `position:absolute;left:0;right:0;bottom:0;height:420px;background:linear-gradient(180deg,rgba(17,17,20,0),${P.ground})`,
    );
    div(
      "",
      box,
      "",
      `position:absolute;left:0;right:0;top:0;height:160px;background:linear-gradient(0deg,rgba(17,17,20,0),${P.ground})`,
    );
    if (LAND) {
      // widescreen: the box's sides show (vertical fills the width), so they fade into the room too
      div(
        "",
        box,
        "",
        `position:absolute;left:0;top:0;bottom:0;width:240px;background:linear-gradient(90deg,${P.ground},rgba(17,17,20,0))`,
      );
      div(
        "",
        box,
        "",
        `position:absolute;right:0;top:0;bottom:0;width:240px;background:linear-gradient(270deg,${P.ground},rgba(17,17,20,0))`,
      );
    }
    // the mic's red light breathes; it is the point the next cut collapses into
    const led = div(
      "",
      push,
      "",
      `position:absolute;left:${(mx - 60).toFixed(1)}px;top:${(my - 60).toFixed(1)}px;width:120px;height:120px`,
    );
    const glow = div("ex-glow", led, "", "left:0;top:0;width:120px;height:120px");
    const dot = div(
      "",
      led,
      "",
      `position:absolute;left:52px;top:52px;width:16px;height:16px;border-radius:50%;background:${P.accent}`,
    );
    dot.setAttribute("data-anchor", "");
    ticks.push((t) => {
      if (t < seg.t0 - 0.5 || t > seg.t1 + 0.5) return;
      glow.style.opacity = (0.55 + 0.35 * Math.sin((t - seg.t0) * 2.4)).toFixed(3);
    });
    tl.fromTo(
      glow,
      { scale: 1 },
      { scale: 2.4, duration: 0.5, ease: "power2.out", yoyo: true, repeat: 1 },
      c.exist - 0.1,
    );
    exLight(stage, 540, 520, 420, seg, 18, 91);
    return "own-push";
  },
});

// four scenes open on a kicker near the top: on a vertical cut they ride 60 units lower
exRideLower(["paradox", "lights", "courier", "joe"], 60);
