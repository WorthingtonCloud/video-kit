// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  flash(stage, seg) {
    // six words on screen for half a second: two seconds to read them
    const k = div("ex-k", stage, "SIX WORDS ARE ON THIS CARD", "left:200px;top:600px", "quick-label");
    tl.fromTo(k, { opacity: 0 }, { opacity: 1, duration: 0.05 }, seg.t0 + 1.0);
    tl.to(k, { opacity: 0, duration: 0.05 }, seg.t0 + 1.5);
    div("ex-k", stage, "STAYS", "left:200px;top:800px", "slow-label"); // one word, the whole segment: fine
  },
});
