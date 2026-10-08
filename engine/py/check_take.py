#!/usr/bin/env python3
"""Check a narration take against the script: transcribe it back and list every word that differs.

    vs check-take v4 [--acts 9-10] --yes     (a take's tag, or its path: voice/narration-v4.mp3; acts: which part of
                                              narration.txt the take reads)

OpenAI gpt-4o-mini-transcribe, about a cent for two minutes (OPENAI_API_KEY, from the environment or a .env), through the
spend gate like every paid step: without --yes it says the cost and stops. Writes <take>.heard.txt.
Why: the voice model changes words, and some changes flip the meaning. The demo's first take (Sep 30, 2026) said "fell to 12"
for "fell twelve percent", "aligned" for "a line", "a role" for "agents to roles". Reword the line and record it again;
don't ship a take with a meaning change. Stage directions ([wry]) and "..." are not spoken, so they are stripped first."""
import difflib, os, re, sys
from vslib import log, gate, done, transcribe

take = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else sys.exit("which take? vs check-take <tag or path>")
if not os.path.isfile(take) and os.path.isfile(f"voice/narration-{take}.mp3"):
    take = f"voice/narration-{take}.mp3"  # a tag, the way vs narrate names it
if not os.path.isfile(take):
    sys.exit(f"⛔ no take called {take}: give its tag (v2 = voice/narration-v2.mp3) or its path")
acts = sys.argv[sys.argv.index("--acts") + 1] if "--acts" in sys.argv else "1-99"
_a = acts.split("-")  # "5" = act 5 alone, "4-6" a run
lo, hi = int(_a[0]), int(_a[-1])
gate("openai", f"Transcribing {os.path.basename(take)} back to check it", usd=0.01, yes="--yes" in sys.argv)
row = log("openai", f"take check {os.path.basename(take)}", usd=0.01, note="gpt-4o-mini-transcribe")
heard = transcribe(take, ["model=gpt-4o-mini-transcribe", "response_format=text"], row).strip()
open(take.replace(".mp3", ".heard.txt"), "w").write(heard + "\n")
done(row)
blocks = [" ".join(l for l in b.splitlines() if l.strip() and not l.startswith("#")) for b in open("narration.txt").read().split("\n\n")]
script = " ".join([b for b in blocks if b][lo - 1:hi])
norm = lambda s: [w for w in re.sub(r"[^a-z0-9' ]", " ", re.sub(r"\[[^\]]*\]", " ", s.lower()).replace("...", " ")).split() if w]
a, b = norm(script), norm(heard)
diffs = [(op, " ".join(a[i1:i2]), " ".join(b[j1:j2])) for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes() if op != "equal"]
print(f"{len(a)} words in the script, {len(b)} heard, {len(diffs)} differences")
for op, s, h in diffs:
    print(f"  script: {s or '—':40s}  heard: {h or '—'}")
print("Numbers read as words vs digits, and contractions, are harmless; anything that changes the meaning gets re-recorded.")
