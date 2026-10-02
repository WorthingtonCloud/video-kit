// A scene by design (tests/regression): expect.json says which decision it pins.
Object.assign(SCENES, {
  hub2(stage, seg) {
    // a label sitting ON its ring with a halo in the ground color, as the kit's hub draws them: the halo cuts the ring
    // around each letter, and the ring runs on through the gap between the words
    const s = svg("svg", { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" }, stage);
    svg("circle", { cx: 540, cy: 600, r: 200, fill: "none", stroke: "#2c2d33", "stroke-width": 3 }, s, "ring");
    const t = svg("text", { x: 540, y: 407, "text-anchor": "middle", fill: "#9b9da4", "font-weight": 700, "font-size": 19,
      "letter-spacing": 3, "paint-order": "stroke", stroke: "#111114", "stroke-width": 12, class: "mono" }, s, "ring-label");
    t.textContent = "LAYER 1";
  },
});
