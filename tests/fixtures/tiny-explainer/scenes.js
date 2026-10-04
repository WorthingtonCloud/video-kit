// The fixture's own scene: one panel the scene names, a label and a chip it doesn't (they get derived names).
Object.assign(SCENES, {
  board(stage, seg) {
    const c = R.scenes[seg.source.scene]?.cues || {};
    const p = div("ex-p", stage, "", "left:140px;top:300px;width:800px;height:420px", "the-board");
    div("ex-k", p, "THE PLAN", "left:34px;top:28px");
    const chip = div("ex-chip red", p, "PINNED TO A WORD", "left:34px;top:120px");
    // on its word when the word falls in this segment, else as the segment opens (a cue past the segment's end never
    // shows: vs inspect's never-seen caught this fixture doing exactly that, Oct 4, 2026)
    const at = c.plan != null && c.plan < seg.t1 - 0.5 ? c.plan : seg.t0;
    exPop(chip, at + 0.1);
  },
});
