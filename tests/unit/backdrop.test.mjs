// The backdrop (the frame, its light, its dust) is never "on screen" in a note, never under a click, never content:
// an explainer (Oct 4, 2026), a note on empty ground listed twelve dust motes as what was there. One set, three places.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
// the page's modules expect a document; these tests only read the maps
globalThis.document ??= { querySelector: () => null, querySelectorAll: () => [], addEventListener() {}, dispatchEvent() {} };
globalThis.ResizeObserver ??= class { observe() {} };
globalThis.window ??= globalThis;
const { app } = await import("../../engine/review/js/core.js");
const { visibleAt, stackAt, BACKDROP } = await import("../../engine/review/js/maps.js");

const item = (id, box) => ({ id, on: [[0, 5]], boxes: [[0, ...box]] });

test("a note's moment lists what's there, not the dust", () => {
  app.maps = {
    elements: {
      step: 0.15,
      items: [item("frame/paper", [0, 0, 1, 1]), item("s01/~ex-spot", [0, 0, 1, 1]), item("s01/~ex-mote#2", [0.49, 0.49, 0.51, 0.51]),
        item("s01/~ex-glow", [0.3, 0.3, 0.7, 0.7]), item("s01/card", [0.1, 0.1, 0.3, 0.2])],
    },
  };
  assert.deepEqual(visibleAt(1).map((e) => e.id), ["s01/card"]);
  assert.deepEqual(stackAt([0.5, 0.5], 1), []); // a click on empty ground lands on nothing, not a speck
});

test("review.py and mapchecks use the same backdrop", () => {
  const py = fs.readFileSync(new URL("../../engine/py/review.py", import.meta.url), "utf8").match(/BACKDROP = re\.compile\(r"(.*?)"\)/)[1],
    js = fs.readFileSync(new URL("../../engine/js/lib/mapchecks.mjs", import.meta.url), "utf8").match(/const AMBIENT = \/(.*?)\/;/)[1];
  assert.equal(py, BACKDROP.source.replaceAll("\\/", "/"));
  assert.equal(js.replace("(^frame\\/)", "^frame\\/"), BACKDROP.source);
});
