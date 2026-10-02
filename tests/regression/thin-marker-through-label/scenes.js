// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  chart(stage, seg) {
    // a dashed marker drawn only as a border-left, through a number: thin, and not its top border (the audit missed both)
    div("ex-m", stage, "49.9%", "left:420px;top:560px;font-size:64px", "value");
    div("", stage, "", "position:absolute;left:500px;top:420px;width:0;height:360px;border-left:4px dashed #e8402c", "marker");
  },
});
