// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  cards(stage, seg) {
    const p = div("ex-p", stage, "", "left:200px;top:400px;width:300px;height:200px", "team-card");
    div("ex-k", p, "OTHER TEAM ON THE FAR SIDE", "left:34px;top:28px", "team-label");
  },
});
