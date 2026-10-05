// A scene that used to raise a false alarm (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  chat(stage, seg) {
    // a conversation window; its first turn has scrolled up out of it, past the top of the frame. The window hides it,
    // so nothing is parked off the frame
    const win = div("", stage, "", "position:absolute;left:140px;top:260px;width:800px;height:700px;overflow:hidden;border:2px solid #444", "window");
    div("ex-p", win, "", "left:40px;top:-560px;width:720px;height:420px", "scrolled-out");
    div("ex-p", win, "", "left:40px;top:120px;width:720px;height:200px", "latest");
  },
});
