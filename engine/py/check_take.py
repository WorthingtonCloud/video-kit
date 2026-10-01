#!/usr/bin/env python3
"""Check a narration take against the script: transcribe it back and list every word that differs.

    vs check-take voice/narration-v4.mp3 [--acts 9-10]     (acts: which part of narration.txt the take reads)

OpenAI gpt-4o-mini-transcribe, about a cent for two minutes (OPENAI_API_KEY, from the environment or a .env). Writes <take>.heard.txt.
Why: the voice model changes words, and some changes flip the meaning. The demo's first take (Sep 30, 2026) said "fell to 12"
for "fell twelve percent", "aligned" for "a line", "a role" for "agents to roles". Reword the line and record it again;
don't ship a take with a meaning change. Stage directions ([wry]) and "..." are not spoken, so they are stripped first."""
import difflib, os, re, subprocess, sys
from vslib import key as get_key, log

take = sys.argv[1]
acts = sys.argv[sys.argv.index("--acts") + 1] if "--acts" in sys.argv else "1-99"
lo, hi = (int(x) for x in acts.split("-"))
key = get_key("OPENAI_API_KEY")
heard = subprocess.run(["curl", "-s", "https://api.openai.com/v1/audio/transcriptions", "-H", f"Authorization: Bearer {key}",
                        "-F", f"file=@{take}", "-F", "model=gpt-4o-mini-transcribe", "-F", "response_format=text"],
                       capture_output=True, text=True, check=True).stdout.strip()
open(take.replace(".mp3", ".heard.txt"), "w").write(heard + "\n")
log("openai", f"take check {os.path.basename(take)}", usd=0.01, note="gpt-4o-mini-transcribe")
blocks = [" ".join(l for l in b.splitlines() if l.strip() and not l.startswith("#")) for b in open("narration.txt").read().split("\n\n")]
script = " ".join([b for b in blocks if b][lo - 1:hi])
norm = lambda s: [w for w in re.sub(r"[^a-z0-9' ]", " ", re.sub(r"\[[^\]]*\]", " ", s.lower()).replace("...", " ")).split() if w]
a, b = norm(script), norm(heard)
diffs = [(op, " ".join(a[i1:i2]), " ".join(b[j1:j2])) for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes() if op != "equal"]
print(f"{len(a)} words in the script, {len(b)} heard, {len(diffs)} differences")
for op, s, h in diffs:
    print(f"  script: {s or '—':40s}  heard: {h or '—'}")
print("Numbers read as words vs digits, and contractions, are harmless; anything that changes the meaning gets re-recorded.")
