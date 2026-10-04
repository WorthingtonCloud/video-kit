// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  late(stage, seg) {
    // words timed to arrive after their own segment has ended: they never reach the screen
    div("ex-t", stage, "ON TIME", "position:absolute;left:200px;top:700px;font-size:60px", "on-time");
    const w = div("ex-t", stage, "TOO LATE", "position:absolute;left:200px;top:900px;font-size:60px;opacity:0", "too-late");
    tl.to(w, { opacity: 1, duration: 0.3 }, seg.t1 + 0.5);
  },
});
