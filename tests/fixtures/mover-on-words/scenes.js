// A mini-project for vs inspect's drawn-mover check (tests/integration/test_movers.py). Three dots drawn on one canvas
// over the scene, each registered with exTrack so inspect can see what no element map can:
//   sits     rests on "WHERE IT RESTS" for a second: a rests-on-text error
//   passes   sweeps across the same words in about a tenth of a second: passing in front is fine
//   beside   rests beside "SHORT", inside its frame-wide box but clear of its glyphs: the box isn't the words
Object.assign(SCENES, {
  movers(stage, seg, f) {
    div("ex-t", stage, "WHERE IT RESTS", "left:240px;top:600px;font-size:80px", "rests-headline");
    div("ex-t", stage, "SHORT", "left:0;right:0;top:900px;font-size:60px;text-align:center", "short-line");
    const fx = (x) => f.x + x * f.s,
      fy = (y) => f.y + y * f.s;
    const tracks = {
      sits: (t) => (t >= 1.2 && t <= 2.2 ? { x: fx(520), y: fy(650), r: 18, o: 1 } : null),
      passes: (t) => (t >= 2.8 && t <= 3.0 ? { x: -100 + ((t - 2.8) / 0.2) * (W + 200), y: fy(650), r: 18, o: 1 } : null),
      beside: (t) => (t >= 3.4 && t <= 4.4 ? { x: fx(120), y: fy(935), r: 18, o: 1 } : null),
    };
    for (const [k, fn] of Object.entries(tracks)) exTrack(k, fn);
    const cv = document.createElement("canvas");
    cv.width = W;
    cv.height = H;
    cv.style.cssText = "position:fixed;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:50";
    document.body.appendChild(cv);
    const cx = cv.getContext("2d");
    ticks.push((t) => {
      cx.clearRect(0, 0, W, H);
      for (const fn of Object.values(tracks)) {
        const d = fn(t);
        if (!d) continue;
        cx.globalAlpha = d.o;
        cx.fillStyle = P.accent;
        cx.beginPath();
        cx.arc(d.x, d.y, d.r, 0, 2 * Math.PI);
        cx.fill();
      }
    });
  },
});
