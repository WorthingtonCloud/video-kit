// The reel runtime, part 4 of 7. build concatenates js/reel/*.js in name order into ONE closure (00 opens it, 60
// closes it), so a part is not a module on its own: it shares every const and helper defined in the parts before it.
  // ───────── scenes ─────────
  const SCENES = {
    chat(stage, seg) {
      const c = R.scenes.chat || {},
        cyc = c.cycles || [{ q: "Where did we leave off?", a: "I don't have any memory of past conversations." }];
      const rig = div("rig3d", stage, "", "transform-origin:540px 670px");
      const box = div(
        "chat",
        rig,
        `<div class="chat-h"><span class="hd">${c.header || "New session"}</span></div>
        <div class="chat-b"><div class="bub-q"></div><div class="bub-a"></div></div><div class="scan"></div>
        <div class="chat-in"><span class="caret"></span><span class="ph">${c.placeholder || "Ask anything"}</span><span class="send" data-anchor></span></div>`,
      );
      const q = $(".bub-q", box),
        a = $(".bub-a", box),
        hd = $(".hd", box),
        ph = $(".ph", box),
        caret = $(".caret", box),
        body = $(".chat-b", box),
        scan = $(".scan", box);
      // the camera drifts around the box for the whole opening (frame one already tilted: the preview looks alive)
      tl.fromTo(
        rig,
        { rotationY: -13, rotationX: 9, ...TP },
        { rotationY: 10, rotationX: 2, ...TP, duration: seg.t1 - seg.t0, ease: "sine.inOut" },
        seg.t0,
      );
      // each exchange a little shorter than the last; each new one starts by a red scan line wiping the last one away
      const wts = cyc.map((_, i) => Math.pow(0.86, i)),
        sum = wts.reduce((x, y) => x + y, 0),
        live = (seg.t1 - seg.t0) * 0.86;
      const starts = [0];
      cyc.forEach((_, i) => starts.push(starts[i] + (live * wts[i]) / sum));
      const WIPE = 0.3,
        JOLT = [14, -11, 7, -4, 2, 0];
      ticks.push((t) => {
        const lt0 = t - seg.t0;
        if (lt0 < -0.1 || t > seg.t1 + 0.1) return;
        let i = cyc.length;
        for (let k = 0; k < cyc.length; k++)
          if (lt0 < starts[k + 1]) {
            i = k;
            break;
          }
        const lt = lt0 - starts[i];
        if (i > 0 && lt < WIPE) {
          // erase: the old exchange is cut away under the scan line; the box jolts
          const pv = cyc[i - 1],
            p = easeInOut(lt / WIPE);
          q.textContent = pv.q;
          q.style.opacity = 1;
          a.textContent = pv.a;
          ph.style.opacity = 0;
          caret.style.opacity = 0;
          body.style.clipPath = `inset(${(p * 100).toFixed(1)}% 0 0 0)`;
          scan.style.opacity = 1;
          scan.style.top = 120 + p * 560 + "px";
          box.style.transform = `translateX(${JOLT[Math.min(Math.floor(lt * 30), JOLT.length - 1)]}px)`;
          hd.style.color = P.accent;
          return;
        }
        body.style.clipPath = "none";
        scan.style.opacity = 0;
        box.style.transform = "none";
        const off = i > 0 ? WIPE : 0,
          l2 = lt - off;
        if (i < cyc.length) {
          const cy = cyc[i],
            L = starts[i + 1] - starts[i] - off;
          const qn = Math.round(cy.q.length * clamp((l2 - 0.08) / 0.45)),
            an = Math.round(cy.a.length * clamp((l2 - 0.75) / (L * 0.42)));
          q.textContent = cy.q.slice(0, qn);
          q.style.opacity = qn ? 1 : 0;
          a.textContent = cy.a.slice(0, an);
          const f = clamp(1 - l2 / 0.25);
          hd.style.color = f > 0 ? `rgba(229,72,77,${0.45 + 0.55 * f})` : P.dim;
          ph.style.opacity = 0;
          caret.style.opacity = 0;
        } else {
          q.textContent = "";
          q.style.opacity = 0;
          a.textContent = "";
          ph.style.opacity = 1;
          hd.style.color = P.dim;
          caret.style.opacity = Math.floor(t * 2.4) % 2 ? 0 : 1;
        }
      });
    },

    hub(stage, seg, f) {
      const c = R.scenes.hub || {},
        C = { x: 540, y: 700 },
        step = c.step ?? 3,
        tstep = c.tstep ?? 0.5;
      const rings = (c.rings || ["TIER 1", "TIER 2", "TIER 3"]).slice(0, 3),
        nodes = (c.nodes || []).slice(0, 8);
      const toolsAt = c.tools_at ?? rings.length * step,
        NR = 342;
      const rig = div("rig3d", stage);
      const s = svg("svg", { width: 1080, height: 1400, viewBox: "0 0 1080 1400", style: "overflow:visible" }, rig),
        g = svg("g", {}, s);
      const gSpokes = svg("g", {}, g),
        gRings = svg("g", {}, g),
        gComets = svg("g", {}, g),
        gLabels = svg("g", {}, g),
        gNodes = svg("g", {}, g);
      const at = (n) => seg.t0 + n * B;
      // the camera: a tilted close-up on the core that pulls back and swings face-on as the tiers draw
      tl.fromTo(
        rig,
        { rotationX: 58, rotationZ: -26, scale: 1.85, ...TP },
        {
          rotationX: 0,
          rotationZ: 0,
          scale: 1,
          ...TP,
          duration: at(Math.min(toolsAt, rings.length * step)) - seg.t0,
          ease: "power2.inOut",
          ...IR,
        },
        seg.t0,
      );
      rings.forEach((label, k) => {
        const r = 132 + 64 * k,
          circ = 2 * Math.PI * r,
          t0 = at(k * step);
        const ring = svg(
          "circle",
          {
            cx: C.x,
            cy: C.y,
            r,
            fill: "none",
            stroke: P.line,
            "stroke-width": 3,
            "stroke-dasharray": circ,
            "stroke-dashoffset": circ,
            transform: `rotate(-90 ${C.x} ${C.y})`,
          },
          gRings,
        );
        // short labels sitting ON their ring: a long one notches the ring above it and the circles read tall
        const lab = svg(
          "text",
          {
            x: C.x,
            y: C.y - r + 7,
            "text-anchor": "middle",
            fill: P.dim,
            "font-weight": 700,
            "font-size": 19,
            "letter-spacing": 3,
            opacity: 0,
            "paint-order": "stroke",
            stroke: P.ground,
            "stroke-width": 12,
            class: "mono",
          },
          gLabels,
        );
        lab.textContent = label;
        tl.to(ring, { attr: { "stroke-dashoffset": 0 }, duration: 0.6, ease: "power2.inOut" }, t0);
        tl.fromTo(
          ring,
          { attr: { stroke: P.accent } },
          { attr: { stroke: P.line }, duration: 0.9, ease: "power1.in", ...IR },
          t0 + 0.3,
        );
        tl.fromTo(lab, { opacity: 0 }, { opacity: 1, duration: 0.3, ...IR }, t0 + 0.35);
        // a comet runs each ring once it exists: the memory is live, each tier at its own speed
        const arc = 70,
          comet = svg(
            "circle",
            {
              cx: C.x,
              cy: C.y,
              r,
              fill: "none",
              stroke: P.accent,
              "stroke-width": 6,
              "stroke-linecap": "round",
              "stroke-dasharray": `${arc} ${circ}`,
              opacity: 0,
            },
            gComets,
          );
        const sp = [52, -38, 27][k],
          tOn = t0 + 0.6;
        ticks.push((t) => {
          if (t < tOn || t > seg.t1 + 0.1) {
            comet.setAttribute("opacity", 0);
            return;
          }
          comet.setAttribute("opacity", 0.9 * clamp((t - tOn) / 0.3));
          comet.setAttribute("transform", `rotate(${-90 + sp * (t - t0)} ${C.x} ${C.y})`);
        });
      });
      // the tools fly in from off-screen along their spokes, trailing red, and land with a squash
      const rects = [];
      nodes.forEach((label, i) => {
        const ang = ((-67.5 + (i * 360) / Math.max(nodes.length, 1)) * Math.PI) / 180,
          ux = Math.cos(ang),
          uy = Math.sin(ang);
        const sx = C.x + 266 * ux,
          sy = C.y + 266 * uy,
          ex = C.x + (NR - 34) * ux,
          ey = C.y + (NR - 34) * uy;
        const len = Math.hypot(ex - sx, ey - sy);
        const sp = svg(
          "line",
          {
            x1: sx,
            y1: sy,
            x2: ex,
            y2: ey,
            stroke: P.line,
            "stroke-width": 3,
            "stroke-dasharray": len,
            "stroke-dashoffset": len,
          },
          gSpokes,
        );
        const trail = svg(
          "line",
          { stroke: P.accent, "stroke-width": 5, "stroke-linecap": "round", opacity: 0 },
          gNodes,
        );
        const fly = svg("g", { opacity: 0 }, gNodes),
          nd = svg("g", {}, fly),
          w = 26 + label.length * 15.5;
        const rect = svg(
          "rect",
          { x: -w / 2, y: -30, width: w, height: 60, rx: 30, fill: P.card, stroke: P.line, "stroke-width": 3 },
          nd,
        );
        svg(
          "text",
          { y: 10, "text-anchor": "middle", fill: P.ink, "font-weight": 600, "font-size": 27, class: "sans" },
          nd,
        ).textContent = label;
        rects.push(rect);
        const t0 = at(toolsAt + i * tstep),
          FL = 0.42,
          FAR = 1250;
        const fx0 = LAND && ux < -0.2 ? 0 : ux,
          fy0 = LAND && ux < -0.2 ? -1 : uy; // widescreen: never across the words
        ticks.push((t) => {
          const p = (t - t0) / FL;
          if (p < 0 || t > seg.t1 + 0.1) {
            fly.setAttribute("opacity", 0);
            trail.setAttribute("opacity", 0);
            return;
          }
          const e = easeOut(Math.min(p, 1)),
            k = (FAR - NR) * (1 - e),
            nx = C.x + NR * ux + k * fx0,
            ny = C.y + NR * uy + k * fy0,
            tr = 40 + (1 - e) * 460;
          fly.setAttribute("transform", `translate(${nx.toFixed(1)} ${ny.toFixed(1)})`);
          fly.setAttribute("opacity", clamp(p * 5));
          trail.setAttribute("x1", nx + 30 * fx0);
          trail.setAttribute("y1", ny + 30 * fy0);
          trail.setAttribute("x2", nx + tr * fx0);
          trail.setAttribute("y2", ny + tr * fy0);
          trail.setAttribute("opacity", p < 1 ? 0.9 : 0);
        });
        tl.fromTo(
          nd,
          { scale: 1.3, svgOrigin: "0 0" },
          { scale: 1, svgOrigin: "0 0", duration: 0.45, ease: "elastic.out(1.1,0.45)", ...IR },
          t0 + FL,
        );
        tl.fromTo(rect, { attr: { stroke: P.accent } }, { attr: { stroke: P.line }, duration: 0.6, ...IR }, t0 + FL);
        tl.to(sp, { attr: { "stroke-dashoffset": 0 }, duration: 0.25, ease: "power2.out" }, t0 + FL - 0.05);
      });
      // live traffic: once a tool is wired in, red streaks run from it through all three rings into the agent and
      // back out, ping-pong, forever. Drawn over the rings and under the core, so they vanish into it.
      const tr = svg("g", {}, g),
        R0 = 76,
        R1 = NR - 34,
        TAIL = 120,
        CYC = 1.5;
      nodes.forEach((_, i) => {
        const ang = ((-67.5 + (i * 360) / Math.max(nodes.length, 1)) * Math.PI) / 180,
          ux = Math.cos(ang),
          uy = Math.sin(ang);
        const start = at(toolsAt + i * tstep) + 0.6;
        [0, 0.5].forEach((off) => {
          // two per spoke, half a cycle apart: one heading in while the other heads out
          const tail = svg("line", { stroke: P.accent, "stroke-width": 5, "stroke-linecap": "round", opacity: 0 }, tr);
          const head = svg("circle", { r: 8, fill: P.accent, opacity: 0 }, tr);
          ticks.push((t) => {
            if (t < start || t < seg.t0 || t > seg.t1 + 0.1) {
              tail.setAttribute("opacity", 0);
              head.setAttribute("opacity", 0);
              return;
            }
            const ph = ((t - start) / CYC + off) % 1,
              inbound = ph < 0.5,
              q = easeInOut(inbound ? 1 - 2 * ph : 2 * ph - 1);
            const fade = clamp((t - start) / 0.25),
              rh = R0 + q * (R1 - R0),
              rt = clamp(rh + (inbound ? TAIL : -TAIL), R0, R1);
            head.setAttribute("cx", C.x + rh * ux);
            head.setAttribute("cy", C.y + rh * uy);
            head.setAttribute("opacity", fade);
            tail.setAttribute("x1", C.x + rh * ux);
            tail.setAttribute("y1", C.y + rh * uy);
            tail.setAttribute("x2", C.x + rt * ux);
            tail.setAttribute("y2", C.y + rt * uy);
            tail.setAttribute("opacity", 0.8 * fade);
          });
        });
      });
      const core = svg("g", {}, svg("g", { transform: `translate(${C.x} ${C.y})` }, g));
      svg("circle", { r: 70, fill: P.card, stroke: P.accent, "stroke-width": 5, "data-anchor": "" }, core);
      svg(
        "text",
        {
          y: 9,
          "text-anchor": "middle",
          fill: P.ink,
          "font-weight": 700,
          "font-size": 25,
          "letter-spacing": 3,
          class: "mono",
        },
        core,
      ).textContent = c.center || "AGENT";
      tl.fromTo(
        core,
        { scale: 0, svgOrigin: "0 0" },
        { scale: 1, svgOrigin: "0 0", duration: 0.5, ease: "back.out(2)", ...IR },
        seg.t0,
      );
      // "everything": the moment the last tool lands, every tool flashes, the core kicks, the camera punches
      const tAll = at(toolsAt + nodes.length * tstep);
      if (nodes.length && tAll < seg.t1 - 0.3) {
        // only if the last tool lands inside the scene (else the ring fires over the next one)
        tl.fromTo(
          rects,
          { attr: { stroke: P.accent } },
          { attr: { stroke: P.line }, duration: 1.0, ease: "power1.in", stagger: 0.02, ...IR },
          tAll,
        );
        tl.fromTo(
          core,
          { scale: 1.22, svgOrigin: "0 0" },
          { scale: 1, svgOrigin: "0 0", duration: 0.6, ease: "elastic.out(1,0.45)", ...IR },
          tAll,
        );
        const cs = toScreen(f, C.x, C.y);
        shock(tAll, cs.x, cs.y, 520, 0.8, 5);
        punch(tAll, 0.03);
      }
      tl.fromTo(
        g,
        { scale: 1, svgOrigin: `${C.x} ${C.y}` },
        { scale: 1.07, svgOrigin: `${C.x} ${C.y}`, duration: seg.t1 - seg.t0, ease: "sine.inOut", ...IR },
        seg.t0,
      );
      return "own-push";
    },

    sources(stage, seg) {
      const c = R.scenes.sources || {},
        cards = (c.cards || []).slice(0, 6);
      const FX = 120,
        FY = 260,
        CW = 262,
        GAP = 27;
      const rig = div("rig3d", stage);
      // a slow orbit around the whole board
      tl.fromTo(
        rig,
        { rotationY: -14, rotationX: 7, ...TP },
        { rotationY: 10, rotationX: -3, ...TP, duration: seg.t1 - seg.t0, ease: "sine.inOut", ...IR },
        seg.t0,
      );
      // footnote markers ordered by column, so no link ever crosses another
      const MARKS = [
        [512, 200],
        [672, 150],
        [752, 100],
        [552, 200],
        [712, 150],
        [790, 100],
      ];
      const claim = div(
        "claim",
        rig,
        `<div class="k mono">${c.heading || "CLAIM"}</div>` +
          [
            [700, 90],
            [620, 140],
            [460, 190],
          ]
            .map(([w, y]) => `<div class="bar" style="width:${w}px;top:${y}px"></div>`)
            .join(""),
      );
      tl.fromTo(
        claim,
        { y: -720, rotation: -7, opacity: 0 },
        { y: 0, rotation: 0, opacity: 1, duration: 0.55, ease: "back.out(1.3)", ...IR },
        seg.t0 - 0.05,
      );
      const links = svg(
        "svg",
        { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" },
        rig,
      ); // over the card
      const marks = svg(
        "svg",
        { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" },
        rig,
      );
      // never from below: a card crossing the title area would pass behind the words
      const FROM = LAND
        ? [
            { x: -250, y: -1150, r: -22 },
            { x: 0, y: -1250, r: 14 },
            { x: 1000, y: -150, r: 26 },
            { x: -150, y: 1100, r: -18 },
            { x: 150, y: 1150, r: -12 },
            { x: 1000, y: 350, r: 20 },
          ]
        : [
            { x: -950, y: -150, r: -28 },
            { x: 0, y: -1150, r: 14 },
            { x: 950, y: -150, r: 26 },
            { x: -1000, y: 60, r: -18 },
            { x: 120, y: -1300, r: -12 },
            { x: 1000, y: 60, r: 20 },
          ];
      const paths = [];
      let tLast = seg.t0;
      cards.forEach(({ k, t }, i) => {
        const col = i % 3,
          row = Math.floor(i / 3),
          x = FX + col * (CW + GAP),
          y = 640 + row * 236;
        const card = div(
          "src",
          rig,
          `<div class="k mono">${k}</div><svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="${P.ink}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">${GLYPH[k] || GLYPH.PAPER}</svg><div class="t">${t}</div>`,
          `left:${x}px;top:${y}px;opacity:0`,
        );
        const [mx, my] = MARKS[i],
          x0 = FX + mx,
          y0 = FY + my,
          x1 = x + CW / 2;
        const p = svg(
          "path",
          {
            d: `M${x0} ${y0} C ${x0} ${y0 + 160}, ${x1} ${y - 160}, ${x1} ${y}`,
            fill: "none",
            stroke: P.accent,
            "stroke-width": 3,
          },
          links,
        );
        const len = p.getTotalLength();
        p.setAttribute("stroke-dasharray", len);
        p.setAttribute("stroke-dashoffset", len);
        const mk = svg("circle", { cx: x0, cy: y0, r: 9, fill: P.accent, opacity: 0 }, marks);
        const t0 = seg.t0 + 0.45 + (i * B) / 2,
          fr = FROM[i];
        paths.push({ p, len, mk, x0, y0, tOn: t0 + 0.8 });
        // each source arrives from its own side of the frame
        tl.fromTo(
          card,
          { x: fr.x, y: fr.y, rotation: fr.r, opacity: 0, scale: 0.9 },
          { x: 0, y: 0, rotation: 0, opacity: 1, scale: 1, duration: 0.55, ease: "power3.out", ...IR },
          t0,
        );
        tl.fromTo(
          mk,
          { scale: 0, opacity: 1, svgOrigin: `${x0} ${y0}` },
          { scale: 1, opacity: 1, svgOrigin: `${x0} ${y0}`, duration: 0.25, ease: "back.out(3)", ...IR },
          t0 + 0.45,
        );
        tl.to(p, { attr: { "stroke-dashoffset": 0 }, duration: 0.35, ease: "power2.inOut" }, t0 + 0.45);
        tLast = t0 + 0.8;
      });
      // data flows: once a link is drawn, packets run up it from the source into the claim, one after another, until
      // the scene ends; each arrival kicks the footnote mark. Big enough to read on a phone: a head, a glow and a tail
      const PER = 1.05,
        TL = 120;
      paths.forEach(({ p, len, mk, tOn }, i) => {
        const packets = [0, 0.5].map(() => ({
          glow: svg("circle", { r: 24, fill: P.accent, opacity: 0 }, marks),
          tail: svg(
            "polyline",
            {
              fill: "none",
              stroke: P.accent,
              "stroke-width": 7,
              "stroke-linecap": "round",
              "stroke-linejoin": "round",
              opacity: 0,
            },
            marks,
          ),
          head: svg("circle", { r: 12, fill: P.accent, opacity: 0 }, marks),
        }));
        ticks.push((t) => {
          let since = 9;
          packets.forEach(({ glow, tail, head }, j) => {
            const k = (t - tOn) / PER - j * 0.5 - (i % 3) * 0.12;
            if (k < 0 || t > seg.t1 + 0.1) {
              glow.setAttribute("opacity", 0);
              tail.setAttribute("opacity", 0);
              head.setAttribute("opacity", 0);
              return;
            }
            if (k >= 1) since = Math.min(since, (k % 1) * PER);
            const q = k % 1,
              at = len * (1 - easeInOut(q)),
              fade = Math.min(1, q / 0.08, (1 - q) / 0.06);
            const h = p.getPointAtLength(at);
            let pts = "";
            for (let m = 0; m <= 6; m++) {
              const pt = p.getPointAtLength(Math.min(len, at + (TL * m) / 6));
              pts += `${pt.x.toFixed(1)},${pt.y.toFixed(1)} `;
            }
            head.setAttribute("cx", h.x);
            head.setAttribute("cy", h.y);
            head.setAttribute("opacity", fade);
            glow.setAttribute("cx", h.x);
            glow.setAttribute("cy", h.y);
            glow.setAttribute("opacity", 0.25 * fade);
            tail.setAttribute("points", pts);
            tail.setAttribute("opacity", 0.75 * fade);
          });
          mk.setAttribute("r", 9 + 7 * clamp(1 - since / 0.3));
        });
      });
      const tv = paths.length ? paths[paths.length - 1].tOn + PER : seg.t0 + 2;
      tl.fromTo(claim, { borderColor: P.accent }, { borderColor: P.line, duration: 0.8, ease: "power1.in", ...IR }, tv);
    },

    endcard(stage, seg, f) {
      const c = R.scenes.endcard || {},
        t0 = seg.t0,
        land = t0 + 2 * B; // the point lands on the beat
      const tile = div("tileicon", stage);
      if (c.mark) {
        // a drawn mark: the stroke draws, then the accent point drops and lands with a squash (the motif, home)
        const m = c.mark,
          s = svg("svg", { width: 240, height: 240, viewBox: m.viewBox || "-3 -3 30 30" }, tile);
        const path = svg(
          "path",
          { d: m.path, fill: "none", stroke: P.ink, "stroke-width": m.stroke || 2.2, "stroke-linecap": "square" },
          s,
        );
        const len = path.getTotalLength();
        path.setAttribute("stroke-dasharray", len);
        path.setAttribute("stroke-dashoffset", len);
        tl.to(path, { attr: { "stroke-dashoffset": 0 }, duration: 0.6, ease: "power2.inOut" }, t0 + 0.15);
        if (m.point) {
          const [px, py, pw, ph] = m.point,
            pt = svg("rect", { x: px, y: py, width: pw, height: ph, fill: P.accent, opacity: 0 }, s);
          tl.fromTo(
            pt,
            { attr: { y: py - 26 }, opacity: 0 },
            { attr: { y: py }, opacity: 1, duration: 0.3, ease: "power3.in", ...IR },
            land - 0.3,
          );
          tl.fromTo(
            pt,
            { scaleY: 0.5, scaleX: 1.4, svgOrigin: `${px + pw / 2} ${py + ph}` },
            {
              scaleY: 1,
              scaleX: 1,
              svgOrigin: `${px + pw / 2} ${py + ph}`,
              duration: 0.45,
              ease: "elastic.out(1.2,0.45)",
              ...IR,
            },
            land,
          );
          const vb = (m.viewBox || "-3 -3 30 30").split(/\s+/).map(Number),
            k = 240 / vb[2];
          const sc = toScreen(f, 420 + (px + pw / 2 - vb[0]) * k, 455 + (py + ph / 2 - vb[1]) * k);
          shock(land, sc.x, sc.y, 300, 0.8, 5);
          punch(land, 0.03);
        }
      } else if (c.logo) {
        div("logo", tile, `<img src="${R.media.logo}" alt="">`);
      }
      tl.fromTo(
        tile,
        { scale: 0.7, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.32, ease: "back.out(1.8)", ...IR },
        t0 - 0.05,
      );
      const word = div(
        "word",
        stage,
        [...(c.wordmark || "")].map((ch) => `<span class="ch">${ch === " " ? "&nbsp;" : ch}</span>`).join(""),
      );
      const url = div("url", stage, c.url || "");
      if (c.word_b != null) {
        // on the beat: the name slams in so its letters land ON a beat, the address on a later one
        const tw = land + c.word_b * B,
          tu = land + (c.url_b ?? c.word_b + 2) * B,
          chs = $$(".ch", word),
          st = 0.025;
        tl.set(word, { opacity: 1 }, tw - 0.3);
        tl.fromTo(
          chs,
          { yPercent: 110, rotation: 6 },
          { yPercent: 0, rotation: 0, duration: 0.3, ease: "expo.out", stagger: st },
          tw - 0.3 - st * (chs.length - 1) + 0.1,
        );
        punch(tw, 0.03);
        tl.fromTo(url, { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "power3.out" }, tu - 0.18);
        tl.fromTo(
          tile,
          { scale: 1 },
          { scale: 1.06, duration: 0.12, yoyo: true, repeat: 1, ease: "power2.out", ...IR },
          tu,
        );
        punch(tu, 0.025);
      } else {
        const late = c.mark ? land - t0 + 0.1 : 0.6; // the name arrives only after the mark has landed
        tl.set(word, { opacity: 1 }, t0 + late);
        tl.fromTo(
          $$(".ch", word),
          { yPercent: 110, rotation: 6 },
          { yPercent: 0, rotation: 0, duration: 0.6, ease: "expo.out", stagger: 0.045 },
          t0 + late,
        );
        tl.fromTo(
          url,
          { y: 20, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.5, ease: "power3.out", ...IR },
          t0 + late + 0.4,
        );
      }
    },
  };
  /*__EXTRA_SCENES__*/
  const GLYPH = {
    PAPER: '<rect x="18" y="10" width="28" height="40" rx="3"/><path d="M25 22h14M25 30h14M25 38h9"/>',
    CODE: '<path d="M24 18L12 32l12 14M40 18l12 14-12 14"/>',
    FILING: '<rect x="10" y="16" width="44" height="32" rx="3"/><path d="M10 16l22 18 22-18"/>',
    DATA: '<ellipse cx="32" cy="16" rx="18" ry="7"/><path d="M14 16v28c0 4 8 7 18 7s18-3 18-7V16M14 30c0 4 8 7 18 7s18-3 18-7"/>',
    VIDEO: '<rect x="10" y="14" width="44" height="32" rx="8"/><path d="M28 23l10 7-10 7z"/>',
    METHOD:
      '<circle cx="18" cy="18" r="5"/><circle cx="46" cy="46" r="5"/><path d="M23 18h14a8 8 0 0 1 0 16H27a8 8 0 0 0 0 16h14"/>',
  };
  GLYPH.DATASET = GLYPH.DATA;
  GLYPH.TRANSCRIPT = GLYPH.VIDEO;

