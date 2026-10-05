// Parked (engine/js/lib/mapchecks.mjs): something resting partly off the frame. an explainer (Oct 4, 2026): chat turns
// scrolled up out of an overflow-hidden window read as "parked partly off the frame", 24 times, none real. What shows
// is what counts: the window's clip, not the frame.
import { test } from "node:test";
import assert from "node:assert/strict";
import { parked } from "../../engine/js/lib/mapchecks.mjs";

const META = [{ addr: "s01/turn", kind: "text", text: "Here's the draft." }];
const STEP = 0.15,
  C = { offscreen_rest_secs: 1.0 };
// two seconds of a box sitting half above the top of the frame, not moving
const map = (clips) => Array.from({ length: 14 }, (_, k) => [+(k * STEP).toFixed(2), [[0, 0.2, -0.05, 0.6, 0.05]], clips]);

test("a box resting half off the frame is parked", () => {
  const out = parked({ META, seenAt: map(undefined), STEP, C, near: () => false });
  assert.equal(out.length, 1);
  assert.equal(out[0].check, "offscreen-at-rest");
});

test("the same box cut by its window to the part inside the frame is not", () => {
  assert.equal(parked({ META, seenAt: map({ 0: [0.2, 0.0, 0.6, 0.05] }), STEP, C, near: () => false }).length, 0);
});

test("the same box clipped away entirely is not on screen at all", () => {
  assert.equal(parked({ META, seenAt: map({ 0: null }), STEP, C, near: () => false }).length, 0);
});
