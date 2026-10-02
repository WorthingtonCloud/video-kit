// The fixture's own scene: one panel the scene names, a label and a chip it doesn't (they get derived names).
Object.assign(SCENES, {
  board(stage, seg) {
    const c = R.scenes[seg.source.scene]?.cues || {};
    const p = div("ex-p", stage, "", "left:140px;top:300px;width:800px;height:420px", "the-board");
    div("ex-k", p, "THE PLAN", "left:34px;top:28px");
    const chip = div("ex-chip red", p, "PINNED TO A WORD", "left:34px;top:120px");
    exPop(chip, (c.plan ?? seg.t0) + 0.1);
  },
});
