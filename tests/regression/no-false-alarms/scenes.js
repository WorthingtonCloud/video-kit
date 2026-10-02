// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  calm(stage, seg) {
    // a label on its own solid chip: its own card, never "words on a shape"
    div("ex-chip", stage, "ON ITS OWN CHIP", "left:200px;top:300px", "chip");
    // an outline box well around its words: only its border counts
    const box = div("", stage, "", "position:absolute;left:150px;top:520px;width:780px;height:220px;border:3px solid #fff", "outline");
    div("ex-t", box, "INSIDE AN OUTLINE", "left:60px;top:80px;font-size:44px", "outlined-words");
    // an SVG line beside a label: a line reports a default black fill, and it's a stroke
    const s = svg("svg", { width: 1080, height: 1400, style: "position:absolute;left:0;top:0;overflow:visible" }, stage);
    svg("line", { x1: 150, y1: 820, x2: 930, y2: 960, stroke: "#fff", "stroke-width": 3 }, s, "diagonal");
    div("ex-k", stage, "BESIDE THE LINE", "left:150px;top:990px", "beside");
  },
});
