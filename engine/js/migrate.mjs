#!/usr/bin/env node
// vs migrate: mark this project's plan.json and reel.json as schema_version 2, the contracts vs check enforces, then
// check them. An unmarked file still builds, with its problems as warnings; once marked, a problem stops the build.
// Only the one line is inserted, so everything else in the file stays byte for byte.
import fs from "node:fs";
import { check } from "./check.mjs";

let n = 0;
for (const f of ["plan.json", "reel.json"]) {
  if (!fs.existsSync(f)) continue;
  const text = fs.readFileSync(f, "utf8"),
    doc = JSON.parse(text);
  if (doc.schema_version === 2) {
    console.log(`${f}: already schema_version 2`);
    continue;
  }
  if (doc.schema_version != null) {
    console.error(`⛔ ${f}: schema_version ${doc.schema_version} is one this kit doesn't know`);
    process.exit(1);
  }
  const m = text.match(/^\{[ \t]*\r?\n([ \t]*)/);
  fs.writeFileSync(
    f,
    m ? text.replace(m[0], `${m[0]}"schema_version": 2,\n${m[1]}`) : JSON.stringify({ schema_version: 2, ...doc }, null, 1) + "\n",
  );
  console.log(`${f}: marked schema_version 2`);
  n++;
}
if (!n && !fs.existsSync("plan.json") && !fs.existsSync("reel.json")) {
  console.error("⛔ no plan.json or reel.json here: run it in a project folder");
  process.exit(1);
}
const { errors } = check();
if (errors.length) console.log("Fix those, then vs check again: from here on they stop the build.");
process.exit(errors.length ? 1 : 0);
