// Graphics pinned to footage the way a footage-first video draws them (Oct 2026): every overlay sits on
// a clear sheet the size of the frame, and a line drawing is its own frame-sized <svg> with one small arrow in it. A click
// on the arrow has to find the arrow, on the caption the caption, and on bare footage the footage: never the sheets.
{
  const css = document.createElement("style");
  css.textContent = `
  .ov{position:absolute;inset:0;pointer-events:none}
  .ov-svg{position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:visible}
  .ov-cap{position:absolute;left:160px;top:820px;padding:14px 22px;font:700 54px Archivo,sans-serif;color:#fff;background:#0b0d10}`;
  document.head.appendChild(css);
}
Object.assign(SCENES, {
  o_marks(stage, seg) {
    const L = div("ov", stage.parentNode, "", "", "marks-layer");
    const sheet = div("ov-svg", L, "", "", "marks-arrow");
    sheet.innerHTML = `<svg width="1920" height="1080" viewBox="0 0 1920 1080" style="overflow:visible">
      <path d="M1500 300 C 1450 230, 1390 205, 1322 214" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round"/>
      <path d="M1356 186 L 1316 214 L 1352 246" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round"/></svg>`;
    const cap = div("ov-cap", L, "THE GARAGE", "", "marks-caption");
    tl.fromTo([sheet, cap], { opacity: 0 }, { opacity: 1, duration: 0.2 }, seg.t0 + 0.2);
  },
});
