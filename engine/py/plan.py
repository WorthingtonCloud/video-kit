#!/usr/bin/env python3
"""Narration → reel.json. The voice is the clock: every segment starts just before its act's first word, every scene
cue and title is pinned to a word the narrator says. Re-record the narration, re-run this, and the whole cut re-times itself.
Usage: vs plan [--wide]   (reads plan.json + the words file it names; writes reel.json)
  --wide = the widescreen cut of the same plan: 1920×1080, name + "-16x9". Same voice, same times, so the vertical
  cut's final audio fits it exactly. Scenes that need a different layout read LAND (true when W > H).

In plan.json a word spec is "word" (first match in the segment's acts, case and punctuation ignored), "word#2" (second
match), or "act:word" to reach into another act; add "+0.3" / "-0.2" to shift. Titles: [id, from, to] with "end".
A long act can carry two scenes: give the second segment the same act and "start": "<word spec>" (it begins `lead` seconds
before that word; the segment before it ends there)."""
import json, os, re, subprocess, sys
from vslib import CONTRACTS, word_at

P = json.load(open("plan.json"))
if "--wide" in sys.argv[1:]: P["size"], P["name"] = CONTRACTS["sizes"]["wide"], P["name"] + "-16x9"
WORDS = json.load(open(P["words"]))

def at(spec, acts):
    try: return word_at(WORDS, spec, acts)[0]
    except ValueError as e: raise SystemExit(str(e))

# a bare word said more than once in its acts takes the first, maybe not the one meant (a parody ad, Oct 2, 2026:
# "job" hit "doing a job" early, so the punchline fired a line too soon): say so, and how to point at the later one
norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
def twice(seg, what, spec, acts):
    m = re.fullmatch(r"(?:(\d+):)?(.+?)(?:#(\d+))?([+-]\d[\d.]*)?", str(spec).strip())
    if not m or m.group(1) or m.group(3) or spec == "end": return
    hits = [w for w in WORDS if w["act"] in acts and norm(w["w"]) == norm(m.group(2))]
    if len(hits) > 1:
        when = ", ".join(f"{w['t0']:.2f}s" for w in hits)
        print(f"⚠️  {seg} → {what} \"{spec}\": said {len(hits)} times in act{'s' if len(acts) > 1 else ''} "
              f"{', '.join(map(str, acts))} ({when}); it takes the first. The later one: \"{m.group(2)}#2\"")

def first(act): return min(w["t0"] for w in WORDS if w["act"] == act)
def last(act): return max(w["t1"] for w in WORDS if w["act"] == act)

lead, segs, cues_all = P.get("lead", 0.3), [], {}
starts = [0.0] + [round((at(s["start"], s["acts"]) if s.get("start") else first(s["acts"][0])) - lead, 3) for s in P["segments"][1:] if s.get("acts")]
narr_end = round(last(max(a for s in P["segments"] for a in s.get("acts", []))) + P.get("after_last", 0.45), 3)
out_segments, scenes = [], dict(P.get("scene_data", {}))
for i, s in enumerate(P["segments"]):
    t0 = starts[i] if s.get("acts") else narr_end
    t1 = starts[i + 1] if i + 1 < len(starts) else (narr_end if s.get("acts") else round(P["total"], 3))
    acts = s.get("acts", [])
    seg = {"name": s["name"], "secs": round(t1 - t0, 3), "source": s["source"]}
    if i: seg["in"] = s.get("in", "whip")
    rel = lambda spec: round((t1 - t0) if spec == "end" else at(spec, acts) - t0, 3)
    for k, v in (s.get("cues") or {}).items(): twice(s["name"], f"cue {k}", v, acts)
    for tid, a, b in s.get("titles") or []: twice(s["name"], f"title {tid}", a, acts)
    if s.get("titles"):
        seg["titles"] = [[tid, max(0, rel(a)), rel(b) if b != "end" else "end"] for tid, a, b in s["titles"]]
        for tid, a, b in seg["titles"]:  # a word that matched too early makes a title end before it starts: it never leaves
            if b != "end" and b <= a + 1.5: raise SystemExit(f"⛔ {s['name']} → {tid}: ends {b:.2f}s after the segment starts but begins at {a:.2f}s; check the word specs")
    out_segments.append(seg)
    sc = s["source"].get("scene")
    if sc and s.get("cues"):
        scenes.setdefault(sc, {})["cues"] = {k: at(v, acts) for k, v in s["cues"].items()}
    print(f"{s['name']:18s} {t0:7.2f} → {t1:7.2f}  ({t1 - t0:5.2f}s)  {len(s.get('cues', {}))} cues, {len(s.get('titles', []))} titles")

reel = {k: P[k] for k in ("schema_version", "name", "version", "size", "fps", "palette", "font", "mono", "finish", "titles",
                           "never") if k in P}
reel["music"] = {"file": P["voice"], "beat": P.get("beat", 0.5), "first_hit": 0, "fade": 0.3}
# the voice's acts, first word to last: the timeline's voice row (voice/act-N), so a note can point at one
reel["acts"] = [{"act": a, "t0": round(first(a), 3), "t1": round(last(a), 3)} for a in sorted({w["act"] for w in WORDS})]
reel["punches"] = [at(p, list(range(1, 20))) for p in P.get("punches", [])]
reel["scene_lib"] = "explainer"  # build inlines the engine's scene library around scenes.js
reel["scenes"], reel["segments"] = scenes, out_segments
json.dump(reel, open("reel.json", "w"), indent=1)
print(f"end {out_segments and sum(s['secs'] for s in out_segments):.2f}s → reel.json")
# the contracts, before anything is built from it (vs check: plan.json, reel.json and the files beside them)
sys.stdout.flush()
sys.exit(subprocess.run(["node", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "js/check.mjs")]).returncode)
