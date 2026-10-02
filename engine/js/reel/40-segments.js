// The reel runtime, part 5 of 7. build concatenates js/reel/*.js in name order into ONE closure (00 opens it, 60
// closes it), so a part is not a module on its own: it shares every const and helper defined in the parts before it.
  // ───────── build every segment ─────────
  const root = $("#root"),
    titlesBox = $("#titles");
  const segs = R.segments.map((seg, i) => ({ ...seg, i, el: $(`#seg-${i}`) }));
  const ANCH = []; // each segment's anchor point (its red point), measured before any tween has moved anything
  for (const seg of segs) {
    const src = seg.source,
      cam = $(".cam", seg.el),
      len = seg.t1 - seg.t0;
    let ownPush = false,
      push = seg.push ?? 0.04;
    if (src.scene) {
      const center = src.scene === "endcard",
        f = fitStage(center);
      const stage = div("stage", cam, "", `transform:translate(${f.x}px,${f.y}px) scale(${f.s})`);
      if (!SCENES[src.scene]) throw new Error(`unknown scene "${src.scene}"`);
      ownPush = SCENES[src.scene](stage, seg, f) === "own-push";
    } else if (src.card) {
      const t = R.titles[src.card],
        wrap = div("cardwrap", cam),
        card = div("card", wrap, lines(t.text, src.out === "shatter"));
      card.dataset.title = src.card;
      if (t.size) card.style.fontSize = parseFloat(getComputedStyle(card).fontSize) * t.size + "px";
      const ats = src.at || [],
        style = src.style || "blur",
        hits = new Set();
      $$(".line", card).forEach((ln, k) => {
        const b = ats[k] ?? (ats.length ? ats[ats.length - 1] : 0),
          t0 = seg.t0 + b * B + (ats.length ? 0 : k * 0.1);
        if (seg.i === 0 && t0 === 0) return; // frame one is the preview: the hook is already there
        // no IR here: a later line must be hidden from load until its own beat, or it shows up with the first one
        if (style === "flap") {
          // each line flips down into place like a departures board
          tl.fromTo(
            ln,
            { rotationX: -105, opacity: 0, transformOrigin: "50% 0%", transformPerspective: 900 },
            { rotationX: 0, opacity: 1, transformPerspective: 900, duration: 0.6, ease: "back.out(1.7)" },
            t0,
          );
        } else if (style === "slam") {
          // each line lands from over the camera's shoulder
          tl.fromTo(
            ln,
            { scale: 2.6, opacity: 0, filter: "blur(22px)" },
            { scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.4, ease: "expo.out" },
            t0,
          );
        } else {
          tl.fromTo(
            ln,
            { scale: 1.4, opacity: 0, filter: "blur(12px)" },
            { scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.36, ease: "expo.out" },
            t0,
          );
        }
        if (!hits.has(b)) {
          hits.add(b);
          if (src.rings) shock(t0 + 0.05, W / 2, H / 2, 300 + hits.size * 150, 0.9, 4); // one ring per tier
          if (style === "slam") punch(t0, 0.045, hits.size % 2 ? -0.8 : 0.8);
          else if (src.rings) punch(t0, 0.02);
        }
      });
      $$(".apart", card).forEach((ap) => {
        const ch = $$(".ch", ap),
          mid = (ch.length - 1) / 2,
          t0 = seg.t0 + (ats[ats.length - 1] || 0) * B + 0.4;
        tl.fromTo(
          ch,
          { x: 0 },
          { x: (k) => (k - mid) * 16, duration: Math.max(0.5, seg.t1 - t0), ease: "sine.inOut", ...IR },
          t0,
        );
      });
      if (t.em) emphasize(t, card, seg.t0);
      if (src.out === "shatter") {
        // "Pull it apart": at the cut, every letter flies apart toward the camera
        const rnd = mulberry32(31),
          TS = seg.t1 - 0.08;
        $$(".ch", card).forEach((ch) => {
          const cx = ch.offsetLeft + ch.offsetWidth / 2 - W / 2,
            cy = ch.offsetTop + ch.offsetHeight / 2 - H / 2;
          const n = Math.hypot(cx, cy) || 1,
            dist = 700 + rnd() * 900,
            dx = (cx / n + (rnd() - 0.5) * 0.8) * dist,
            dy = (cy / n + (rnd() - 0.5) * 0.8) * dist;
          tl.fromTo(
            ch,
            { xPercent: 0, yPercent: 0, rotation: 0, scale: 1 },
            {
              xPercent: (dx / ch.offsetWidth) * 100,
              yPercent: (dy / ch.offsetHeight) * 100,
              rotation: (rnd() - 0.5) * 420,
              scale: 1.8 + rnd() * 1.6,
              duration: 0.8,
              ease: "power3.out",
              ...IR,
            },
            TS,
          );
          tl.fromTo(
            ch,
            { opacity: 1, filter: "blur(0px)" },
            { opacity: 0, filter: "blur(6px)", duration: 0.45, ease: "power1.in", ...IR },
            TS + 0.2,
          );
        });
      }
    } else if (src.grid) {
      // the collage: frames of this very reel assemble into a wall in 3D while the camera sweeps over it
      const files = R.media.tiles[seg.i],
        n = files.length,
        cols = src.cols || 3,
        rows = Math.ceil(n / cols);
      const tw = LAND ? 330 : 300,
        th = Math.round((tw * H) / W),
        gap = 26,
        WW = cols * tw + (cols - 1) * gap,
        WH = rows * th + (rows - 1) * gap;
      cam.style.perspective = "1300px";
      const wall = div("wall", cam, "", `left:${(W - WW) / 2}px;top:${(H - WH) / 2}px;width:${WW}px;height:${WH}px`);
      const rnd = mulberry32(77),
        T = seg.t0;
      const scan0 = T + 1.45,
        scanStep = Math.min(0.07, (len - 1.6) / n);
      files.forEach((file, k) => {
        const col = k % cols,
          row = Math.floor(k / cols),
          left = col * (tw + gap),
          top = row * (th + gap);
        const tile = div(
          "tile",
          wall,
          `<img src="${file}" alt="">`,
          `left:${left}px;top:${top}px;width:${tw}px;height:${th}px`,
        );
        tile.dataset.dx = WW / 2 - (left + tw / 2);
        tile.dataset.dy = WH / 2 - (top + th / 2);
        const ang = rnd() * Math.PI * 2,
          dist = 520 + rnd() * 560,
          t0 = T - 0.06 + k * 0.07;
        // from every direction, from above the wall, spinning; they land in reading order
        tl.fromTo(
          tile,
          {
            x: Math.cos(ang) * dist,
            y: Math.sin(ang) * dist,
            z: 260 + rnd() * 360,
            rotationX: (rnd() - 0.5) * 140,
            rotationY: (rnd() - 0.5) * 140,
            rotation: (rnd() - 0.5) * 120,
            opacity: 0,
          },
          {
            x: 0,
            y: 0,
            z: 0,
            rotationX: 0,
            rotationY: 0,
            rotation: 0,
            opacity: 1,
            duration: 0.62,
            ease: "power3.out",
            ...IR,
          },
          t0,
        );
        // a red playhead runs the wall in order, one tile after another
        tl.fromTo(
          tile,
          { borderColor: P.accent, filter: "brightness(1.5)" },
          { borderColor: P.line, filter: "brightness(1)", duration: 0.5, ease: "power1.in", ...IR },
          scan0 + k * scanStep,
        );
      });
      // the camera: skimming low over the wall as it assembles, then rising to face it
      const settle = T + Math.min(2.1, len - 0.3);
      const S1 = LAND ? 1.0 : 0.8,
        S2 = LAND ? 0.93 : 0.72; // the wall at rest: widescreen has room for it bigger
      tl.fromTo(
        wall,
        { rotationX: 58, rotationZ: -24, scale: 1.5, y: H * 0.16 },
        { rotationX: 12, rotationZ: -4, scale: S1, y: 0, duration: settle - T, ease: "power2.inOut", ...IR },
        T,
      );
      tl.fromTo(
        wall,
        { rotationX: 12, rotationZ: -4, rotationY: 0, scale: S1 },
        { rotationX: 3, rotationZ: 0, rotationY: -12, scale: S2, duration: 3.2, ease: "sine.inOut", ...IR },
        settle,
      );
      ownPush = true;
    }
    // footage (shot / clip / still) was written into .cam by build.mjs: its media tags must be static HTML
    const panel = $(".panel", cam);
    if (panel) {
      // a real page floats like a device: a slow 3D sway, lit by one light that stays put in the room
      const dir = seg.i % 2 ? 1 : -1,
        mover = $(".mover", seg.el);
      if (LAND)
        mover.style.transformOrigin = `${panel.offsetLeft + panel.offsetWidth / 2}px ${panel.offsetTop + panel.offsetHeight / 2}px`;
      // held at its starting angle from load: the page is on screen during the hand-off, before its own slot starts
      // reel.json → shots.<id>.float: {"y": [from, to], "x": [from, to], "glare": 1} turns the sway up for a hero
      // shot (a product's own interface): a wider turn, so the glare crosses the whole glass
      const fl = (src.shot && R.shots?.[src.shot]?.float) || {},
        fy = fl.y || [7, -6],
        fx2 = fl.x || [4, -2];
      tw3(
        panel,
        { rotationY: fy[0] * dir, rotationX: fx2[0], transformPerspective: 2200 },
        { rotationY: fy[1] * dir, rotationX: fx2[1], transformPerspective: 2200, duration: len, ease: "sine.inOut" },
        seg.t0,
      );
      const sh = div("sheen", panel),
        pw = panel.offsetWidth;
      if (fl.glare) {
        const g = Math.min(2.5, fl.glare),
          a = (v) => `rgba(255,255,255,${(v * g).toFixed(3)})`;
        // glass: a soft wide band with a bright core, and a thin second glint beside it, screened onto the page
        sh.style.background = `linear-gradient(100deg,transparent 0%,${a(0.03)} 24%,${a(0.09)} 40%,${a(0.16)} 47%,${a(0.09)} 54%,${a(0.02)} 62%,${a(0.1)} 66%,${a(0.02)} 70%,transparent 82%)`;
        sh.style.mixBlendMode = "screen";
      }
      // the glare sits where that light reflects off the glass: turn the page right and it slides left, tip it back
      // and it slides a little right. The sway, the hand-offs and the flips all move it, so it never jumps
      ticks.push((t) => {
        if (t < seg.t0 - 0.6 || t > seg.t1 + 0.8) return;
        const ry = tilt(panel, "rotationY", t) + tilt(mover, "rotationY", t),
          rx = tilt(panel, "rotationX", t) + tilt(mover, "rotationX", t);
        const u = 0.4 - ry / 18 + rx / 40; // the band's center across the page, 0..1 (off either edge = out of sight)
        sh.style.transform = `translateX(${((u - 0.3) * pw).toFixed(1)}px)`;
      });
    }
    if (seg.fx?.dust) {
      // dust hanging in the light: two depths, drifting up, each mote on its own seeded path
      const d = seg.fx.dust,
        n = d.n || 40,
        rnd = mulberry32(4242),
        layer = div("dust", cam);
      const motes = [...Array(n)].map(() => {
        const z = rnd(),
          m = div("mote", layer),
          sz = 1.5 + z * 3.2;
        m.style.cssText = `width:${sz.toFixed(1)}px;height:${sz.toFixed(1)}px;filter:blur(${((1 - z) * 2.2).toFixed(1)}px)`;
        return { m, z, x: rnd(), y: rnd(), ph: rnd() * 6.283, sp: 0.35 + rnd() * 0.65 };
      });
      ticks.push((t) => {
        if (t < seg.t0 - 0.6 || t > seg.t1 + 0.1) return;
        const lt = t - seg.t0;
        motes.forEach((o) => {
          const yy = (((o.y - lt * 0.022 * o.sp * (0.5 + o.z)) % 1) + 1) % 1,
            xx = o.x + Math.sin(lt * 0.7 * o.sp + o.ph) * 0.03;
          const X = (d.x[0] + xx * (d.x[1] - d.x[0])) * W,
            Y = (d.y[0] + yy * (d.y[1] - d.y[0])) * H;
          const edge = Math.min(1, yy / 0.15, (1 - yy) / 0.15);
          o.m.style.transform = `translate(${X.toFixed(1)}px,${Y.toFixed(1)}px)`;
          o.m.style.opacity = (
            (0.1 + 0.35 * o.z) *
            (0.65 + 0.35 * Math.sin(lt * 1.9 * o.sp + o.ph * 2)) *
            edge
          ).toFixed(3);
        });
      });
    }
    // widescreen: the picture sits centered and slides right only while a title is up on the left (same video, just
    // wider). Parked on the right with nothing to read beside it, half the frame sat empty (video-kit reel, Oct 2, 2026)
    if (LAND && R.scene_lib !== "explainer" && ((src.scene && src.scene !== "endcard") || panel)) {
      const words = seg.titles
          .filter((tt) => ["lower", "stat", undefined].includes(R.titles[tt.id]?.kind))
          .sort((a, b) => a.t0 - b.t0),
        cx = panel ? panel.offsetLeft + panel.offsetWidth / 2 : W * 0.72,
        dx = W / 2 - cx,
        IN = 0.45,
        MOVE = 0.55;
      let at = words.length && words[0].t0 - IN <= seg.t0 ? 0 : dx;
      gsap.set(cam, { x: at });
      words.forEach((tt, k) => {
        if (at !== 0) tl.fromTo(cam, { x: at }, { x: 0, duration: MOVE, ease: "power3.inOut", ...IR }, tt.t0 - IN);
        at = 0;
        const next = k + 1 < words.length ? words[k + 1].t0 - IN : seg.t1;
        if (next - (tt.t1 + 0.05) >= 0.9) {
          tl.fromTo(cam, { x: 0 }, { x: dx, duration: MOVE + 0.1, ease: "power3.inOut", ...IR }, tt.t1 + 0.05);
          at = dx;
        }
      });
    }
    if (!ownPush && push)
      tl.fromTo(cam, { scale: 1 }, { scale: 1 + push, duration: len, ease: "sine.inOut", ...IR }, seg.t0);
    {
      // the anchor as it sits at load (scene rigs haven't moved yet; the red point is at rest)
      const a = $("[data-anchor]", seg.el),
        r = a && a.getBoundingClientRect();
      ANCH[seg.i] = r ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : { x: W / 2, y: H / 2 };
    }

    // titles over this segment
    for (const tt of seg.titles) {
      const t = R.titles[tt.id];
      if (!t) throw new Error(`title "${tt.id}" not in reel.json → titles`);
      const el = div(t.kind === "stat" ? "stat" : "lower", titlesBox);
      el.dataset.title = tt.id;
      if (t.size) el.style.fontSize = parseFloat(getComputedStyle(el).fontSize) * t.size + "px"; // one long line: shrink just this title
      if (t.kind === "stat") el.innerHTML = `<div class="num">${t.text}</div><div class="sub">${t.sub || ""}</div>`;
      else el.innerHTML = `<span class="rule"></span>${lines(t.text)}`;
      const t0 = tt.t0 + (seg.in === "fade" && tt.t0 === seg.t0 ? 0.3 : 0) + (t.spark ? 0.3 : 0);
      const ws = $$(".w", el),
        lns = $$(".line", el),
        num = $(".num", el),
        sub = $(".sub", el),
        rule = $(".rule", el);
      tl.set(el, { opacity: 1 }, t0);
      if (t0 > 0) {
        if (t.kind === "stat") {
          if (t.spark) {
            // the number is fired out of the diagram: a spark from the core lands where the number slams in
            const a = ANCH[seg.i] || { x: W / 2, y: H * 0.35 },
              r = num.getBoundingClientRect();
            spark(t0 - 0.3, { x: a.x, y: a.y + 40 }, { x: r.left + r.width * 0.3, y: r.top + r.height * 0.5 }, 0.3);
          }
          tl.fromTo(
            num,
            { scale: 1.6, opacity: 0, filter: "blur(16px)", transformOrigin: "0% 60%" },
            { scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.5, ease: "expo.out" },
            t0,
          );
          tl.fromTo(sub, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.45, ease: "power3.out" }, t0 + 0.15);
          const n = +String(t.text).replace(/,/g, "");
          if (Number.isFinite(n))
            ticks.push((tt2) => {
              if (tt2 >= t0 - 0.2 && tt2 <= tt.t1 + 0.2)
                num.textContent = Math.round(n * easeOut((tt2 - t0 - 0.05) / 0.75)).toLocaleString("en-US");
            });
        } else {
          // words rise into place through their own line, one at a time
          tl.fromTo(rule, { scaleX: 0 }, { scaleX: 1, duration: 0.35, ease: "power3.out" }, t0);
          tl.set(lns, { clipPath: MASK }, t0);
          tl.fromTo(
            ws,
            { yPercent: 125, rotation: 7, opacity: 0 },
            {
              yPercent: 0,
              rotation: 0,
              opacity: 1,
              duration: 0.6,
              ease: "expo.out",
              stagger: 0.07,
              transformOrigin: "0% 100%",
            },
            t0,
          );
          tl.set(lns, { clipPath: "none" }, t0 + 0.7 + 0.07 * ws.length);
        }
      }
      const made = emphasize(t, el, tt.t0);
      if (tt.t1 < END - 0.01) {
        // out: words drop back out through the top of their line
        if (t.kind === "stat") {
          tl.to(
            [num, sub],
            { yPercent: -35, opacity: 0, filter: "blur(8px)", duration: 0.22, ease: "power2.in", stagger: 0.04 },
            tt.t1 - 0.26,
          );
        } else {
          const te = tt.t1 - (0.24 + 0.02 * ws.length);
          tl.set(lns, { clipPath: MASK }, te);
          tl.to(ws, { yPercent: -125, duration: 0.24, ease: "power2.in", stagger: 0.02 }, te);
          tl.to(rule, { scaleX: 0, duration: 0.2, ease: "power2.in" }, te);
          if (made.length) tl.to(made, { opacity: 0, duration: 0.15 }, te - 0.15);
        }
        tl.set(el, { opacity: 0 }, tt.t1);
      }
    }
  }

