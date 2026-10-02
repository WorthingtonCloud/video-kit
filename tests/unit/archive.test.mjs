// A version keeps its own maps (engine/js/lib/archive.mjs): build/ moves on, a review round and Compare don't.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { archive } from "../../engine/js/lib/archive.mjs";

function project(files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vk-archive-"));
  for (const [f, body] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(dir, f)), { recursive: true });
    fs.writeFileSync(path.join(dir, f), JSON.stringify(body));
  }
  return dir;
}
const read = (dir, f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));

test("a render keeps the timing, the element map and the findings made from its own composition", () => {
  const dir = project({
    "build/timeline.json": { fingerprint: "fp3", version: 3, engine: "e", reel: "r", size: [1080, 1920] },
    "build/elements.json": { fingerprint: "fp3", items: [{ id: "s01/a" }] },
    "build/findings.json": { fingerprint: "fp3", items: [] },
  });
  const a = archive("out/x-v3.mp4", { dir, now: new Date("2026-10-01T22:00:00Z") });
  assert.deepEqual(a, { home: "out/x-v3.review", kept: ["timeline.json", "elements.json", "findings.json"], skipped: [] });
  assert.equal(read(dir, "out/x-v3.review/elements.json").items[0].id, "s01/a");
  const v = read(dir, "out/x-v3.review/version.json");
  assert.equal(v.version, 3);
  assert.equal(v.fingerprint, "fp3");
  assert.equal(v.rendered, "2026-10-01T22:00:00.000Z");
});

test("a map made from another composition is never kept (it would point at the wrong things)", () => {
  const dir = project({
    "build/timeline.json": { fingerprint: "fp4", version: 4 },
    "build/elements.json": { fingerprint: "fp3", items: [] },
    "out/x-v4.review/elements.json": { fingerprint: "stale", items: [] },
  });
  const a = archive("out/x-v4.mp4", { dir });
  assert.deepEqual(a.kept, ["timeline.json"]);
  assert.deepEqual(a.skipped, ["elements.json", "findings.json"]);
  assert.equal(fs.existsSync(path.join(dir, "out/x-v4.review/elements.json")), false);
});
