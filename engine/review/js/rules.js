// The human's standing rules, shown where they apply: every keep-clear zone from a sent note, drawn faintly over the
// picture while the playhead is in that note's scene (on the cut it was drawn on). vs inspect enforces them: nothing but
// what a zone was drawn over may enter it. Done scenes show on the timeline and in the Notes panel.
import { app, round } from "./core.js";
import { player } from "./player.js";
import { segmentAt } from "./maps.js";

const LIVE = new Set(["sent", "question", "resolved", "accepted", "reopened"]);
export function zones() {
  const R = round();
  return Object.values(app.state?.notes || {})
    .filter((n) => LIVE.has(n.status) && n.resolution?.outcome !== "wontdo" && (!R || !n.cut || n.cut === R.cut))
    .flatMap((n) => [n.mark, ...(n.also || [])].filter((m) => m?.type === "keep-clear" && m.box).map((z) => ({ note: n.id, segment: n.segment, box: z.box })));
}
let seg = null;
function draw(force) {
  const s = segmentAt(player.t())?.name ?? null;
  if (s === seg && !force) return;
  seg = s;
  player.draw(
    "rules",
    zones()
      .filter((z) => z.segment === s)
      .map((z) => ({ x: z.box[0], y: z.box[1], width: z.box[2] - z.box[0], height: z.box[3] - z.box[1], class: "rule" })),
  );
}
player.on(() => draw());
export const rules = { render: () => draw(true), maps: () => draw(true) };
