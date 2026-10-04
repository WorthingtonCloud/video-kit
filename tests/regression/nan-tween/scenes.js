// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  nan(stage, seg) {
    // a value that comes out NaN: the stack should scroll up, and silently never moves (contextual-ui v1, Oct 2, 2026:
    // exPath returns {x, y}, used as a number). One that moves for real beside it is fine
    const stuck = div("ex-t", stage, "STUCK", "position:absolute;left:200px;top:700px;font-size:60px", "stuck");
    const moves = div("ex-t", stage, "MOVES", "position:absolute;left:200px;top:1000px;font-size:60px", "moves");
    const p = { x: 0, y: -200 };
    tl.to(stuck, { y: p, duration: 2 }, seg.t0 + 0.5);
    tl.to(moves, { y: -200, duration: 2 }, seg.t0 + 0.5);
    const r = svg("svg", { width: 400, height: 200, style: "position:absolute;left:300px;top:1300px" }, stage);
    const c = svg("circle", { cx: 50, cy: 50, r: 30, fill: "#e8402c" }, r, "dot");
    tl.to(c, { attr: { cx: p }, duration: 2 }, seg.t0 + 0.5);
  },
});
