// This video's scenes. The engine's scene library is already loaded around this file (helpers ex*, icons GLX, props
// like exStamp / exBell / exPhoto; see the explainer skill's references/scenes.md), and so is everything the renderer
// shares: tl, ticks, svg, div, tw3, punch, easeOut, easeInOut, clamp, IR, TP, mulberry32, P (the palette), W, H, LAND.
// Every cue in R.scenes.<scene>.cues is the absolute time of a word the narrator says (plan.json → segments → cues).
// Write props only this video needs here too; when one would serve another video, move it to the studio's
// library/scenes/ (vs learn reminds you).
Object.assign(SCENES, {
  intro(stage, seg) {
    const c = R.scenes.intro?.cues || {};
    exLight(stage, 540, 600, 780, seg, 26, 11);
    const rig = exRig(stage, seg, { rotationX: 8, rotationY: -8 }, { rotationX: 2, rotationY: 6 });
    const card = div("ex-p", rig, "", "left:110px;top:260px;width:860px;height:520px");
    div("ex-k", card, "A KICKER", "left:34px;top:28px");
    exIn(card, seg.t0 + 0.05, { y: 80, scale: 0.94 }, 0.55);
    const pt = exPoint(rig, 22);
    exAt(pt, 540, 520);
    exPop(pt, c.first ?? seg.t0 + 0.6, 0.3, 0.5);
    return "own-push";
  },
});
// A scene whose kicker sits near the top can ride lower on a vertical cut only: exRideLower(["intro"], 60);
