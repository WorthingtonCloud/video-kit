// A deliberately broken scene (tests/regression): expect.json says which scar it pins.
Object.assign(SCENES, {
  money(stage, seg) {
    div("ex-t", stage, "HEAR IT $$ · $& · $1 · $'", "left:150px;top:500px;font-size:48px", "price");
  },
});
