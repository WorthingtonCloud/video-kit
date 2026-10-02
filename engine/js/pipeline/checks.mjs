// Build step 2, checks for mistakes that each cost a round of notes, before any work is done.
import { R, die } from "./context.mjs";
import { SEGS } from "./timing.mjs";

// ───────── checks for mistakes that each cost a round of notes ─────────
// (an emphasis with no word to land on is vs check's now: check.mjs)
export function checkNever() {
  // Pages that must never be on screen (reel.json → "never": [urls]): whatever the human rules out, and any page whose
  // headline IS the closing line (showing it mid-reel spends the ending before the close).
  const norm = (u) =>
    String(u || "")
      .replace(/[#?].*$/, "")
      .replace(/\/+$/, "")
      .toLowerCase();
  const NEVER = (R.never || []).map(norm);
  SEGS.forEach((s) => {
    const u = s.source.shot && R.shots?.[s.source.shot]?.url;
    if (u && NEVER.includes(norm(u)))
      die(`${s.name}: shot "${s.source.shot}" records ${u}, which reel.json → "never" rules out`);
  });
}
