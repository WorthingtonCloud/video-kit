// Where the video stands (video.json, engine/protocol/files.md) decides what may render: vs build asks before anything
// else, so a refusal costs no time. A project with no video.json gets one on its first render, in the shape being built.
// Refused, each with its way out:
//   a finished video (status done)                      → vs reopen <video>
//   the other shape while the first isn't approved yet  → vs shape <it> once it is, or --early "<why>" (logged)
import fs from "node:fs";
import { activeShape, videoName } from "./paths.mjs";

export function lifecycle(args = process.argv.slice(2)) {
  const SHAPE = activeShape(),
    at = new Date().toISOString(),
    early = args.includes("--early") ? args[args.indexOf("--early") + 1] : null,
    die = (msg) => {
      console.error(`⛔ ${msg}`);
      process.exit(1);
    },
    save = (V) => fs.writeFileSync("video.json", JSON.stringify(V, null, 1) + "\n");
  if (!fs.existsSync("video.json")) {
    save({ schema_version: 1, video: videoName(), first: SHAPE, building: SHAPE, status: "first", finals: [],
      log: [{ at, event: `started in ${SHAPE} (vs build made video.json)` }] });
    console.log(`  video.json: ${videoName()}, starting in ${SHAPE}`);
    return;
  }
  const V = JSON.parse(fs.readFileSync("video.json", "utf8"));
  if (V.status === "done") die(`${V.video} is finished (filed in finals/). A change starts a new version: vs reopen ${V.video}`);
  if (V.status === "first" && SHAPE !== V.first) {
    if (!early || early.startsWith("--"))
      die(`${V.video} is still on its first shape (${V.first}): the ${SHAPE} is made once the ${V.first} is approved ` +
        `(then vs shape ${SHAPE}). A real pivot: --early "<why>"`);
    V.log = [...(V.log || []), { at, event: `rendered ${SHAPE} early`, why: early }];
    save(V);
    console.log(`  ⚠️  rendering the ${SHAPE} before the ${V.first} is approved (--early: ${early}; logged)`);
  }
  if (V.status === "second" && SHAPE === V.first)
    console.log(`  ⚠️  a new ${SHAPE} version: the approved one is replaced, so this one needs approving again`);
}
