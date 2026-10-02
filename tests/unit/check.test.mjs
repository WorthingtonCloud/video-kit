// vs check (engine/js/check.mjs) and the schemas: a clean project passes, each planted mistake is named with its fix,
// and every template and example the kit ships validates.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { check, near, sceneNames } from "../../engine/js/check.mjs";

const KIT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const require = createRequire(path.join(KIT, "engine/package.json"));

function project(reel, files = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vk-check-"));
  process.env.HOME = dir; // no studio: nobody's real profile or library is read
  delete process.env.VIDEO_STUDIO;
  fs.writeFileSync(path.join(dir, "reel.json"), JSON.stringify(reel));
  for (const [f, body] of Object.entries({ "music/take1.mp3": "", ...files })) {
    fs.mkdirSync(path.dirname(path.join(dir, f)), { recursive: true });
    fs.writeFileSync(path.join(dir, f), body);
  }
  return dir;
}
const GOOD = {
  schema_version: 2,
  name: "t",
  size: [1080, 1920],
  fps: 30,
  music: { file: "music/take1.mp3", beat: 0.5, first_hit: 1 },
  titles: { t_a: { kind: "lower", text: "Hello <span class=a>world</span>", em: "pulse" } },
  segments: [
    { name: "s01", to_hit: true, source: { scene: "chat" }, titles: [["t_a", 0, "end"]] },
    { name: "s02", beats: 4, in: "zoom", source: { scene: "endcard" } },
  ],
};
const clone = () => JSON.parse(JSON.stringify(GOOD));

test("a clean project checks out", () => {
  const r = check({ dir: project(GOOD), quiet: true });
  assert.deepEqual(r.errors, []);
});

test("each planted mistake is named, with the likely fix", () => {
  const R = clone();
  R.budjet_usd = 5;
  R.segments[1].in = "zoomm";
  R.segments[1].source.scene = "endcrd";
  R.segments[0].titles[0][0] = "t_b";
  R.segments[1].secs = 2;
  R.titles.t_a.em = { fx: "box", word: "World!" };
  R.segments.push({ name: "s01", secs: 1, source: { clip: "clips/nope.mp4" } });
  const e = check({ dir: project(R), quiet: true }).errors.join("\n");
  for (const want of [
    'unknown key "budjet_usd" (did you mean "budget_usd"?)',
    '"zoomm" isn\'t one of',
    'no scene "endcrd" (did you mean "endcard"?)',
    'no title "t_b" (did you mean "t_a"?)',
    "give it ONE length, not beats and secs",
    '"World!" isn\'t a word of the title',
    'the name "s01" is used twice',
    "clips/nope.mp4 doesn't exist",
  ])
    assert.ok(e.includes(want), `missing: ${want}\n${e}`);
});

test("an older file only warns until vs migrate marks it", () => {
  const R = clone();
  delete R.schema_version;
  R.budjet_usd = 5;
  const r = check({ dir: project(R), quiet: true });
  assert.equal(r.errors.length, 0);
  assert.ok(r.warnings.some((w) => w.includes("vs migrate")));
});

test("did you mean, and scene names from definitions only (not calls)", () => {
  assert.equal(near("zoomm", ["zoom", "whip"]), ' (did you mean "zoom"?)');
  assert.equal(near("completely-different", ["zoom"]), "");
  const s = sceneNames(`Object.assign(SCENES, {\n  pitch(stage, seg) {\n    exLight(stage, 540, 600);\n  },\n  cage: (stage, seg) => {},\n});\nSCENES.extra = (stage) => 1;`);
  assert.deepEqual([...s].sort(), ["cage", "extra", "pitch"]);
});

test("every schema compiles, and every template and example the kit ships validates", () => {
  const Ajv = require("ajv/dist/2020").default,
    ajv = new Ajv({ allErrors: true, strict: false });
  const SD = path.join(KIT, "engine/schema");
  for (const f of fs.readdirSync(SD)) ajv.addSchema(JSON.parse(fs.readFileSync(path.join(SD, f), "utf8")));
  for (const f of fs.readdirSync(SD)) assert.ok(ajv.getSchema(`video-kit/${f}`), f);
  for (const [file, schema] of [
    ["templates/reel/reel.json", "reel"],
    ["templates/explainer/plan.json", "plan"],
    ["examples/meeting-explainer/plan.json", "plan"],
    ["templates/studio/profile.json", "profile"],
    ["library/sfx/index.json", "sounds"],
  ]) {
    const v = ajv.getSchema(`video-kit/${schema}.schema.json`),
      doc = JSON.parse(fs.readFileSync(path.join(KIT, file), "utf8"));
    assert.ok(v(doc), `${file}: ${JSON.stringify(v.errors?.slice(0, 3))}`);
    if (schema === "reel" || schema === "plan") assert.equal(doc.schema_version, 2, file);
  }
});
