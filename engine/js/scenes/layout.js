// Explainer scene library, part 4 of 4 (inlined AFTER the project's scenes, so it wraps them).
// Widescreen (plan.py --wide): the words live on the left, and an explainer's titles come and go, so a scene pinned to
// the right would leave half the frame empty most of the time. Each scene in this file sits in the middle of the frame
// and slides right only while a title is up: it arrives as the title lands and goes back as it leaves; short gaps, and
// a title near a cut, hold the side. The kit's own scenes keep the kit's layout.
if (LAND)
  for (const k of Object.keys(SCENES)) {
    if (KIT_SCENES.has(k)) continue;
    const draw = SCENES[k];
    SCENES[k] = (stage, seg, f) => {
      const out = draw(stage, seg, f),
        GL = 0.6,
        DX = W / 2 - 540 * f.s - f.x,
        spans = [];
      for (const tt of [...(seg.titles || [])].sort((a, b) => a.t0 - b.t0)) {
        const a = tt.t0 - GL - seg.t0 < 1.2 ? -Infinity : tt.t0 - GL,
          b = seg.t1 - tt.t1 < 1.2 ? Infinity : tt.t1,
          L = spans[spans.length - 1];
        if (L && a - L[1] < 2.5) L[1] = Math.max(L[1], b);
        else spans.push([a, b]);
      }
      // the slide is a wrapper's x (a transform: `left` snaps to whole pixels and stutters, the lint refuses it)
      const slide = document.createElement("div");
      slide.style.cssText = "position:absolute;inset:0";
      stage.before(slide);
      slide.appendChild(stage);
      slide.style.transform = `translateX(${spans[0]?.[0] === -Infinity ? 0 : DX}px)`;
      let first = true; // the first move paints its start at load; every later one waits for its time (IR)
      const move = (t, from, to) => {
        tl.fromTo(slide, { x: from }, { x: to, duration: GL, ease: "power2.inOut", ...(first ? {} : IR) }, t);
        first = false;
      };
      for (const [a, b] of spans) {
        if (a > -Infinity) move(a, DX, 0);
        if (b < Infinity) move(b, 0, DX);
      }
      return out;
    };
  }
