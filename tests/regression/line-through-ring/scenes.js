// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  ring(stage, seg) {
    const s = svg("svg", { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" }, stage);
    svg("circle", { cx: 540, cy: 600, r: 180, fill: "none", stroke: "#fff", "stroke-width": 4 }, s, "ring");
    div("ex-k", stage, "ROUND 1", "left:470px;top:404px;font-size:30px", "round-label");
  },
});
