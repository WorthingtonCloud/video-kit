// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  busy(stage, seg) {
    // the scene's own sentence, up the whole time a title is
    div("ex-chip", stage, "A SCENE WITH ITS OWN WORDS", "left:200px;top:500px", "scene-words");
  },
});
