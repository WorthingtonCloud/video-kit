// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  words(stage, seg) {
    // a scene full of words, right where the next segment's card lands
    for (let k = 0; k < 6; k++)
      div("ex-chip", stage, ["FILING", "VIDEO", "METHOD", "PAPER", "DATA", "CODE"][k], `left:${140 + (k % 3) * 280}px;top:${860 + Math.floor(k / 3) * 120}px`);
  },
});
