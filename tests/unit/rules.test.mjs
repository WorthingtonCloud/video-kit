// The human's standing rules (engine/js/lib/rules.mjs): which notes make a keep-clear rule, and what may sit in a zone.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { readRules, keepClear } from "../../engine/js/lib/rules.mjs";

function project(state) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vk-rules-"));
  fs.mkdirSync(path.join(dir, "review"));
  fs.writeFileSync(path.join(dir, "review/state.json"), JSON.stringify(state));
  return dir;
}
const zone = { type: "keep-clear", box: [0.4, 0.3, 0.6, 0.4], over: ["s/phone", "s/label"], keeps: ["s/phone"] };
const note = (id, status, extra = {}) => ({ id, status, segment: "s", cut: "9x16", mark: { type: "none" }, also: [zone], ...extra });

test("a sent note's zone is a rule; a draft, a withdrawn note and an accepted won't-do aren't", () => {
  const R = readRules(project({ notes: {
    "n-0001": note("n-0001", "sent", { target: { el: "s/label" } }),
    "n-0002": note("n-0002", "draft"),
    "n-0003": note("n-0003", "withdrawn"),
    "n-0004": note("n-0004", "accepted", { resolution: { outcome: "wontdo" } }),
  }, done: { s2: { version: 3, cut: "9x16", video: "out/x-v3.mp4" } } }));
  assert.deepEqual(R.keep.map((z) => z.note), ["n-0001"]);
  assert.deepEqual(R.keep[0].over, ["s/phone"]); // what it protects: what was mostly inside it, never the note's target
  assert.deepEqual(R.done, [{ segment: "s2", version: 3, cut: "9x16", video: "out/x-v3.mp4" }]);
  assert.deepEqual(readRules(fs.mkdtempSync(path.join(os.tmpdir(), "vk-rules-"))), { keep: [], done: [] });
});

test("what may be in the zone: what it protects, what that holds, what holds it; backdrops and holders pass", () => {
  // the scene: a backdrop, a panel holding the phone (and the phone its screen), a label, and a chip holding a word
  const META = [
    { addr: "s/backdrop", up: null }, { addr: "s/panel", up: null }, { addr: "s/phone", up: "s/panel" },
    { addr: "s/screen", up: "s/phone" }, { addr: "s/label", up: null }, { addr: "s/chip", up: null }, { addr: "s/word", up: "s/chip" },
    { addr: "frame/ring", up: null },
  ];
  const at = (t) => [t, [
    [0, 0, 0, 1, 1],                 // fills the frame
    [1, 0.3, 0.2, 0.7, 0.5],         // holds the whole zone
    [2, 0.42, 0.31, 0.58, 0.39],     // what the zone protects
    [3, 0.45, 0.32, 0.55, 0.38],
    [4, 0.5, 0.35, 0.7, 0.42],       // pokes into it: flagged
    [5, 0.55, 0.36, 0.65, 0.39],     // a chip and its word both in it: only the word is named
    [6, 0.56, 0.365, 0.6, 0.385],
    [7, 0.4, 0.3, 0.6, 0.4],         // the camera's own
  ]];
  const seenAt = [0.6, 0.75, 0.9, 1.05].map(at);
  const rules = readRules(project({ notes: { "n-0001": note("n-0001", "sent", { target: { el: "s/label" } }) } }));
  const TL = { segments: [{ name: "s", t0: 0, t1: 2 }] };
  const run = (W, H) => keepClear({ rules, TL, META, seenAt, W, H, near: () => false, MIN: 0.45, STEP: 0.15 });
  const { out } = run(1080, 1920);
  assert.deepEqual(out.map((f) => f.elements[0]).sort(), ["s/label", "s/word"]);
  assert.equal(out[0].check, "keep-clear");
  assert.ok(out[0].hint.includes("n-0001"));
  assert.deepEqual(run(1920, 1080).out, []); // the mark stays with the cut it was drawn on
});

test("a zone whose scene left the build says so instead of checking nothing quietly", () => {
  const rules = readRules(project({ notes: { "n-0001": note("n-0001", "sent") } }));
  const r = keepClear({ rules, TL: { segments: [] }, META: [], seenAt: [], W: 1080, H: 1920, near: () => false, MIN: 0.45, STEP: 0.15 });
  assert.match(r.warn[0], /its scene s isn't in this build/);
});
