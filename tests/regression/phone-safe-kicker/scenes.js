// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  panel(stage, seg) {
    const p = div("ex-p", stage, "", "left:130px;top:30px;width:820px;height:400px", "panel");
    div("ex-k", p, "UNDER THE STATUS BAR", "left:34px;top:24px", "kicker");
  },
});
