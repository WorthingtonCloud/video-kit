// Dead air (engine/js/lib/mapchecks.mjs): nothing but the backdrop on screen for a stretch. The Jev explainer's v3 had
// three such stretches; vs inspect on its composition finds exactly those, and none on v4 (checked Oct 2, 2026).
import { test } from "node:test";
import assert from "node:assert/strict";
import { deadAir } from "../../engine/js/lib/mapchecks.mjs";

const META = [
  { addr: "frame/paper", kind: "group", text: "" },
  { addr: "s01/~ex-spot", kind: "box", text: "" },
  { addr: "s01/~ex-mote#3", kind: "box", text: "" },
  { addr: "s01/panel", kind: "group", text: "" },
  { addr: "s01/label", kind: "text", text: "Coal burned" },
  { addr: "s01/~stage", kind: "group", text: "" },
];
const STEP = 0.15,
  C = { dead_air_secs: 0.6 };
const backdrop = [[0, -0.1, -0.1, 1.1, 1.1], [1, 0.2, 0.2, 0.8, 0.6], [2, 0.5, 0.5, 0.51, 0.51], [5, 0, 0, 1, 1]];
// moments 0–6 s; the panel is away from `gone[0]` to `gone[1]`
const map = (gone) =>
  Array.from({ length: 41 }, (_, k) => {
    const t = +(k * STEP).toFixed(2);
    return [t, t >= gone[0] && t <= gone[1] ? backdrop : [...backdrop, [3, 0.1, 0.3, 0.9, 0.6], [4, 0.2, 0.4, 0.5, 0.45]]];
  });

test("a second with nothing but the frame, its light, its dust and an empty stage is dead air", () => {
  const out = deadAir({ META, seenAt: map([2.1, 3.0]), STEP, C, cuts: [0] });
  assert.equal(out.length, 1);
  assert.equal(out[0].check, "dead-air");
  assert.deepEqual([out[0].t0, out[0].t1], [2.1, 3]);
  assert.match(out[0].text, /backdrop for 1\.\ds/);
});

test("a blink shorter than dead_air_secs, or one inside a cut's window, isn't", () => {
  assert.equal(deadAir({ META, seenAt: map([2.1, 2.4]), STEP, C, cuts: [0] }).length, 0);
  assert.equal(deadAir({ META, seenAt: map([2.85, 3.45]), STEP, C, cuts: [3.0] }).length, 0); // the transition
  assert.equal(deadAir({ META, seenAt: map([2.1, 3.0]), STEP, C: { dead_air_secs: 2 }, cuts: [0] }).length, 0); // profile.json → checks
});

test("a first frame with nothing but the backdrop is a blank start; one with the opening on it is not", async () => {
  const { blankStart } = await import("../../engine/js/lib/mapchecks.mjs");
  const blank = blankStart({ META, seenAt: map([0, 1.0]) });
  assert.equal(blank.length, 1);
  assert.equal(blank[0].check, "blank-start");
  assert.equal(blankStart({ META, seenAt: map([2.1, 3.0]) }).length, 0);
});
