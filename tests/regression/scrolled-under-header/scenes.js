// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  page(stage, seg) {
    // a page scrolled up under its own solid header: the lines above the viewport are clipped, not on the kicker
    const p = div("ex-p", stage, "", "left:140px;top:300px;width:800px;height:620px", "page");
    div("", p, "", "position:absolute;left:0;right:0;top:0;height:96px;background:#1a1b1f", "header");
    div("ex-k", p, "THE NOTES", "left:34px;top:34px", "kicker");
    const view = div("", p, "", "position:absolute;left:0;right:0;top:96px;bottom:0;overflow:hidden", "viewport");
    const body = div("", view, "", "position:absolute;left:34px;top:-180px;width:700px", "body");
    for (let k = 0; k < 14; k++) div("", body, `Line ${k + 1} of the meeting notes`, `position:absolute;top:${k * 56}px;font-size:34px;color:#f2f2f0;white-space:nowrap`);
  },
});
