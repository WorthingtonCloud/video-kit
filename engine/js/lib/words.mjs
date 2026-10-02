// A word spec → the moment the narrator says it. "word" (first match in the given acts, case and punctuation ignored),
// "word#2" (the second), "act:word" (reach into another act), plus "+0.3" / "-0.2" to shift. plan.py reads specs the
// same way (vslib.word_at); tests/contract/cases.json holds both to the same answers.
const norm = (s) => String(s).toLowerCase().replace(/[^a-z0-9]/g, "");
export function wordAt(WORDS, spec, acts) {
  const m = String(spec)
    .trim()
    .match(/^(?:(\d+):)?(.+?)(?:#(\d+))?([+-]\d[\d.]*)?$/);
  if (!m) return { err: `"${spec}" isn't a word spec ("word", "word#2", "act:word", "+0.3")` };
  const [, act, word, nth, shift] = m,
    pool = WORDS.filter((w) => (act ? [+act] : acts).includes(w.act)),
    hits = pool.filter((w) => norm(w.w) === norm(word)),
    k = +(nth || 1);
  if (hits.length < k) return { err: `"${spec}" isn't said in act${act || acts.length === 1 ? "" : "s"} ${act || acts.join(", ")}`, pool };
  return { t: Math.round((hits[k - 1].t0 + +(shift || 0)) * 1000) / 1000, w: hits[k - 1] };
}
