// The contract, from JavaScript: every case in cases.json (test_contract.py runs the same cases in Python).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { studioRoot, profile, findKey, hash } from "../../engine/js/lib/paths.mjs";
import { timeSegments } from "../../engine/js/lib/time.mjs";
import { wordAt } from "../../engine/js/lib/words.mjs";

const CASES = JSON.parse(fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "cases.json"), "utf8"));
const KEEP = { ...process.env },
  CWD = process.cwd();

// a fresh folder with the case's tree, its env (HOME always inside it, nothing paid), and its working folder
function runIn(c) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "vk-contract-")));
  for (const [rel, body] of Object.entries(c.tree || {})) {
    const p = path.join(root, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, (typeof body === "string" ? body : JSON.stringify(body)).replaceAll("{root}", root));
  }
  for (const k of ["VIDEO_STUDIO", "K"]) delete process.env[k];
  fs.mkdirSync(path.join(root, "home"), { recursive: true });
  Object.assign(process.env, { HOME: path.join(root, "home"), VIDEO_KIT_NO_SPEND: "1" });
  for (const [k, v] of Object.entries(c.env || {})) process.env[k] = v.replaceAll("{root}", root);
  process.chdir(path.join(root, c.cwd));
  return root;
}
function restore() {
  process.chdir(CWD);
  for (const k of Object.keys(process.env)) if (!(k in KEEP)) delete process.env[k];
  Object.assign(process.env, KEEP);
}
const dig = (d, dotted) => dotted.split(".").reduce((x, k) => x[k], d);

for (const c of CASES.studio)
  test(`studio: ${c.name}`, () => {
    const root = runIn(c);
    try {
      const got = studioRoot();
      assert.equal(got ? fs.realpathSync(got) : null, c.expect ? c.expect.replaceAll("{root}", root) : null);
    } finally {
      restore();
    }
  });

for (const c of CASES.profile)
  test(`profile: ${c.name}`, () => {
    runIn(c);
    try {
      const pr = profile();
      for (const [k, v] of Object.entries(c.expect)) assert.deepEqual(dig(pr, k), v, k);
    } finally {
      restore();
    }
  });

for (const c of CASES.keys)
  test(`keys: ${c.name}`, () => {
    runIn(c);
    try {
      assert.equal(findKey("K")?.value ?? null, c.expect);
    } finally {
      restore();
    }
  });

for (const c of CASES.timing)
  test(`timing: ${c.name}`, () => {
    if (c.expect === null) return assert.throws(() => timeSegments(c.reel));
    const { segs, end } = timeSegments(c.reel);
    assert.deepEqual(Object.fromEntries(segs.map((s) => [s.name, s.t0])), c.expect.T);
    assert.deepEqual(Object.fromEntries(segs.flatMap((s) => s.titles.map((t) => [t.id, t.t0]))), c.expect.TT);
    assert.equal(end, c.expect.END);
  });

for (const c of CASES.words.cases)
  test(`words: ${c.spec} in ${c.acts}`, () => {
    const r = wordAt(CASES.words.words, c.spec, c.acts);
    assert.equal(r.err ? null : r.t, c.expect);
  });

for (const c of CASES.hash) test(`hash: ${JSON.stringify(c.text)}`, () => assert.equal(hash(c.text), c.expect));
