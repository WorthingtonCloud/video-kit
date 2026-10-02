// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  parked(stage, seg) {
    // a card resting half past the right edge for the whole segment; one fully in frame beside it is fine
    div("ex-p", stage, "", "left:900px;top:700px;width:400px;height:200px", "half-off");
    div("ex-p", stage, "", "left:200px;top:700px;width:400px;height:200px", "in-frame");
  },
});
