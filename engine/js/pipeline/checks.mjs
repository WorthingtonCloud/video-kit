// Build step 2, checks for mistakes that each cost a round of notes, before any work is done.
import { R, die } from "./context.mjs";
import { SEGS } from "./timing.mjs";

// ───────── checks for mistakes that each cost a round of notes ─────────
export function checkTitles() {
  // An emphasis whose word isn't in its title shows nothing, silently ("word" must match with its punctuation).
  const plain = (html) =>
    String(html || "")
      .replace(/<br\s*\/?>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .split(/\s+/)
      .filter(Boolean);
  for (const [id, tt] of Object.entries(R.titles || {})) {
    const em = typeof tt.em === "string" ? { fx: tt.em } : tt.em;
    if (!em) continue;
    if (em.word ? !plain(tt.text).includes(em.word) : !/class=["']?a[\s"'>]/.test(tt.text || ""))
      console.log(
        `  ⚠️  ${id}: its emphasis has nothing to land on (${em.word ? `"${em.word}" isn't a word of the title; punctuation counts` : 'no accent word and no "word"'}), so it won't show`,
      );
  }
}

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
