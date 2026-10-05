// The reel runtime, part 6 of 7. build concatenates js/reel/*.js in name order into ONE closure (00 opens it, 60
// closes it), so a part is not a module on its own: it shares every const and helper defined in the parts before it.
  // ───────── transitions: every switch lands exactly on the grid ─────────
  const dot = $("#dot"),
    ring = $("#ring");
  const mv = (s) => $(".mover", s.el);
  const hitDot = (t, x, y, big = 16) => {
    // the red point lands and rings out
    tl.fromTo(
      dot,
      { x: x - 28, y: y - 28, opacity: 1, scale: 2.3 },
      { x: x - 28, y: y - 28, opacity: 1, scale: 0, duration: 0.34, ease: "power3.in", ...IR },
      t,
    );
    tl.fromTo(
      ring,
      { x: x - 28, y: y - 28, opacity: 1, scale: 1 },
      { x: x - 28, y: y - 28, opacity: 0, scale: big, duration: 0.75, ease: "expo.out", ...IR },
      t,
    );
  };
  segs.forEach((cur, i) => {
    if (!i) return;
    const prev = segs[i - 1],
      T = cur.t0,
      kind = cur.in || "whip",
      d = Math.round(H * 0.09);
    const shatterOut = prev.source.out === "shatter";
    if (kind === "fade") {
      tl.to(prev.el, { opacity: 0, filter: "blur(10px)", duration: 0.22, ease: "power2.in" }, T - 0.22);
      tl.fromTo(cur.el, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power1.out", ...IR }, T - 0.1);
      return;
    }
    if (kind === "dissolve") {
      // a slow cross-dissolve: the next scene melts in over the last one, no blur, no move; the last one is hidden only
      // once it's covered (a calm parody of an old TV bit with soft nature stills, Oct 5, 2026)
      const dd = cur.source.dissolve ?? 1.4;
      tl.fromTo(cur.el, { opacity: 0 }, { opacity: 1, duration: dd, ease: "sine.inOut", ...IR }, T - dd / 2);
      tl.to(prev.el, { opacity: 0, duration: 0.01, ...IR }, T + dd / 2);
      return;
    }
    if (kind === "over") {
      // this card lands ON the last segment: it dims and keeps moving under the first line, then collapses into the red
      // point on the second line's beat. Only a collage brightens back for its collapse: a scene with words stays dim, or
      // its words fight the card's for the last 0.6 s (the reel template's sources under "This video…", Oct 1, 2026)
      tl.set(cur.el, { opacity: 1 }, T);
      const pcam = $(".cam", prev.el),
        hit = T + ((cur.source.at || [])[1] ?? 2) * B,
        tiles = $$(".tile", prev.el);
      tl.fromTo(
        pcam,
        { filter: "brightness(1) blur(0px)" },
        { filter: "brightness(0.28) blur(5px)", duration: 0.35, ease: "power2.out", ...IR },
        T - 0.05,
      );
      // nothing to collapse: the scene is gone BEFORE the card's first words land, never dimmed behind them ("those
      // shapes in the background should be gone before the 'This reel?' text comes on screen", video-kit reel, Oct 2)
      if (!tiles.length) tl.to(prev.el, { opacity: 0, duration: 0.35, ease: "power2.in" }, T - 0.4);
      if (tiles.length)
        // the collapse lifts only to half, still soft: the card's first line is up over it, and a sharp, bright collage
        // under "This video?" was words on photos (vs inspect, The Lab reel v23, Oct 4, 2026)
        tl.fromTo(
          pcam,
          { filter: "brightness(0.28) blur(5px)" },
          { filter: "brightness(0.55) blur(4px)", duration: 0.2, ease: "power1.out", ...IR },
          hit - 0.62,
        );
      if (tiles.length) {
        const each = 0.012,
          dur = 0.42,
          s0 = hit - dur - each * (tiles.length - 1);
        tl.fromTo(
          tiles,
          { x: 0, y: 0, z: 0, scale: 1, opacity: 1, rotation: 0 },
          {
            x: (k, el) => +el.dataset.dx,
            y: (k, el) => +el.dataset.dy,
            z: 0,
            scale: 0.04,
            opacity: 0.2,
            rotation: (k) => (k % 2 ? 40 : -40),
            duration: dur,
            ease: "power3.in",
            stagger: { each, from: "edges" },
            ...IR,
          },
          s0,
        );
      }
      tl.set(prev.el, { opacity: 0 }, hit + 0.02);
      // the point is where a collage collapses to; with nothing collapsing it only lands on the card's own words
      // (dead center = the middle line: "The red dot over the text makes it hard to read", video-kit reel, Oct 2, 2026)
      if (tiles.length) hitDot(hit, W / 2, H / 2, 20);
      punch(hit, 0.05);
      return;
    }
    const s0 = ["swing", "depth"].includes(kind)
      ? T - 0.3
      : kind === "drop"
        ? T - 0.25
        : kind === "rise"
          ? T - 0.12
          : T;
    const hideAt = shatterOut
      ? T + 0.85
      : kind === "swing"
        ? s0 + 0.62
        : kind === "depth"
          ? s0 + 0.45
          : kind === "drop"
            ? T + 0.3
            : T;
    tl.set(cur.el, { opacity: 1 }, s0);
    tl.set(prev.el, { opacity: 0 }, hideAt);
    if (shatterOut) tl.set(prev.el, { zIndex: 5 }, T - 0.2); // the flying letters pass in front of what's arriving
    if (kind === "whip") {
      // out accelerates up into a blur, in decelerates out of it: one continuous move
      tl.to(prev.el, { y: -d, filter: "blur(26px)", duration: 0.2, ease: "power2.in" }, T - 0.2);
      tl.fromTo(
        cur.el,
        { y: d, filter: "blur(26px)" },
        { y: 0, filter: "blur(0px)", duration: 0.5, ease: "power3.out", ...IR },
        T,
      );
    } else if (kind === "whipx") {
      // the same, sideways
      tl.to(prev.el, { x: -2 * d, filter: "blur(26px)", duration: 0.2, ease: "power2.in" }, T - 0.2);
      tl.fromTo(
        cur.el,
        { x: 2 * d, filter: "blur(26px)" },
        { x: 0, filter: "blur(0px)", duration: 0.5, ease: "power3.out", ...IR },
        T,
      );
    } else if (kind === "zoom") {
      // the camera dollies through the outgoing frame
      tl.to(
        prev.el,
        { scale: 5, opacity: 0, filter: "blur(14px)", transformOrigin: "50% 50%", duration: 0.32, ease: "power2.in" },
        T - 0.32,
      );
    } else if (kind === "flash") {
      tl.fromTo(
        cur.el,
        { filter: "brightness(3.2)" },
        { filter: "brightness(1)", duration: 0.35, ease: "power2.out", ...IR },
        T,
      );
    } else if (kind === "rise") {
      // the outgoing scene whips up and away; the page swings up into view like a phone raised to the eye
      tl.to(prev.el, { y: -d, filter: "blur(26px)", duration: 0.2, ease: "power2.in" }, T - 0.2);
      tw3(
        mv(cur),
        { y: H * 0.5, rotationX: 58, scale: 0.85, ...(LAND ? {} : { transformOrigin: "50% 70%" }), ...TP },
        { y: 0, rotationX: 0, scale: 1, ...TP, duration: 0.7, ease: "power4.out", ...IR },
        T - 0.12,
      );
      punch(T + 0.1, 0.02);
    } else if (kind === "swing") {
      // a carousel: both pages travel together, curving away as they go
      tw3(
        mv(prev),
        { x: 0, rotationY: 0, ...TP },
        { x: -W * 1.02, rotationY: 50, ...TP, duration: 0.62, ease: "power3.inOut", ...IR },
        s0,
      );
      tw3(
        mv(cur),
        { x: W * 1.02, rotationY: -50, ...TP },
        { x: 0, rotationY: 0, ...TP, duration: 0.62, ease: "power3.inOut", ...IR },
        s0,
      );
    } else if (kind === "depth") {
      // the outgoing page flies past the camera; the next rushes in from far away
      tl.set(prev.el, { zIndex: 5 }, s0);
      tw3(
        mv(prev),
        { z: 0, rotationY: 0, opacity: 1, filter: "blur(0px)", ...TP },
        { z: 1000, rotationY: -14, opacity: 0, filter: "blur(14px)", ...TP, duration: 0.45, ease: "power2.in", ...IR },
        s0,
      );
      tw3(
        mv(cur),
        { z: -2800, x: W * 0.4, y: -H * 0.12, rotationY: 30, opacity: 0, ...TP },
        { z: 0, x: 0, y: 0, rotationY: 0, opacity: 1, ...TP, duration: 0.7, ease: "power3.out", ...IR },
        s0,
      );
    } else if (kind === "flip") {
      // turned over like a card
      tw3(
        mv(prev),
        { rotationY: 0, ...TP },
        { rotationY: -90, ...TP, duration: 0.26, ease: "power2.in", ...IR },
        T - 0.26,
      );
      tw3(mv(cur), { rotationY: 90, ...TP }, { rotationY: 0, ...TP, duration: 0.45, ease: "back.out(1.4)", ...IR }, T);
    } else if (kind === "drop") {
      // the old page sinks back; the new one drops in from above and lands
      tw3(
        mv(prev),
        { y: 0, z: 0, rotationX: 0, opacity: 1, ...TP },
        { y: H * 0.25, z: -900, rotationX: -22, opacity: 0, ...TP, duration: 0.55, ease: "power2.in", ...IR },
        s0,
      );
      tw3(
        mv(cur),
        { y: -H * 1.1, rotation: -9, rotationX: -25, ...TP },
        { y: 0, rotation: 0, rotationX: 0, ...TP, duration: 0.75, ease: "back.out(1.25)", ...IR },
        s0,
      );
      punch(s0 + 0.42, 0.025);
    } else if (kind === "dot") {
      // the outgoing frame collapses into its accent point, which flies to center and hits
      tl.seek(T - 0.34);
      frame(T - 0.34); // where the point really is at that moment (the scene's camera has moved)
      const el = $("[data-anchor]", prev.el),
        r = el && el.getBoundingClientRect(),
        a = r ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : ANCH[i - 1];
      tl.to(
        prev.el,
        { scale: 0.04, opacity: 0, transformOrigin: `${a.x}px ${a.y}px`, duration: 0.34, ease: "power3.in" },
        T - 0.34,
      );
      tl.fromTo(
        dot,
        { x: a.x - 28, y: a.y - 28, opacity: 1, scale: 1 },
        { x: W / 2 - 28, y: H / 2 - 28, opacity: 1, scale: 1, duration: 0.34, ease: "power3.in", ...IR },
        T - 0.34,
      );
      hitDot(T, W / 2, H / 2);
      punch(T, 0.05);
    }
  });
  (R.punches || []).forEach((p) => (Array.isArray(p) ? punch(p[0], p[1] ?? 0.03) : punch(p, 0.03)));

